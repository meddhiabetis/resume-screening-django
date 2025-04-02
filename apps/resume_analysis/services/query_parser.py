import re

class QueryParser:
    def __init__(self):
        pass

    def parse_query(self, query: str):
        # Example parsing logic, can be extended as needed
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