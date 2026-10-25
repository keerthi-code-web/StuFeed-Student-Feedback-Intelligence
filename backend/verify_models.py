import sys
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import AgglomerativeClustering

print(f"Python version: {sys.version}")
print(f"PyTorch version: {torch.__version__}, CUDA available: {torch.cuda.is_available()}")

# 1. Verify Sentiment Model
SENTIMENT_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
print(f"\n--- Loading Sentiment Model: {SENTIMENT_MODEL_NAME} ---")
sentiment_tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL_NAME)
sentiment_model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL_NAME)
sentiment_model.eval()

# Check labels
# cardiffnlp/twitter-roberta-base-sentiment-latest mapping:
# config.id2label: 0 -> Negative, 1 -> Neutral, 2 -> Positive
labels = sentiment_model.config.id2label
print("Model id2label mapping:", labels)

test_sentences = [
    "The instructor explains concepts clearly.",
    "The computer laboratory needs better equipment.",
    "The class moves too quickly.",
    "The teaching is excellent, but the lecture pace is too fast."
]

print("\n--- Running Sentiment Inference ---")
for text in test_sentences:
    inputs = sentiment_tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = sentiment_model(**inputs)
        scores = torch.softmax(outputs.logits, dim=1)[0].numpy()
        pred_idx = int(np.argmax(scores))
        pred_label = labels.get(pred_idx, str(pred_idx))
        confidence = float(scores[pred_idx])
        print(f"Text: '{text}' -> {pred_label} (Confidence: {confidence:.4f}) [neg: {scores[0]:.3f}, neu: {scores[1]:.3f}, pos: {scores[2]:.3f}]")

# 2. Verify Sentence Transformer Embeddings
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"\n--- Loading Embedding Model: {EMBEDDING_MODEL_NAME} ---")
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

pace_comments = [
    "The class moves too quickly.",
    "The lecturer rushes through the concepts.",
    "Please explain the lessons more slowly."
]
lab_comments = [
    "The computer laboratory needs better equipment.",
    "Several computers in the lab are not working.",
    "We need more functional systems for practical work."
]
all_comments = pace_comments + lab_comments

print(f"\n--- Generating Embeddings for {len(all_comments)} comments ---")
embeddings = embedder.encode(all_comments, convert_to_numpy=True, normalize_embeddings=True)
print(f"Embeddings shape: {embeddings.shape}")

# Test clustering
clustering = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=0.5,
    metric="cosine",
    linkage="average"
)
cluster_ids = clustering.fit_predict(embeddings)
print("Cluster assignments:")
for comment, cid in zip(all_comments, cluster_ids):
    print(f"  Cluster {cid}: '{comment}'")

print("\n=== All basic NLP tests passed successfully! ===")
