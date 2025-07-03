"""
Module for scoring the relevance of resume analysis results.
"""

class RelevanceScorer:
    """
    A class to score the relevance of resume analysis results based on similarity scores and section types.

    Methods
    -------
    score_results(results):
        Scores the provided results and sorts them by relevance score.

    calculate_relevance(similarity_score, section_type):
        Calculates the relevance score based on similarity score and section type.
    """

    def __init__(self):
        """Initializes the RelevanceScorer instance."""
        pass

    def score_results(self, results):
        """
        Scores the provided results and sorts them by relevance score.

        Parameters
        ----------
        results : list of dict
            A list of dictionaries containing 'similarity_score' and 'section_type'.

        Returns
        -------
        list of dict
            The input results sorted by their relevance score in descending order.
        """
        for result in results:
            result['relevance_score'] = self.calculate_relevance(result['similarity_score'], result['section_type'])
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results

    def calculate_relevance(self, similarity_score, section_type):
        """
        Calculates the relevance score based on similarity score and section type.

        Parameters
        ----------
        similarity_score : float
            The similarity score of the result.
        section_type : str
            The type of section (e.g., 'skills', 'experience').

        Returns
        -------
        float
            The calculated relevance score.
        """
        weight = {'skills': 1.2, 'experience': 1.0, 'education': 0.8, 'projects': 1.0, 'full_text': 0.9}
        return similarity_score * weight.get(section_type, 1.0)

# Example usage
if __name__ == "__main__":
    rs = RelevanceScorer()
    results = [{'similarity_score': 0.9, 'section_type': 'skills'}, {'similarity_score': 0.85, 'section_type': 'experience'}]
    scored_results = rs.score_results(results)
    print(scored_results)