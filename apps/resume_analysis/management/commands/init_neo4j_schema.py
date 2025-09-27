from django.core.management.base import BaseCommand
from apps.resume_analysis.services.neo4j_service import Neo4jService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Initialize Neo4j constraints and indexes for the resume graph."

    def handle(self, *args, **options):
        try:
            neo4j = Neo4jService()
            with neo4j._driver.session() as session:
                # Constraints (ensure uniqueness)
                constraints = [
                    "CREATE CONSTRAINT resume_id IF NOT EXISTS FOR (r:Resume) REQUIRE r.id IS UNIQUE",
                    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
                    "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
                    "CREATE CONSTRAINT title_name IF NOT EXISTS FOR (t:Title) REQUIRE t.name IS UNIQUE",
                    "CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
                    "CREATE CONSTRAINT school_name IF NOT EXISTS FOR (s:School) REQUIRE s.name IS UNIQUE",
                ]
                for constraint in constraints:
                    try:
                        session.run(constraint)
                        self.stdout.write(self.style.SUCCESS(f"Created/ensured: {constraint}"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Constraint ensure failed or exists: {e}"))

                # Optional indexes (non-unique)
                indexes = [
                    "CREATE INDEX resume_file_name IF NOT EXISTS FOR (r:Resume) ON (r.file_name)",
                    "CREATE INDEX skill_category IF NOT EXISTS FOR (s:Skill) ON (s.category)",
                ]
                for index in indexes:
                    try:
                        session.run(index)
                        self.stdout.write(self.style.SUCCESS(f"Created/ensured: {index}"))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Index ensure failed or exists: {e}"))

            self.stdout.write(self.style.SUCCESS("Neo4j schema initialized successfully."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error initializing Neo4j schema: {e}"))
            logger.exception("Neo4j schema initialization failed")