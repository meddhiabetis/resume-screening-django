import os
import datetime
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from .forms import UserRegisterForm, UserUpdateForm, GmailFetchForm, UserProfileForm
from .models import Profile
from apps.resume_analysis.views import process_resume
from apps.resume_analysis.models import Resume
from .email_sync.gmail_utils import fetch_gmail_pdfs
from .tasks import update_gmail_periodic_task
from django.core.files.base import ContentFile

import google_auth_oauthlib.flow
import googleapiclient.discovery


def home(request):
    """Render the home page or redirect to the dashboard if the user is authenticated."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    return render(request, "accounts/home.html")


def register(request):
    """Handle user registration and account creation."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("accounts:dashboard")
    else:
        form = UserRegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Handle user login and authentication."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("accounts:dashboard")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    """Log out the user and redirect to the login page."""
    logout(request)
    return redirect("accounts:login")


@login_required
def profile(request):
    """Render and handle user profile updates."""
    profile = request.user.profile
    if request.method == "POST":
        profile_form = UserProfileForm(request.POST, instance=profile)
        if profile_form.is_valid():
            old_enabled = profile.gmail_fetch_enabled  # Save previous value
            profile_form.save()
            profile.refresh_from_db()  # Ensure we have the latest values

            # If auto-fetch is now enabled and wasn't enabled before, set last_gmail_fetch to now
            if profile.gmail_fetch_enabled and not old_enabled:
                profile.last_gmail_fetch = timezone.now()
                profile.save(update_fields=["last_gmail_fetch"])

            update_gmail_periodic_task(profile)
            messages.success(request, "Profile updated successfully!")
            return redirect("accounts:profile")
    else:
        profile_form = UserProfileForm(instance=profile)
    return render(request, "accounts/profile.html", {"profile_form": profile_form})


@login_required
def dashboard(request):
    """Render the user dashboard with resume metrics and Gmail fetching options."""
    resumes = Resume.objects.filter(user=request.user).order_by("-upload_date")
    gmail_form = GmailFetchForm(request.POST or None)
    fetched_files = []
    profile = request.user.profile

    # ---- METRICS ----
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    total_resumes = resumes.count()
    processed_count = resumes.filter(status='processed').count()
    pending_count = resumes.filter(status='pending').count()
    failed_count = resumes.filter(status='failed').count()
    new_this_week = resumes.filter(upload_date__gte=week_ago).count()
    success_rate = int(processed_count / total_resumes * 100) if total_resumes > 0 else 0
    last_resume = resumes.order_by('-upload_date').first()
    last_resume_date = last_resume.upload_date if last_resume else None

    if (
        request.method == "POST"
        and "fetch_gmail" in request.POST
        and profile.gmail_connected
    ):
        if gmail_form.is_valid():
            subject = gmail_form.cleaned_data["subject"]
            before = gmail_form.cleaned_data["before"].strftime("%Y/%m/%d")
            after = gmail_form.cleaned_data["after"].strftime("%Y/%m/%d")
            save_dir = os.path.join(
                settings.MEDIA_ROOT, "gmail_cvs", str(request.user.id)
            )
            os.makedirs(save_dir, exist_ok=True)
            try:
                files = fetch_gmail_pdfs(
                    access_token=profile.gmail_access_token,
                    gmail_email=profile.gmail_email,
                    subject=subject,
                    before=before,
                    after=after,
                    save_dir=save_dir,
                )
                if files:
                    messages.success(request, f"Fetched {len(files)} CV(s) from Gmail.")
                    fetched_files = [os.path.basename(f) for f in files]

                    # Step 4: Parse and store as Resume objects
                    for file_path in files:
                        try:
                            # Open file for Django file storage
                            with open(file_path, "rb") as f:

                                django_file = ContentFile(
                                    f.read(), name=os.path.basename(file_path)
                                )

                                # Create Resume instance (status='processing' by default)
                                resume = Resume.objects.create(
                                    user=request.user,
                                    original_filename=os.path.basename(file_path),
                                    status="processing",
                                )
                                # Process and extract features (this saves ResumeContent etc.)
                                process_resume(django_file, resume)

                        except Exception as e:
                            messages.error(
                                request,
                                f"Failed to process {os.path.basename(file_path)}: {e}",
                            )

                else:
                    messages.info(request, "No matching CVs found in Gmail.")
            except Exception as e:
                messages.error(request, f"Failed to fetch from Gmail: {e}")

    return render(
        request,
        "accounts/dashboard.html",
        {
            "resumes": resumes,
            "gmail_form": gmail_form,
            "fetched_files": fetched_files,
            "total_resumes": total_resumes,
            "processed_count": processed_count,
            "pending_count": pending_count,
            "failed_count": failed_count,
            "new_this_week": new_this_week,
            "success_rate": success_rate,
            "last_resume_date": last_resume_date,
        },
    )


@login_required
def gmail_connect(request):
    """Initiate the Gmail OAuth flow for connecting the user's Gmail account."""
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.GOOGLE_OAUTH_CLIENT_SECRETS,
        scopes=settings.GOOGLE_OAUTH_SCOPES,
    )
    # Build redirect_uri based on current request to avoid localhost/127.0.0.1 mismatches
    flow.redirect_uri = request.build_absolute_uri(reverse("accounts:gmail_callback"))

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["google_oauth_state"] = state
    request.session["google_oauth_redirect_uri"] = flow.redirect_uri
    request.session.save()
    return redirect(authorization_url)


