# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         HDBSCAN Clustering Service
# =======================================================================

import numpy as np
import hdbscan
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClusteringService:
    def __init__(self, min_cluster_size: int = 5, min_samples: int = 3, metric: str = 'euclidean'):
        """
        Initialize clustering service using HDBSCAN.
        
        Args:
            min_cluster_size: Minimum size of clusters
            min_samples: Measure of how conservative the clustering is
            metric: Distance metric to use
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.metric = metric
        self.model = None
        self.labels_ = []
        
    def fit_predict(self, embeddings: List[List[float]]) -> List[int]:
        """
        Cluster embeddings and return cluster IDs.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            List of cluster IDs (-1 indicates noise)
        """
        if not embeddings:
            logger.warning("No embeddings provided for clustering")
            return []
            
        if len(embeddings) < self.min_cluster_size:
            logger.warning(f"Not enough data ({len(embeddings)}) for clustering (min_size={self.min_cluster_size}). Returning noise.")
            # Return all as noise (-1) if not enough data
            return [-1] * len(embeddings)
            
        X = np.array(embeddings)
        
        # Initialize HDBSCAN
        # cluster_selection_method='eom' (Excess of Mass) is generally better for variable density
        self.model = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric=self.metric,
            cluster_selection_method='eom'
        )
        
        self.labels_ = self.model.fit_predict(X)
        
        # Calculate stats
        n_clusters = len(set(self.labels_)) - (1 if -1 in self.labels_ else 0)
        n_noise = list(self.labels_).count(-1)
        
        logger.info(f"HDBSCAN found {n_clusters} clusters and {n_noise} noise points from {len(embeddings)} items")
        
        return self.labels_.tolist()

    def generate_cluster_names(self, all_data: List[dict], cluster_labels: List[int]) -> dict:
        """
        Generate semantic names for clusters using TF-IDF.
        
        Args:
            all_data: List of {id, vector, metadata} from Qdrant
            cluster_labels: List of cluster IDs for each chunk
        
        Returns:
            dict: {cluster_id: "Cluster Name"}
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        cluster_names = {}
        
        # Group chunks by cluster
        cluster_texts = {}
        for item, label in zip(all_data, cluster_labels):
            if label not in cluster_texts:
                cluster_texts[label] = []
            
            # Get text from metadata
            metadata = item.get('metadata', {})
            # Try 'text' field, fallback to 'content' or empty string
            text = metadata.get('text') or metadata.get('content') or ''
            if text:
                cluster_texts[label].append(text)
        
        # Generate names for each cluster
        for cluster_id, texts in cluster_texts.items():
            if cluster_id == -1:
                cluster_names[-1] = "Uncategorized"
                continue
            
            if not texts or len(texts) < 2:
                # Not enough text, use generic name
                cluster_names[cluster_id] = f"Cluster {cluster_id}"
                continue
            
            # Combine all text from this cluster
            corpus = texts
            
            # Extract keywords
            # Use a try-except block in case of empty vocabulary or other sklearn errors
            try:
                # Adjust parameters for small clusters
                n_docs = len(corpus)
                min_df = 2 if n_docs >= 5 else 1
                max_df = 0.8 if n_docs >= 5 else 1.0
                
                vectorizer = TfidfVectorizer(
                    max_features=5,
                    stop_words='english',
                    ngram_range=(1, 2),  # Allow 1-2 word phrases
                    min_df=min_df,       # Ignore very rare words
                    max_df=max_df        # Ignore very common words
                )
                
                vectorizer.fit(corpus)
                keywords = vectorizer.get_feature_names_out()
                
                if len(keywords) == 0:
                     cluster_names[cluster_id] = f"Cluster {cluster_id}"
                     continue

                # Take top 3, capitalize, join
                top_keywords = [k.title() for k in keywords[:3]]
                name = " & ".join(top_keywords)
                
                cluster_names[cluster_id] = name
                
            except Exception as e:
                logger.warning(f"Failed to generate name for cluster {cluster_id}: {e}")
                cluster_names[cluster_id] = f"Cluster {cluster_id}"
        
        return cluster_names
