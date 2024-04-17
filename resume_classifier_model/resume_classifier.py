import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.multiclass import OneVsRestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os
import re
import string
import nltk
from nltk.corpus import stopwords
nltk.download('punkt')
nltk.download('stopwords')
# Get the path to the dataset file
dataset_path = os.path.join(os.getcwd(), 'resume_classifier_model', 'UpdatedResumeDataSet.csv')

# Load the dataset
resumeDataSet = pd.read_csv(dataset_path, encoding='utf-8')

# Preprocess the resumes
def cleanResume(resumeText):
    # Remove URLs
    resumeText = re.sub('http\S+\s*', ' ', resumeText)
    # Remove RT and cc
    resumeText = re.sub('RT|cc', ' ', resumeText)
    # Remove hashtags
    resumeText = re.sub('#\S+', '', resumeText)
    # Remove mentions
    resumeText = re.sub('@\S+', '  ', resumeText)
    # Remove punctuations
    resumeText = re.sub('[%s]' % re.escape(string.punctuation), ' ', resumeText)
    # Remove non-ASCII characters
    resumeText = re.sub(r'[^\x00-\x7f]', ' ', resumeText)
    # Remove extra whitespaces
    resumeText = re.sub('\s+', ' ', resumeText)
    
    # Tokenize the text
    tokens = nltk.word_tokenize(resumeText)
    
    # Get stopwords
    stop_words = set(stopwords.words('english'))
    
    # Filter out stopwords and punctuation
    cleaned_tokens = [word.lower() for word in tokens if word.lower() not in stop_words and word.lower() not in string.punctuation]
    
    # Join the cleaned tokens back into a sentence
    cleaned_resume = ' '.join(cleaned_tokens)
    
    return cleaned_resume

resumeDataSet['cleaned_resume'] = resumeDataSet['Resume'].apply(cleanResume)

# Prepare features and target
requiredText = resumeDataSet['cleaned_resume'].values
requiredTarget = resumeDataSet['Category'].values

# Vectorize the text data
vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words='english')
WordFeatures = vectorizer.fit_transform(requiredText)

# Split the data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(WordFeatures, requiredTarget, test_size=0.2, random_state=42)

# Define the classifier
classifier = OneVsRestClassifier(KNeighborsClassifier())

# Train the classifier
classifier.fit(X_train, y_train)

# Evaluate the classifier
train_accuracy = classifier.score(X_train, y_train)
test_accuracy = classifier.score(X_test, y_test)
print(f"Training accuracy: {train_accuracy}")
print(f"Test accuracy: {test_accuracy}")

# Save the trained model
model_path = os.path.join(os.getcwd(), 'resume_classifier_model', 'resume_classifier.pkl')
joblib.dump(classifier, model_path)
