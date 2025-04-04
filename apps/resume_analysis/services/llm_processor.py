import requests
import json
from django.conf import settings
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self):
        self.api_key = settings.MISTRAL_API_KEY
        self.model = "mistral-large-latest"
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        
        # Configure retry strategy
        self.session = requests.Session()
        retries = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def extract_resume_features(self, text, max_retries=3):
        """Extract important features from resume text using Mistral AI"""
        
        # Split text into chunks if it's too long
        max_chunk_length = 8000  # Adjust based on model's context window
        chunks = [text[i:i + max_chunk_length] for i in range(0, len(text), max_chunk_length)]
        
        for attempt in range(max_retries):
            try:
                # If we have multiple chunks, process them separately and combine
                all_features = {}
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_features = self._process_chunk(chunk, chunk_idx, len(chunks))
                    
                    if "error" in chunk_features:
                        logger.warning(f"Error processing chunk {chunk_idx + 1}: {chunk_features['error']}")
                        continue
                    
                    # Merge features
                    all_features = self._merge_features(all_features, chunk_features)

                # If we got any valid features, return them
                if all_features:
                    return all_features
                
                # If we got here, no chunks were processed successfully
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Progressive delay: 5s, 10s, 15s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                return {
                    "error": "Failed to process resume after multiple attempts",
                    "details": "All chunks failed processing",
                    "status": "failed"
                }

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.info(f"Retrying in {wait_time} seconds due to error: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "error": "Processing Error",
                        "details": str(e),
                        "status": "failed"
                    }

    def _process_chunk(self, text_chunk, chunk_idx, total_chunks):
        """Process a single chunk of text"""
        
        system_prompt = """You are an expert resume analyzer. Extract information from the resume chunk and return it ONLY as a valid JSON object.
        If this is not the first chunk, only extract new information not seen before.
        
        Return the JSON in this exact structure:
        {
            "contact_info": {
                "name": "",
                "email": "",
                "phone": "",
                "location": ""
            },
            "work_experience": [
                {
                    "company": "",
                    "title": "",
                    "dates": "",
                    "responsibilities": []
                }
            ],
            "education": [
                {
                    "institution": "",
                    "degree": "",
                    "dates": "",
                    "gpa": ""
                }
            ],
            "skills": {
                "technical": [],
                "soft": []
            },
            "projects": [
                {
                    "name": "",
                    "description": "",
                    "technologies": []
                }
            ],
            "certifications": [],
            "languages": []
        }"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Process this resume chunk ({chunk_idx + 1} of {total_chunks}):\n\n{text_chunk}"}
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"}
            }

            response = self.session.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=60  # Increased timeout
            )

            if response.status_code != 200:
                return {
                    "error": f"API Error {response.status_code}",
                    "details": response.text,
                    "status": "failed"
                }

            content = response.json()['choices'][0]['message']['content']
            return json.loads(content)

        except requests.Timeout:
            return {
                "error": "API Timeout",
                "details": "Request timed out",
                "status": "failed"
            }
        except Exception as e:
            return {
                "error": "Processing Error",
                "details": str(e),
                "status": "failed"
            }

    def _merge_features(self, existing_features, new_features):
        """Merge features from multiple chunks"""
        if not existing_features:
            return new_features
            
        merged = existing_features.copy()
        
        # Merge lists
        for key in ['work_experience', 'education', 'projects', 'certifications', 'languages']:
            if key in new_features:
                merged[key] = merged.get(key, []) + new_features[key]
        
        # Merge skills
        if 'skills' in new_features:
            if 'skills' not in merged:
                merged['skills'] = {'technical': [], 'soft': []}
            merged['skills']['technical'] = list(set(
                merged['skills'].get('technical', []) +
                new_features['skills'].get('technical', [])
            ))
            merged['skills']['soft'] = list(set(
                merged['skills'].get('soft', []) +
                new_features['skills'].get('soft', [])
            ))
        
        # Update contact info if any new fields are present
        if 'contact_info' in new_features:
            if 'contact_info' not in merged:
                merged['contact_info'] = {}
            for field, value in new_features['contact_info'].items():
                if value and not merged['contact_info'].get(field):
                    merged['contact_info'][field] = value
        
        return merged