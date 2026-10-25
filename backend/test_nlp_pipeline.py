import sys
import os

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.nlp.sentiment import sentiment_analyzer
from app.nlp.topic_clustering import topic_clusterer
from app.nlp.pipeline import compute_topic_clusters

TEST_DATA = [
    # Teaching pace
    {"id": 1, "text": "The class moves too quickly.", "category": "Teaching pace", "expected_sentiment": "Negative"},
    {"id": 2, "text": "The lecturer rushes through the concepts.", "category": "Teaching pace", "expected_sentiment": "Negative"},
    {"id": 3, "text": "Please explain the lessons more slowly.", "category": "Teaching pace", "expected_sentiment": "Neutral/Negative"},
    # Laboratory
    {"id": 4, "text": "The computer laboratory needs better equipment.", "category": "Laboratory", "expected_sentiment": "Negative/Neutral"},
    {"id": 5, "text": "Several computers in the lab are not working.", "category": "Laboratory", "expected_sentiment": "Negative"},
    {"id": 6, "text": "We need more functional systems for practical work.", "category": "Laboratory", "expected_sentiment": "Negative/Neutral"},
    # Practical sessions
    {"id": 7, "text": "We need more hands-on practice.", "category": "Practical sessions", "expected_sentiment": "Neutral"},
    {"id": 8, "text": "Please provide more practical exercises.", "category": "Practical sessions", "expected_sentiment": "Neutral"},
    {"id": 9, "text": "There is not enough time to practise after theory.", "category": "Practical sessions", "expected_sentiment": "Negative"},
    # Grading
    {"id": 10, "text": "The grading criteria were not explained clearly.", "category": "Grading", "expected_sentiment": "Negative"},
    {"id": 11, "text": "We need clearer feedback on our marks.", "category": "Grading", "expected_sentiment": "Neutral/Negative"},
    # Positive teaching
    {"id": 12, "text": "The instructor explains concepts clearly.", "category": "Positive teaching", "expected_sentiment": "Positive"},
    {"id": 13, "text": "The teaching sessions are very helpful.", "category": "Positive teaching", "expected_sentiment": "Positive"},
    # Mixed feedback
    {"id": 14, "text": "The teaching is excellent, but the lecture pace is too fast.", "category": "Mixed feedback", "expected_sentiment": "Neutral (Mixed)"},
    {"id": 15, "text": "The laboratory is useful, although some equipment needs improvement.", "category": "Mixed feedback", "expected_sentiment": "Neutral (Mixed)"},
    # Negative feedback
    {"id": 16, "text": "The laboratory equipment is poor.", "category": "Negative feedback", "expected_sentiment": "Negative"},
    {"id": 17, "text": "The lessons are difficult to follow.", "category": "Negative feedback", "expected_sentiment": "Negative"}
]

def run_tests():
    print("=" * 60)
    print("RUNNING REAL NLP EVALUATION SUITE ON REQUIRED TEST CASES")
    print("=" * 60)
    
    # Initialize models
    sentiment_analyzer.initialize()
    topic_clusterer.initialize()

    # 1. Sentiment Evaluation
    print("\n[PART 1: REAL SENTIMENT INFERENCE RESULTS]")
    formatted_submissions = []
    
    for item in TEST_DATA:
        res = sentiment_analyzer.analyze(item["text"])
        formatted_submissions.append({
            "id": item["id"],
            "subject_name": "Test Subject",
            "instructor_name": "Test Instructor",
            "rating": 3,
            "feedback_text": item["text"],
            "sentiment_label": res["sentiment_label"],
            "sentiment_detail": res["sentiment_detail"],
            "sentiment_confidence": res["sentiment_confidence"],
            "sentiment_scores": res["sentiment_scores"],
            "is_mixed": res["is_mixed"],
            "created_at": "2026-10-24T22:00:00"
        })
        mixed_tag = " [MIXED SENTIMENT DETECTED]" if res["is_mixed"] else ""
        print(f"ID {item['id']:2d} | Category: {item['category']:<18} | Text: \"{item['text']}\"")
        print(f"      -> Predicted: {res['sentiment_detail']} (Conf: {res['sentiment_confidence']:.4f}){mixed_tag}")
        if res["clause_analysis"]:
            for c in res["clause_analysis"]:
                print(f"         Clause: \"{c['clause']}\" -> {c['predicted_label']} ({c['confidence']:.3f})")

    # 2. Topic Intelligence & Clustering Evaluation
    print("\n" + "=" * 60)
    print("[PART 2: REAL TOPIC INTELLIGENCE & CLUSTERING RESULTS]")
    print("=" * 60)
    clusters = compute_topic_clusters(formatted_submissions)
    print(f"Total Clusters Discovered: {len(clusters)}\n")

    for c in clusters:
        print(f"Cluster #{c['cluster_id']} - Topic: \"{c['topic_label']}\"")
        print(f"  Comment Count: {c['comment_count']}")
        print(f"  Top Keywords: {c['top_keywords']}")
        print(f"  Sentiment Distribution: Pos={c['sentiment_distribution']['positive']}, Neg={c['sentiment_distribution']['negative']}, Neu={c['sentiment_distribution']['neutral']}")
        print(f"  Representative Comment: \"{c['representative_comments'][0]}\"")
        print("  Supporting Comments:")
        for sc in c["supporting_comments"]:
            print(f"    - \"{sc['feedback_text']}\" ({sc['sentiment_detail']})")
        print("-" * 60)

    print("\nTEST SUITE EXECUTION FINISHED.")

if __name__ == "__main__":
    run_tests()
