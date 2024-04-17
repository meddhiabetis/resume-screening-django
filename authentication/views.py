from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout

from django.contrib import messages
from django.urls import reverse
from .forms import  SignUpForm



def signin(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, "Logged in Successfully!")
            print(user.first_name)  # Check if the first name is retrieved correctly
            return redirect('home')  # Redirect to the home page without any additional parameters
        else:
            messages.error(request, "Wrong Credentials!")  # Change to messages.error
            return redirect('signin')
            
    return render(request, 'signin.html')

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)  # Use Django's built-in forms for data validation
        if form.is_valid():
            user = form.save()
            # Use.first_name instead of user.first_name to get the actual value
            print(user.first_name)
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            messages.success(request, "Signed up Successfully!")
            return redirect('home')
        else:
            messages.error(request, "Invalid Data!")
            return redirect('signup')

    else:
        form = SignUpForm()
        return render(request, 'signup.html', {'form': form})

def signout(request):
    logout(request)
    messages.success(request, "Logged Out Successfully!")
    return redirect('signin')  # Redirect to the login page