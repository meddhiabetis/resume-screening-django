from sentence_transformers import SentenceTransformer

# Load and save model in a specific directory
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
model.save("models/mpnet")  # Save locally

print("Model downloaded and saved to 'models/mpnet'")