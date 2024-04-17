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


def your_view_function(request):
    resumes_directory = os.path.join(BASE_DIR, 'homepage', 'resumes')
    extracted_text = process_uploaded_resumes(resumes_directory)
    # Further processing or rendering the extracted text
    return render(request, 'your_template.html', {'extracted_text': extracted_text})

def upload_resumes(request):
    if request.method == 'POST' and request.FILES.getlist('resume'):
        uploaded_resumes = request.FILES.getlist('resume')
        for resume in uploaded_resumes:
            fs = FileSystemStorage()
            fs.save(os.path.join('homepage/resumes', resume.name), resume)

        resumes_directory = os.path.join(BASE_DIR, 'homepage', 'resumes')
        extracted_text = process_uploaded_resumes(resumes_directory)

        messages.success(request, "Resumes uploaded successfully!")
        return redirect('analysis_results')  # Redirect to analysis results page after successful upload
    return render(request, 'index.html')

from sklearn.feature_extraction.text import TfidfVectorizer

from .pdf_utils import process_uploaded_resumes, clean_resume
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer

def classify_resumes(resumes,requiredText):
    # Load the trained classifier
    classifier = joblib.load('resume_classifier_model/resume_classifier.pkl')  
    
    # Load the TfidfVectorizer
    word_vectorizer = TfidfVectorizer(
        sublinear_tf=True,
        stop_words='english'
    )
    word_vectorizer.fit(requiredText)
    
    # Preprocess the resumes (cleaning, tokenization, etc.)
    cleaned_resumes = [clean_resume(resume) for resume in resumes]
    
    # Vectorize the preprocessed resumes
    vectorized_resumes = word_vectorizer.transform(cleaned_resumes)
    
    # Predict the category for each resume
    predictions = classifier.predict(vectorized_resumes)
    
    return predictions

from wordcloud import WordCloud
import matplotlib.pyplot as plt
from django.conf import settings
import base64

def generate_word_cloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    # Save the word cloud image
    wordcloud_path = os.path.join(BASE_DIR, 'homepage', 'static', 'wordcloud.png')
    wordcloud.to_file(wordcloud_path)
    return wordcloud_path


from django.http import HttpResponseRedirect
from django.urls import reverse

def analysis_results(request):
    if request.method == 'POST':
        required_skills = request.POST.get('required_skills', '')
        # Process the required skills and match candidates here
        # For demonstration, let's assume you have a function to match candidates
        matched_candidates = match_candidates_based_on_skills(required_skills)
        return render(request, 'analysis_results.html', {'categories': percentage_stats, 'total_resumes': total_resumes, 'wordcloud_path': wordcloud_path, 'matched_candidates': matched_candidates})

    resumes_directory = os.path.join(BASE_DIR, 'homepage', 'resumes')
    extracted_texts, file_names = process_uploaded_resumes(resumes_directory)
    
    # Concatenate all extracted text
    all_text = ' '.join(extracted_texts)
    
    # Generate word cloud
    wordcloud_path = generate_word_cloud(all_text)
    
    # Classify the extracted resumes
    predictions = classify_resumes(extracted_texts, requiredText)
    
    # Calculate category statistics and percentages
    categories, counts = np.unique(predictions, return_counts=True)
    total_resumes = len(predictions)
    stats = {category: count for category, count in zip(categories, counts)}
    percentage_stats = {category: (count / total_resumes) * 100 for category, count in stats.items()}
    
    return render(request, 'analysis_results.html', {'categories': percentage_stats, 'total_resumes': total_resumes, 'wordcloud_path': wordcloud_path})

def match_candidates_based_on_skills(required_skills):
    # For demonstration purposes, let's assume you have a list of candidates with their skills
    candidates = [
        {'name': 'Candidate 1', 'skills': ['Python', 'Java', 'SQL']},
        {'name': 'Candidate 2', 'skills': ['Python', 'JavaScript', 'HTML']},
        {'name': 'Candidate 3', 'skills': ['Java', 'C++', 'SQL']},
        # Add more candidates as needed
    ]
    
    # Calculate relevance score for each candidate based on their skills compared to required skills
    for candidate in candidates:
        candidate['relevance_score'] = calculate_relevance_score(candidate['skills'], required_skills)
    
    # Sort candidates by relevance score in descending order
    matched_candidates = sorted(candidates, key=lambda x: x['relevance_score'], reverse=True)
    
    return matched_candidates

def calculate_relevance_score(candidate_skills, required_skills):
    # Calculate the relevance score based on the number of matching skills
    matching_skills = set(candidate_skills) & set(required_skills)
    relevance_score = len(matching_skills)
    return relevance_score