def gmail_callback(request):
    """Handle the callback from the Gmail OAuth flow and link the Gmail account to the user."""
    expected_state = request.session.get("google_oauth_state")
    incoming_state = request.GET.get("state")

    # Gracefully handle state mismatch: restart flow instead of error page
    if not expected_state or incoming_state != expected_state:
        messages.error(request, "OAuth state mismatch. Please try connecting again.")
        request.session.pop("google_oauth_state", None)
        request.session.pop("google_oauth_redirect_uri", None)
        return redirect("accounts:gmail_connect")

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.GOOGLE_OAUTH_CLIENT_SECRETS,
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        state=expected_state,
    )
    flow.redirect_uri = request.session.get("google_oauth_redirect_uri") or request.build_absolute_uri(
        reverse("accounts:gmail_callback")
    )

    authorization_response = request.build_absolute_uri()
    flow.fetch_token(authorization_response=authorization_response)

    # Clear state after use
    request.session.pop("google_oauth_state", None)
    request.session.pop("google_oauth_redirect_uri", None)

    credentials = flow.credentials

    # Get user info from Google
    userinfo_service = googleapiclient.discovery.build("oauth2", "v2", credentials=credentials)
    user_info = userinfo_service.userinfo().get().execute()
    google_email = user_info.get("email")

    # Make sure the user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to connect your Gmail account.")
        return redirect("accounts:login")

    # Optional: Prevent Gmail already linked to another user
    from apps.accounts.models import Profile

    if Profile.objects.filter(gmail_email=google_email).exclude(user=request.user).exists():
        messages.error(request, "This Gmail account is already connected to another user.")
        return redirect("accounts:profile")

    # Link Gmail to the currently logged in user
    profile = request.user.profile
    profile.gmail_access_token = credentials.token
    profile.gmail_refresh_token = credentials.refresh_token
    expiry_time = timezone.now() + datetime.timedelta(
        seconds=(credentials.expiry.timestamp() - timezone.now().timestamp())
    )
    profile.gmail_token_expiry = expiry_time
    profile.gmail_email = google_email
    profile.gmail_connected = True
    profile.save()

    messages.success(request, f"Gmail account {google_email} connected successfully!")
    return render(request, "accounts/gmail_connected.html", {"email": profile.gmail_email})


@login_required
def disconnect_gmail(request):
    """Disconnect the user's Gmail account."""
    profile = request.user.profile
    profile.gmail_credentials_json = None
    profile.gmail_email = None  # If you store email separately
    profile.gmail_connected = False
    profile.save()
    messages.success(request, "Gmail account disconnected.")
    return redirect("accounts:profile")