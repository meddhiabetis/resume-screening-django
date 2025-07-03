class ResultAggregator:
    """A class to aggregate results from primary and secondary sources.

    Methods
    -------
    aggregate_results(primary_results, secondary_results):
        Aggregates primary and secondary results into a single list.
    """

    def __init__(self):
        """Initializes the ResultAggregator instance."""
        pass

    def aggregate_results(self, primary_results, secondary_results):
        """Aggregates primary and secondary results.

        Parameters
        ----------
        primary_results : list
            A list of dictionaries containing primary results.
        secondary_results : list
            A list of dictionaries containing secondary results.

        Returns
        -------
        list
            A combined list of all results from primary and secondary sources.
        """
        all_results = primary_results + secondary_results
        return all_results

# Example usage
if __name__ == "__main__":
    ra = ResultAggregator()
    primary_results = [{'resume_id': 1, 'similarity_score': 0.9, 'section_type': 'skills'}]
    secondary_results = [{'resume_id': 2, 'similarity_score': 0.85, 'section_type': 'experience'}]
    aggregated_results = ra.aggregate_results(primary_results, secondary_results)
    print(aggregated_results)