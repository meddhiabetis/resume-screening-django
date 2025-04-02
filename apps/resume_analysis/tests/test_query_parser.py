import unittest
from ..services.query_parser import QueryParser

class TestQueryParser(unittest.TestCase):
    def setUp(self):
        self.qp = QueryParser()

    def test_basic_text_search(self):
        query, section = self.qp.parse_query("Find resumes with Python experience")
        self.assertEqual(query, "find resumes with python")
        self.assertEqual(section, "experience")

    def test_section_specific_search(self):
        query, section = self.qp.parse_query("Show me skills in Java")
        self.assertEqual(query, "show me in java")
        self.assertEqual(section, "skills")

    def test_default_section_search(self):
        query, section = self.qp.parse_query("Data science projects")
        self.assertEqual(query, "data science projects")
        self.assertEqual(section, "full_text")

if __name__ == '__main__':
    unittest.main()