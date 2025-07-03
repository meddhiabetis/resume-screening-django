import logging
from typing import List, Dict, Any
from django.conf import settings
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class Neo4jService:
    """Service class for interacting with Neo4j database for resume analysis.

    This class provides methods to create, update, delete, and retrieve resumes
    and their associated skills in the Neo4j database.
    """

    def __init__(self):
        """Initialize the Neo4jService with a database driver."""
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        """Close the Neo4j database driver."""
        self._driver.close()

    def create_or_update_resume(self, resume_data: Dict[str, Any]) -> str:
        """Create or update a resume node with basic information.

        Args:
            resume_data (Dict[str, Any]): A dictionary containing resume information,
                                            including 'id', 'file_name', 'vector_id',
                                            'user_id', and 'skills'.

        Returns:
            str: The ID of the created or updated resume.
        """
        with self._driver.session() as session:
            try:
                # First, create or update the resume node
                create_resume_query = """
                MERGE (r:Resume {id: $resume_id})
                SET r.file_name = $file_name,
                    r.vector_id = $vector_id,
                    r.updated_at = datetime()
                WITH r
                
                MERGE (u:User {id: $user_id})
                MERGE (u)-[:OWNS]->(r)
                
                // Remove all existing skill relationships
                WITH r
                OPTIONAL MATCH (r)-[old_rel:HAS_SKILL]->()
                DELETE old_rel
                
                RETURN r
                """
                
                session.run(
                    create_resume_query,
                    resume_id=resume_data['id'],
                    file_name=resume_data['file_name'],
                    vector_id=resume_data.get('vector_id', ''),
                    user_id=resume_data['user_id']
                )

                # Log skills being added
                logger.info(f"Adding {len(resume_data.get('skills', []))} skills for resume {resume_data['id']}")
                
                # Then, create skills and relationships if skills exist
                if resume_data.get('skills'):
                    for skill in resume_data['skills']:
                        skill_query = """
                        MATCH (r:Resume {id: $resume_id})
                        MERGE (s:Skill {name: $skill_name})
                        SET s.category = $skill_category,
                            s.updated_at = datetime()
                        MERGE (r)-[rel:HAS_SKILL]->(s)
                        SET rel.confidence = $skill_confidence,
                            rel.updated_at = datetime()
                        """
                        
                        # Log each skill being added
                        logger.info(f"Adding skill '{skill['name']}' to resume {resume_data['id']}")
                        
                        session.run(
                            skill_query,
                            resume_id=resume_data['id'],
                            skill_name=skill['name'].lower().strip(),
                            skill_category=skill['category'],
                            skill_confidence=skill.get('confidence', 1.0)
                        )

                # Verify skills were added
                verify_query = """
                MATCH (r:Resume {id: $resume_id})-[rel:HAS_SKILL]->(s:Skill)
                RETURN count(s) as skill_count, collect(s.name) as skill_names
                """
                
                result = session.run(verify_query, resume_id=resume_data['id']).single()
                logger.info(f"Verified {result['skill_count']} skills added to resume {resume_data['id']}: {result['skill_names']}")

                return resume_data['id']
                
            except Exception as e:
                logger.error(f"Error creating/updating resume: {str(e)}")
                raise

    def find_similar_resumes(self, resume_id: str, min_skill_match: int = 1, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar resumes based on skills.

        Args:
            resume_id (str): The ID of the resume to compare against.
            min_skill_match (int): Minimum number of matching skills to consider a resume similar.
            limit (int): Maximum number of similar resumes to return.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing similar resumes' information.
        """
        with self._driver.session() as session:
            try:
                query = """
                // Get all skills of the source resume
                MATCH (r1:Resume {id: $resume_id})-[:HAS_SKILL]->(s:Skill)
                WITH r1, COLLECT(s) as r1_skills, SIZE(COLLECT(s)) as total_skills
                
                // Find other resumes that share skills
                MATCH (r2:Resume)-[:HAS_SKILL]->(s2:Skill)
                WHERE r2 <> r1 AND s2 IN r1_skills
                
                WITH r2,
                     COUNT(DISTINCT s2) as common_skills,
                     COLLECT(DISTINCT s2.name) as shared_skills,
                     total_skills
                WHERE common_skills >= $min_skill_match
                
                // Calculate normalized similarity score
                WITH r2, 
                     common_skills,
                     shared_skills,
                     toFloat(common_skills) / toFloat(total_skills) as similarity_score
                
                RETURN 
                    r2.id as resume_id,
                    r2.file_name as file_name,
                    r2.vector_id as vector_id,
                    common_skills,
                    shared_skills,
                    similarity_score
                ORDER BY similarity_score DESC, common_skills DESC
                LIMIT $limit
                """
                
                results = session.run(
                    query,
                    resume_id=resume_id,
                    min_skill_match=min_skill_match,
                    limit=limit
                )
                
                return [dict(record) for record in results]
                
            except Exception as e:
                logger.error(f"Error finding similar resumes: {str(e)}")
                return []

    def delete_resume(self, resume_id: str):
        """Delete a resume and its relationships.

        Args:
            resume_id (str): The ID of the resume to delete.
        """
        with self._driver.session() as session:
            try:
                query = """
                MATCH (r:Resume {id: $resume_id})
                OPTIONAL MATCH (r)-[rel]-()
                DELETE rel, r
                """
                
                session.run(query, resume_id=resume_id)
                logger.info(f"Deleted resume {resume_id} from Neo4j")
                
            except Exception as e:
                logger.error(f"Error deleting resume: {str(e)}")
                raise

    def get_resume_skills(self, resume_id: str) -> List[Dict[str, Any]]:
        """Get all skills associated with a resume.

        Args:
            resume_id (str): The ID of the resume to retrieve skills for.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing skill information.
        """
        with self._driver.session() as session:
            try:
                query = """
                MATCH (r:Resume {id: $resume_id})-[rel:HAS_SKILL]->(s:Skill)
                RETURN s.name as name,
                       s.category as category,
                       rel.confidence as confidence
                ORDER BY s.category, s.name
                """
                
                results = session.run(query, resume_id=resume_id)
                return [dict(record) for record in results]
                
            except Exception as e:
                logger.error(f"Error getting resume skills: {str(e)}")
                return []