class ResultAggregator:
    def __init__(self):
        pass

    def aggregate_results(self, primary_results, secondary_results):
        # Example aggregation logic, can be extended as needed
        all_results = primary_results + secondary_results
        return all_results

# Example usage
if __name__ == "__main__":
    ra = ResultAggregator()
    primary_results = [{'resume_id': 1, 'similarity_score': 0.9, 'section_type': 'skills'}]
    secondary_results = [{'resume_id': 2, 'similarity_score': 0.85, 'section_type': 'experience'}]
    aggregated_results = ra.aggregate_results(primary_results, secondary_results)
    print(aggregated_results)