import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class Neo4jService:
    """Service class for interacting with Neo4j database for resume analysis.
    Provides methods to create/update resumes with richer entities (skills, titles, companies, schools),
    and to search resumes directly from query tokens (independent of vector search).
    """

    def __init__(self):
        """Initialize the Neo4jService with a database driver."""
        self._driver = GraphDatabase.driver(
            getattr(settings, 'NEO4J_URI', "bolt://localhost:7687"),
            auth=(getattr(settings, 'NEO4J_USER', "neo4j"), getattr(settings, 'NEO4J_PASSWORD', "your-password"))
        )

    def close(self):
        """Close the Neo4j database driver."""
        self._driver.close()

    @staticmethod
    def _norm(value: Optional[str]) -> Optional[str]:
        if not value or not isinstance(value, str):
            return None
        return value.strip().lower()

    def create_or_update_resume(self, resume_data: Dict[str, Any]) -> str:
        """Create or update a resume node with skills, titles, companies, and schools.

        Expected resume_data keys:
          - id (str) [required]
          - file_name (str)
          - vector_id (str) [optional]
          - user_id (str)
          - skills: List[Dict{name, category, confidence}]
          - titles: List[str]                (normalized job titles)
          - experiences: List[Dict{company, role/title, start_year, end_year}]
          - education: List[Dict{school, degree}]
        """
        with self._driver.session() as session:
            try:
                # Create/Update Resume and Owner
                create_resume_query = """
                MERGE (r:Resume {id: $resume_id})
                SET r.file_name = $file_name,
                    r.vector_id = $vector_id,
                    r.updated_at = datetime()
                WITH r
                MERGE (u:User {id: $user_id})
                MERGE (u)-[:OWNS]->(r)
                // Clear existing relationships we manage
                WITH r
                OPTIONAL MATCH (r)-[old_rel:HAS_SKILL|HAS_TITLE|WORKED_AT|STUDIED_AT]->()
                DELETE old_rel
                RETURN r
                """
                session.run(
                    create_resume_query,
                    resume_id=resume_data['id'],
                    file_name=resume_data.get('file_name', ''),
                    vector_id=resume_data.get('vector_id', ''),
                    user_id=resume_data.get('user_id', 'unknown')
                )

                # Skills
                skills = resume_data.get('skills', []) or []
                if skills:
                    logger.info(f"Adding {len(skills)} skills for resume {resume_data['id']}")
                    skill_query = """
                    MATCH (r:Resume {id: $resume_id})
                    MERGE (s:Skill {name: $skill_name})
                    SET s.category = $skill_category,
                        s.updated_at = datetime()
                    MERGE (r)-[rel:HAS_SKILL]->(s)
                    SET rel.confidence = $skill_confidence,
                        rel.updated_at = datetime()
                    """
                    for skill in skills:
                        name = self._norm(skill.get('name'))
                        if not name:
                            continue
                        session.run(
                            skill_query,
                            resume_id=resume_data['id'],
                            skill_name=name,
                            skill_category=(skill.get('category') or '').strip(),
                            skill_confidence=float(skill.get('confidence', 1.0))
                        )

                # Titles
                titles = [self._norm(t) for t in (resume_data.get('titles') or []) if self._norm(t)]
                if titles:
                    title_query = """
                    MATCH (r:Resume {id: $resume_id})
                    MERGE (t:Title {name: $title_name})
                    SET t.updated_at = datetime()
                    MERGE (r)-[:HAS_TITLE]->(t)
                    """
                    for title in titles:
                        session.run(title_query, resume_id=resume_data['id'], title_name=title)

                # Experiences (WORKED_AT with properties, and ensure company node)
                experiences = resume_data.get('experiences', []) or []
                if experiences:
                    exp_query = """
                    MATCH (r:Resume {id: $resume_id})
                    MERGE (c:Company {name: $company_name})
                    SET c.updated_at = datetime()
                    MERGE (r)-[rel:WORKED_AT]->(c)
                    SET rel.role = $role,
                        rel.start_year = $start_year,
                        rel.end_year = $end_year,
                        rel.updated_at = datetime()
                    """
                    for exp in experiences:
                        company = self._norm(exp.get('company') or exp.get('organization') or exp.get('employer'))
                        role = self._norm(exp.get('role') or exp.get('title'))
                        if not company:
                            continue
                        session.run(
                            exp_query,
                            resume_id=resume_data['id'],
                            company_name=company,
                            role=role or '',
                            start_year=int(exp.get('start_year')) if str(exp.get('start_year') or '').isdigit() else None,
                            end_year=int(exp.get('end_year')) if str(exp.get('end_year') or '').isdigit() else None
                        )
                        # Also ensure title exists if role provided
                        if role:
                            session.run(
                                """
                                MATCH (r:Resume {id: $resume_id})
                                MERGE (t:Title {name: $title_name})
                                SET t.updated_at = datetime()
                                MERGE (r)-[:HAS_TITLE]->(t)
                                """,
                                resume_id=resume_data['id'],
                                title_name=role
                            )

                # Education (STUDIED_AT with degree property, and School node)
                education = resume_data.get('education', []) or []
                if education:
                    edu_query = """
                    MATCH (r:Resume {id: $resume_id})
                    MERGE (s:School {name: $school_name})
                    SET s.updated_at = datetime()
                    MERGE (r)-[rel:STUDIED_AT]->(s)
                    SET rel.degree = $degree,
                        rel.updated_at = datetime()
                    """
                    for edu in education:
                        school = self._norm(edu.get('school') or edu.get('university') or edu.get('institution'))
                        degree = (edu.get('degree') or '').strip()
                        if not school:
                            continue
                        session.run(
                            edu_query,
                            resume_id=resume_data['id'],
                            school_name=school,
                            degree=degree
                        )

                # Log a quick check
                result = session.run(
                    """
                    MATCH (r:Resume {id: $resume_id})
                    OPTIONAL MATCH (r)-[:HAS_SKILL]->(s:Skill)
                    OPTIONAL MATCH (r)-[:HAS_TITLE]->(t:Title)
                    OPTIONAL MATCH (r)-[:WORKED_AT]->(c:Company)
                    OPTIONAL MATCH (r)-[:STUDIED_AT]->(sch:School)
                    RETURN size(collect(distinct s)) as skills,
                           size(collect(distinct t)) as titles,
                           size(collect(distinct c)) as companies,
                           size(collect(distinct sch)) as schools
                    """,
                    resume_id=resume_data['id']
                ).single()
                logger.info(f"Resume {resume_data['id']} graph summary: {dict(result)}")
                return resume_data['id']

            except Exception as e:
                logger.error(f"Error creating/updating resume: {str(e)}")
                raise

    def find_similar_resumes(self, resume_id: str, min_skill_match: int = 1, limit: int = 5) -> List[Dict[str, Any]]:
        """Existing seed-based similarity (kept for compatibility)."""
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


    def find_resumes_by_query(self,
                              skills: List[str],
                              titles: List[str],
                              orgs: List[str],
                              limit: int = 10) -> List[Dict[str, Any]]:
        """Independent graph search using coverage × strength, with education bonus.

        Score = (MatchingSkills / RequiredSkills) * SkillStrengthFactor
        SkillStrengthFactor = 0.7*avg_confidence + 0.3*experience_strength
        experience_strength = min(total_years_across_WORKED_AT / 8, 1)
        Education bonus: +0.15 for (phd/master/msc), +0.10 for relevant fields (cs/data/ai/ml)
        Final similarity_score = Score * (1 + edu_bonus)
        """
        skills = [self._norm(s) for s in (skills or []) if self._norm(s)]
        titles = [self._norm(t) for t in (titles or []) if self._norm(t)]
        orgs = [self._norm(o) for o in (orgs or []) if self._norm(o)]

        with self._driver.session() as session:
            try:
                query = """
                MATCH (r:Resume)
                WITH r, $skills AS q_skills, $titles AS q_titles, $orgs AS q_orgs

                // Matched skills and confidences
                OPTIONAL MATCH (r)-[hs:HAS_SKILL]->(s:Skill)
                WHERE size(q_skills) > 0 AND s.name IN q_skills
                WITH r, q_skills,
                     collect(DISTINCT s.name) AS matched_skills,
                     collect(hs.confidence)  AS confs

                // Titles (for display only)
                OPTIONAL MATCH (r)-[:HAS_TITLE]->(t:Title)
                WITH r, q_skills, matched_skills, confs,
                     collect(DISTINCT toLower(t.name)) AS matched_titles

                // Companies and work rels for experience years (display + years)
                OPTIONAL MATCH (r)-[w:WORKED_AT]->(c:Company)
                WITH r, q_skills, matched_skills, confs, matched_titles,
                     collect(DISTINCT toLower(c.name)) AS companies,
                     collect(w) AS workrels

                // Schools and degrees (for edu bonus)
                OPTIONAL MATCH (r)-[st:STUDIED_AT]->(sch:School)
                WITH r, q_skills, matched_skills, confs, matched_titles, companies, workrels,
                     collect(DISTINCT toLower(sch.name)) AS schools,
                     collect( toLower(coalesce(st.degree,'')) ) AS degrees

                // Aggregate orgs for display
                WITH r, q_skills, matched_skills, confs, matched_titles,
                     (companies + schools) AS matched_orgs,
                     degrees, workrels,
                     size(q_skills) AS required_skills,
                     size(matched_skills) AS matching_skills

                // Compute total years of experience
                WITH r, matched_skills, confs, matched_titles, matched_orgs, degrees,
                     required_skills, matching_skills,
                     reduce(total=0, w IN workrels |
                           total + CASE
                                     WHEN w.start_year IS NOT NULL
                                     THEN toInteger(coalesce(w.end_year, date().year)) - toInteger(w.start_year)
                                     ELSE 0
                                   END) AS years_total

                // Compute average confidence and normalized experience strength
                WITH r, matched_skills, matched_titles, matched_orgs, degrees,
                     required_skills, matching_skills, years_total, confs,
                     CASE
                       WHEN size(confs) > 0
                       THEN reduce(sum=0.0, c IN confs | sum + toFloat(c)) / toFloat(size(confs))
                       ELSE 0.8
                     END AS avg_conf,
                     CASE
                       WHEN years_total >= 8 THEN 1.0
                       ELSE toFloat(years_total)/8.0
                     END AS exp_strength

                // Education bonus from degrees
                WITH r, matched_skills, matched_titles, matched_orgs,
                     required_skills, matching_skills, avg_conf, exp_strength,
                     CASE
                       WHEN any(d IN degrees WHERE d CONTAINS 'phd' OR d CONTAINS 'master' OR d CONTAINS 'msc') THEN 0.15
                       WHEN any(d IN degrees WHERE d CONTAINS 'computer' OR d CONTAINS 'data' OR d CONTAINS 'ai' OR d CONTAINS 'machine') THEN 0.10
                       ELSE 0.0
                     END AS edu_bonus

                // Coverage and strength
                WITH r, matched_skills, matched_titles, matched_orgs, edu_bonus,
                     CASE
                       WHEN required_skills = 0 THEN 0.0
                       ELSE toFloat(matching_skills)/toFloat(required_skills)
                     END AS skill_coverage,
                     0.7*avg_conf + 0.3*exp_strength AS ssf

                // Final score
                WITH r, matched_skills, matched_titles, matched_orgs,
                     (skill_coverage * ssf) * (1.0 + edu_bonus) AS similarity_score

                WHERE similarity_score > 0.0
                RETURN r.id AS resume_id,
                       r.file_name AS file_name,
                       similarity_score,
                       matched_skills AS shared_skills,
                       matched_titles AS matched_titles,
                       matched_orgs AS matched_orgs
                ORDER BY similarity_score DESC
                LIMIT $limit
                """
                rows = session.run(query, skills=skills, titles=titles, orgs=orgs, limit=limit)
                return [dict(record) for record in rows]
            except Exception as e:
                logger.error(f"Error in independent graph search: {str(e)}")
                return []


    def delete_resume(self, resume_id: str):
        """Delete a resume and its relationships."""
        with self._driver.session() as session:
            try:
                session.run(
                    """
                    MATCH (r:Resume {id: $resume_id})
                    OPTIONAL MATCH (r)-[rel]-()
                    DELETE rel, r
                    """,
                    resume_id=resume_id
                )
                logger.info(f"Deleted resume {resume_id} from Neo4j")
            except Exception as e:
                logger.error(f"Error deleting resume: {str(e)}")
                raise

    def get_resume_skills(self, resume_id: str) -> List[Dict[str, Any]]:
        """Get all skills associated with a resume."""
        with self._driver.session() as session:
            try:
                results = session.run(
                    """
                    MATCH (r:Resume {id: $resume_id})-[rel:HAS_SKILL]->(s:Skill)
                    RETURN s.name as name,
                           s.category as category,
                           rel.confidence as confidence
                    ORDER BY s.category, s.name
                    """,
                    resume_id=resume_id
                )
                return [dict(record) for record in results]
            except Exception as e:
                logger.error(f"Error getting resume skills: {str(e)}")
                return []