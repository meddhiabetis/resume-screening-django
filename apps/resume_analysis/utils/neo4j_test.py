import os
import sys
import django
from neo4j import GraphDatabase
import logging

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

from django.conf import settings

logger = logging.getLogger(__name__)

def test_neo4j_connection():
    """Test Neo4j connection and basic operations"""
    driver = None
    try:
        # Get Neo4j settings
        uri = getattr(settings, 'NEO4J_URI', "bolt://localhost:7687")
        user = getattr(settings, 'NEO4J_USER', "neo4j")
        password = getattr(settings, 'NEO4J_PASSWORD', "your-password")  # Replace with your password

        print(f"Attempting to connect to Neo4j at {uri}")
        
        # Create driver
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 AS num").single()
            if result and result.get("num") == 1:
                print("Successfully connected to Neo4j!")
                return True
            else:
                print("Connection test failed - unexpected result")
                return False

    except Exception as e:
        print(f"Failed to connect to Neo4j: {str(e)}")
        return False
    
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    success = test_neo4j_connection()
    print("Connection test:", "SUCCESS" if success else "FAILED")