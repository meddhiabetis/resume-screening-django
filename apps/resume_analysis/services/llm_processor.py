import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self):
        self.api_key = settings.MISTRAL_API_KEY
        self.model = "mistral-large-latest"
        self.api_url = "https://api.mistral.ai/v1/chat/completions"

    def extract_resume_features(self, text):
        """Extract important features from resume text using Mistral AI"""
        
        system_prompt = """You are an expert resume analyzer. You must extract information from the resume and return it ONLY as a valid JSON object with no additional text or explanation.

        The JSON must follow this exact structure:
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
        }

        Rules:
        1. Use YYYY-MM format for dates when available
        2. Return empty arrays [] for missing lists
        3. Return empty strings "" for missing text fields
        4. Return ONLY the JSON object, no other text
        5. Ensure the JSON is properly formatted and valid"""
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract information from this resume:\n\n{text}"}
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"}  # Force JSON response
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30  # 30 seconds timeout
            )

            # Log the raw response for debugging
            logger.debug(f"API Response Status: {response.status_code}")
            logger.debug(f"API Response Headers: {response.headers}")
            logger.debug(f"API Response Text: {response.text[:500]}...")  # Log first 500 chars

            if response.status_code != 200:
                error_message = f"API Error {response.status_code}: {response.text}"
                logger.error(error_message)
                return {
                    "error": "API Error",
                    "details": error_message,
                    "status": "failed"
                }

            try:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Log the content for debugging
                logger.debug(f"Response Content: {content[:500]}...")

                # Try to parse the content as JSON
                try:
                    parsed_result = json.loads(content)
                    # Validate the required keys are present
                    required_keys = [
                        "contact_info", "work_experience", "education",
                        "skills", "projects", "certifications", "languages"
                    ]
                    if all(key in parsed_result for key in required_keys):
                        return parsed_result
                    else:
                        missing_keys = [key for key in required_keys if key not in parsed_result]
                        return {
                            "error": "Invalid JSON structure",
                            "details": f"Missing required keys: {', '.join(missing_keys)}",
                            "raw_response": content
                        }

                except json.JSONDecodeError as e:
                    # Try to extract JSON if there's additional text
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.endswith('```'):
                        content = content[:-3]
                    
                    try:
                        parsed_result = json.loads(content.strip())
                        return parsed_result
                    except:
                        return {
                            "error": "JSON Parsing Error",
                            "details": str(e),
                            "raw_response": content
                        }

            except Exception as e:
                return {
                    "error": "Response Processing Error",
                    "details": str(e),
                    "raw_response": response.text
                }

        except requests.RequestException as e:
            error_message = f"Request Error: {str(e)}"
            logger.error(error_message)
            return {
                "error": "Request Failed",
                "details": error_message,
                "status": "failed"
            }
        except Exception as e:
            error_message = f"Unexpected Error: {str(e)}"
            logger.error(error_message)
            return {
                "error": "Processing Error",
                "details": error_message,
                "status": "failed"
            }