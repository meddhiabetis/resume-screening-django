import os
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from django.shortcuts import redirect
from django.contrib.auth import logout
from django.shortcuts import render
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
import joblib

from resume_screening import settings
from resume_screening.settings import BASE_DIR
from .pdf_utils import clean_resume, process_uploaded_resumes
from resume_classifier_model.resume_classifier import requiredText
from .analysis import classify_resumes
from django.http import HttpResponseRedirect
from django.urls import reverse
from sklearn.feature_extraction.text import TfidfVectorizer
from .pdf_utils import process_uploaded_resumes, clean_resume
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .analysis import generate_word_cloud
class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fname'] = self.kwargs.get('fname', '')  # Get the 'fname' parameter from URL
        return context
    

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def signout(request):
    logout(request)
    messages.success(request, "Logged Out Successfully!")
    return redirect('home')  # Redirect to the home page using GET request



def analysis_results_single(request):
    if request.method == 'POST' and request.FILES.get('resume'):
        resume = request.FILES['resume']
        fs = FileSystemStorage()
        # Delete existing files in 'resume' folder
        delete_existing_files('resume')
        # Save the uploaded resume to the 'resume' folder
        fs.save(os.path.join('homepage', 'resume', resume.name), resume)
        resume_directory = os.path.join(settings.BASE_DIR, 'homepage', 'resume')
        # Pass the directory path containing the uploaded resume
        extracted_text, _ = process_uploaded_resumes(resume_directory)
        print(extracted_text)
        print(type(extracted_text))
        # Generate word cloud from extracted text
        wordcloud_path = generate_word_cloud(extracted_text[0])
        # Further processing or rendering the extracted text and word cloud path
        return render(request, 'analysis_results_single.html', {'extracted_text': extracted_text,
                                                         'wordcloud_path': wordcloud_path})
    return render(request, 'analysis_results_single.html')




import json
from django.http import JsonResponse

def analysis_results_multiple(request):
    categories_json = '{}'
    total_resumes = 0
    file_names = []

    if request.method == 'POST' and request.FILES.getlist('resume'):
        uploaded_resumes = request.FILES.getlist('resume')
        fs = FileSystemStorage()
        # Delete existing files in 'resumes' folder
        delete_existing_files('resumes')
        for resume in uploaded_resumes:
            fs.save(os.path.join('homepage/resumes', resume.name), resume)
        resumes_directory = os.path.join(settings.BASE_DIR, 'homepage', 'resumes')
        extracted_texts, file_names = process_uploaded_resumes(resumes_directory)
        predictions = classify_resumes(extracted_texts, requiredText)  # Adjust requiredText accordingly
        categories, counts = np.unique(predictions, return_counts=True)
        total_resumes = len(predictions)
        stats = {category: count for category, count in zip(categories, counts)}
        percentage_stats = {category: (count / total_resumes) * 100 for category, count in stats.items()}
        
        # Convert categories to JSON format
        categories_json = json.dumps(percentage_stats)
        
        # Print the data for verification
        print("Categories:", categories)
        print("Total Resumes:", total_resumes)
        print("Percentage Stats:", percentage_stats)
        
    # Handle GET request for search
    if request.method == 'GET' and 'search' in request.GET:
        search_query = request.GET.get('search', '')
        # Ensure resumes are processed before searching
        resumes_directory = os.path.join(settings.BASE_DIR, 'homepage', 'resumes')
        extracted_texts, file_names = process_uploaded_resumes(resumes_directory)
        predictions = classify_resumes(extracted_texts, requiredText)  # Adjust requiredText accordingly
        categories, counts = np.unique(predictions, return_counts=True)
        total_resumes = len(predictions)
        stats = {category: count for category, count in zip(categories, counts)}
        percentage_stats = {category: (count / total_resumes) * 100 for category, count in stats.items()}
        
        # Convert categories to JSON format
        categories_json = json.dumps(percentage_stats)
        
        # Print the data for verification
        print("Categories:", categories)
        print("Total Resumes:", total_resumes)
        print("Percentage Stats:", percentage_stats)
        
        # Filter resumes based on the search query
        filtered_resumes = []
        for resume_text, resume_file in zip(extracted_texts, file_names):
            if search_query.lower() in resume_text.lower():
                filtered_resumes.append(resume_file)
        return render(request, 'analysis_results_multiple.html', {'search_query': search_query, 'filtered_resumes': filtered_resumes, 'categories': categories_json, 'total_resumes': total_resumes})
    
    # If no search query is provided, return the initial page with categories
    return render(request, 'analysis_results_multiple.html', {'categories': categories_json, 'total_resumes': total_resumes})

def delete_existing_files(folder):
    folder_path = os.path.join(settings.BASE_DIR, 'homepage', folder)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        os.remove(file_path)

