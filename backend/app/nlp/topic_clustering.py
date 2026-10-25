import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from app.config import settings

logger = logging.getLogger(__name__)

# Stop words tailored for academic student feedback to highlight actionable topics
CUSTOM_STOP_WORDS = {
    "student", "students", "class", "classes", "session", "sessions", "lesson", "lessons",
    "course", "subject", "teacher", "instructor", "lecturer", "professor",
    "please", "need", "needs", "needed", "make", "makes", "give", "gives", "provide", "provides",
    "good", "bad", "great", "excellent", "poor", "very", "much", "also", "well", "lot", "bit",
    "really", "quite", "too", "more", "less", "many", "enough", "get", "got", "can", "could",
    "would", "should", "one", "two", "way", "feel", "feels", "like", "just", "even"
}

class TopicClusterer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TopicClusterer, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return
        logger.info(f"Loading Sentence Embedding Model: {settings.EMBEDDING_MODEL_NAME}")
        self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        self.initialized = True
        logger.info("Sentence Embedding Model loaded successfully")

    def encode(self, texts: List[str]) -> np.ndarray:
        if not self.initialized:
            self.initialize()
        # Returns normalized embeddings so that dot product equals cosine similarity
        return self.embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def _generate_topic_label(self, texts: List[str]) -> Tuple[str, List[str]]:
        """
        Uses TF-IDF unigrams and bigrams to generate a data-driven topic label
        from the actual comments within a cluster.
        """
        if not texts:
            return "General Feedback", []

        # Combine English stopwords with feedback specific generic terms
        from sklearn.feature_extraction import text
        all_stop_words = list(text.ENGLISH_STOP_WORDS.union(CUSTOM_STOP_WORDS))

        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words=all_stop_words,
                max_features=25,
                token_pattern=r'(?u)\b[a-zA-Z]{3,}\b'
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Sum TF-IDF scores across cluster documents
            scores = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
            sorted_indices = np.argsort(scores)[::-1]
            
            top_keywords = []
            for idx in sorted_indices:
                term = feature_names[idx]
                if len(term.strip()) > 2 and term not in top_keywords:
                    top_keywords.append(term)
                if len(top_keywords) >= 5:
                    break

            if not top_keywords:
                # Fallback to simple words if all terms were filtered
                simple_words = [w.capitalize() for w in re.findall(r'\b[A-Za-z]{4,}\b', " ".join(texts))[:3]]
                label = " / ".join(simple_words) if simple_words else "General Observations"
                return label, simple_words

            # Formulate title from top 2 salient keywords / bigrams
            salient = [k.title() for k in top_keywords[:2]]
            label = " & ".join(salient) if len(salient) > 1 else salient[0]
            return label, top_keywords
        except Exception as e:
            logger.warning(f"TF-IDF topic labeling exception: {e}")
            # Fallback simple keyword extraction
            words = [w.title() for w in re.findall(r'\b[A-Za-z]{4,}\b', " ".join(texts))[:2]]
            label = " / ".join(words) if words else "Feedback Topic"
            return label, words

    def cluster_feedback(self, submissions: List[Dict[str, Any]], distance_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Performs semantic clustering on feedback records using sentence embeddings
        and cosine distance.
        """
        if distance_threshold is None:
            distance_threshold = settings.CLUSTERING_DISTANCE_THRESHOLD
        if not submissions:
            return []

        if not self.initialized:
            self.initialize()

        texts = [s["feedback_text"] for s in submissions]

        # Case of 1 submission
        if len(texts) == 1:
            label, keywords = self._generate_topic_label(texts)
            item = submissions[0]
            sent_label = item.get("sentiment_label", "Neutral")
            return [{
                "cluster_id": 0,
                "topic_label": label,
                "comment_count": 1,
                "sentiment_distribution": {
                    "positive": 1 if sent_label == "Positive" else 0,
                    "negative": 1 if sent_label == "Negative" else 0,
                    "neutral": 1 if sent_label == "Neutral" else 0
                },
                "representative_comments": [texts[0]],
                "supporting_comments": [item],
                "top_keywords": keywords,
                "departments": [item.get("department_name", "Other")] if item.get("department_name") else [],
                "subjects": [item.get("subject_name", "")] if item.get("subject_name") else [],
                "instructors": [item.get("instructor_name", "")] if item.get("instructor_name") else []
            }]

        # Generate embeddings
        embeddings = self.encode(texts)

        # Agglomerative clustering with cosine metric and average linkage
        # Cosine distance = 1 - cosine_similarity
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="cosine",
            linkage="average"
        )
        labels = clustering.fit_predict(embeddings)

        clusters_map: Dict[int, List[int]] = {}
        for idx, cluster_label in enumerate(labels):
            clusters_map.setdefault(cluster_label, []).append(idx)

        # Sort clusters by size (largest first)
        sorted_clusters = sorted(clusters_map.items(), key=lambda x: len(x[1]), reverse=True)

        results = []
        for new_cid, (orig_label, doc_indices) in enumerate(sorted_clusters):
            cluster_texts = [texts[i] for i in doc_indices]
            cluster_subs = [submissions[i] for i in doc_indices]
            cluster_embeddings = embeddings[doc_indices]

            # Find representative comment (closest to cluster centroid)
            centroid = np.mean(cluster_embeddings, axis=0, keepdims=True)
            centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-9)
            cos_sims = np.dot(cluster_embeddings, centroid_norm.T).flatten()
            medoid_idx = doc_indices[int(np.argmax(cos_sims))]
            rep_comment = texts[medoid_idx]

            # Generate keyword topic label
            topic_label, keywords = self._generate_topic_label(cluster_texts)

            # Calculate sentiment breakdown
            pos_count = sum(1 for s in cluster_subs if s.get("sentiment_label") == "Positive")
            neg_count = sum(1 for s in cluster_subs if s.get("sentiment_label") == "Negative")
            neu_count = sum(1 for s in cluster_subs if s.get("sentiment_label") == "Neutral")

            departments = sorted(list(set(s.get("department_name", "") for s in cluster_subs if s.get("department_name"))))
            subjects = sorted(list(set(s.get("subject_name", "") for s in cluster_subs if s.get("subject_name"))))
            instructors = sorted(list(set(s.get("instructor_name", "") for s in cluster_subs if s.get("instructor_name"))))

            results.append({
                "cluster_id": new_cid,
                "topic_label": topic_label,
                "comment_count": len(cluster_subs),
                "sentiment_distribution": {
                    "positive": pos_count,
                    "negative": neg_count,
                    "neutral": neu_count
                },
                "representative_comments": [rep_comment],
                "supporting_comments": cluster_subs,
                "top_keywords": keywords,
                "departments": departments,
                "subjects": subjects,
                "instructors": instructors
            })

        return results

topic_clusterer = TopicClusterer()
