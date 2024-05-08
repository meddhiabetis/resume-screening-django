import os
import joblib
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from django.conf import settings
import base64

from homepage.pdf_utils import clean_resume
from resume_screening.settings import BASE_DIR
from sklearn.feature_extraction.text import TfidfVectorizer,CountVectorizer

import numpy as np
from PIL import Image

def generate_word_cloud(text):
    if isinstance(text, str):
        # Generate word cloud without background color
        wordcloud = WordCloud(width=800, height=400, background_color=None).generate(text)
        
        # Convert hex color code to RGB
        background_color = (244, 234, 224)  # Corresponding RGB values for #f4eae0
        
        # Create a mask for the background color
        mask = np.full_like(wordcloud.to_array(), fill_value=255)  # Create a mask with white background
        r, g, b = background_color
        mask[(mask[:,:,0] == 255) & (mask[:,:,1] == 255) & (mask[:,:,2] == 255)] = [r, g, b]  # Fill mask with background color
        
        # Generate word cloud with custom background color
        wordcloud_with_color = WordCloud(width=800, height=400, mask=mask, contour_color=None,
                                         contour_width=0, background_color=None).generate(text)
        
        # Save the word cloud image
        wordcloud_path = os.path.join(BASE_DIR, 'homepage', 'static', 'wordcloud.png')
        wordcloud_with_color.to_file(wordcloud_path)
        
        return wordcloud_path
    else:
        # If the text is not a string, return None or handle it appropriately
        return None  # You can adjust this based on your requirements

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

def match_candidates_based_on_skills(required_skills):
    # to do
    pass

def calculate_relevance_score(candidate_skills, required_skills):
    pass

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
