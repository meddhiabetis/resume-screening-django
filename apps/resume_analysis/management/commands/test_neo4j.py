from django.core.management.base import BaseCommand
from apps.resume_analysis.utils.neo4j_test import test_neo4j_connection

class Command(BaseCommand):
    help = 'Test Neo4j connection'

    def handle(self, *args, **options):
        try:
            success = test_neo4j_connection()
            if success:
                self.stdout.write(
                    self.style.SUCCESS('Successfully connected to Neo4j')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to connect to Neo4j')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error testing Neo4j connection: {str(e)}')
            )