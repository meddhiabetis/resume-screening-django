from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json
from celery import shared_task
from django.utils import timezone
from .models import Profile
from .email_sync.gmail_utils import fetch_gmail_pdfs
from apps.resume_analysis.views import process_resume
from apps.resume_analysis.models import Resume
import os
from django.conf import settings

def update_gmail_periodic_task(profile):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=profile.gmail_fetch_interval,
        period=IntervalSchedule.MINUTES,
    )
    task_name = f'auto-fetch-gmail-{profile.user.id}'
    task_kwargs = json.dumps({'user_id': profile.user.id})
    task, _ = PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            'interval': interval,
            'task': 'apps.accounts.tasks.auto_fetch_gmail_resumes_for_one',
            'kwargs': task_kwargs,
            'enabled': profile.gmail_fetch_enabled and profile.gmail_connected,
        }
    )
    if not (profile.gmail_fetch_enabled and profile.gmail_connected):
        task.enabled = False
        task.save()
        

    
@shared_task
def auto_fetch_gmail_resumes_for_one(user_id):
    from django.utils import timezone
    from datetime import timezone as dt_timezone
    now = timezone.now()
    try:
        profile = Profile.objects.get(user_id=user_id, gmail_connected=True, gmail_fetch_enabled=True)
    except Profile.DoesNotExist:
        return

    last_fetch = profile.last_gmail_fetch or now
    before = int(now.timestamp())
    after = int(last_fetch.timestamp())
    """ FOR DEBUG
    print("---- Gmail Fetch Debug Info ----")
    print("now:", now)
    print("last_gmail_fetch:", last_fetch)
    print("now.timestamp():", before)
    print("last_gmail_fetch.timestamp():", after)
    print("now as UTC:", now.astimezone(dt_timezone.utc))
    print("last_gmail_fetch as UTC:", last_fetch.astimezone(dt_timezone.utc))
    print("now (ISO):", now.isoformat())
    print("last_gmail_fetch (ISO):", last_fetch.isoformat())
    print("-------------------------------")"""

    save_dir = os.path.join(settings.MEDIA_ROOT, "gmail_cvs", str(profile.user.id))
    os.makedirs(save_dir, exist_ok=True)
    files = fetch_gmail_pdfs(
        access_token=profile.gmail_access_token,
        gmail_email=profile.gmail_email,
        subject=None,
        before=before,
        after=after,
        save_dir=save_dir
    )
    for file_path in files:
        with open(file_path, "rb") as f:
            from django.core.files.base import ContentFile
            django_file = ContentFile(f.read(), name=os.path.basename(file_path))
            resume = Resume.objects.create(
                user=profile.user,
                original_filename=os.path.basename(file_path),
                status='processing'
            )
            process_resume(django_file, resume)
    profile.last_gmail_fetch = now
    profile.save()