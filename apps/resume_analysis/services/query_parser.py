import re

class QueryParser:
    """A class to parse search queries for resume screening.

    This class provides functionality to parse a query string and
    identify specific sections such as skills, experience, education,
    projects, or full text.

    Attributes:
        None
    """

    def __init__(self):
        """Initializes the QueryParser instance."""
        pass

    def parse_query(self, query: str):
        """Parses the input query string to extract relevant sections.

        Args:
            query (str): The query string to be parsed.

        Returns:
            tuple: A tuple containing the cleaned query string and the
            identified section (e.g., skills, experience, etc.).
        """
        query = query.lower().strip()
        # Extract specific sections if mentioned
        section_keywords = ['skills', 'experience', 'education', 'projects', 'full_text']
        sections = [kw for kw in section_keywords if kw in query]
        if sections:
            section = sections[0]
            query = query.replace(section, '').strip()
        else:
            section = 'full_text'
        
        return query, section

# Example usage
if __name__ == "__main__":
    qp = QueryParser()
    query, section = qp.parse_query("Search for Python skills")
    print(query, section)  # Output: "search for python" "skills"