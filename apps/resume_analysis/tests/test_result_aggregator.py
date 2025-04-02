import unittest
from ..services.result_aggregator import ResultAggregator
from ..services.relevance_scorer import RelevanceScorer

class TestResultAggregator(unittest.TestCase):
    def setUp(self):
        self.ra = ResultAggregator()
        self.rs = RelevanceScorer()

    def test_aggregation_and_ranking(self):
        primary_results = [{'resume_id': 1, 'similarity_score': 0.9, 'section_type': 'skills'}]
        secondary_results = [{'resume_id': 2, 'similarity_score': 0.85, 'section_type': 'experience'}]
        aggregated_results = self.ra.aggregate_results(primary_results, secondary_results)
        ranked_results = self.rs.score_results(aggregated_results)
        self.assertEqual(len(ranked_results), 2)
        self.assertGreater(ranked_results[0]['relevance_score'], ranked_results[1]['relevance_score'])

if __name__ == '__main__':
    unittest.main()