class RelevanceScorer:
    def __init__(self):
        pass

    def score_results(self, results):
        # Example scoring logic, to be refined as needed
        for result in results:
            result['relevance_score'] = self.calculate_relevance(result['similarity_score'], result['section_type'])
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results

    def calculate_relevance(self, similarity_score, section_type):
        # Basic example: weight different sections differently
        weight = {'skills': 1.2, 'experience': 1.0, 'education': 0.8, 'projects': 1.0, 'full_text': 0.9}
        return similarity_score * weight.get(section_type, 1.0)

# Example usage
if __name__ == "__main__":
    rs = RelevanceScorer()
    results = [{'similarity_score': 0.9, 'section_type': 'skills'}, {'similarity_score': 0.85, 'section_type': 'experience'}]
    scored_results = rs.score_results(results)
    print(scored_results)