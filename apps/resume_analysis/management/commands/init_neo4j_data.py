from django.core.management.base import BaseCommand
from apps.resume_analysis.models import Resume
from apps.resume_analysis.services.neo4j_service import Neo4jService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Initialize Neo4j database with resume data'

    def handle(self, *args, **options):
        try:
            neo4j = Neo4jService()
            resumes = Resume.objects.filter(status='processed')
            
            self.stdout.write(f"Found {resumes.count()} processed resumes to add to Neo4j")
            
            for resume in resumes:
                try:
                    # Get extracted features
                    content = resume.resumecontent
                    features = content.extracted_features
                    
                    if not features:
                        self.stdout.write(f"No features for resume {resume.file_id}, skipping")
                        continue

                    # Prepare skills data
                    skills = []
                    if 'skills' in features:
                        technical_skills = features['skills'].get('technical', [])
                        soft_skills = features['skills'].get('soft', [])
                        
                        for skill in technical_skills:
                            skills.append({
                                'name': skill,
                                'category': 'technical',
                                'confidence': 1.0
                            })
                        
                        for skill in soft_skills:
                            skills.append({
                                'name': skill,
                                'category': 'soft',
                                'confidence': 1.0
                            })

                    # Create resume data structure
                    resume_data = {
                        'id': str(resume.file_id),
                        'file_name': resume.original_filename,
                        'vector_id': f"{resume.file_id}-full_text",
                        'user_id': str(resume.user.id),
                        'metadata': {
                            'processed_date': str(resume.upload_date),
                            'status': resume.status
                        },
                        'skills': skills
                    }

                    # Add to Neo4j
                    neo4j.create_or_update_resume(resume_data)
                    self.stdout.write(
                        self.style.SUCCESS(f"Added resume {resume.file_id} to Neo4j")
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing resume {resume.file_id}: {str(e)}")
                    )
                    continue

            self.stdout.write(
                self.style.SUCCESS('Successfully initialized Neo4j database with resume data')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error initializing Neo4j data: {str(e)}')
            )