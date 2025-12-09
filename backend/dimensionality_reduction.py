# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Dimensionality reduction service
# =======================================================================

import numpy as np
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from sklearn.decomposition import PCA
import pickle
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DimensionalityReducer:
    """
    Handles dimensionality reduction of high-dimensional embeddings to 3D
    using PCA (default) or UMAP.
    """
    
    def __init__(self, method: str = 'pca', n_components: int = 3):
        """
        Initialize the dimensionality reducer.
        
        Args:
            method: 'pca' or 'umap'
            n_components: Number of dimensions to reduce to (default 3)
        """
        self.method = method.lower()
        self.n_components = n_components
        self.transformer = None
        self.is_fitted = False
        
        if self.method not in ['pca', 'umap']:
            logger.warning(f"Unknown method '{method}', defaulting to 'pca'")
            self.method = 'pca'
            
        # Try to import UMAP if requested
        if self.method == 'umap':
            try:
                import umap
                self._umap_lib = umap
            except ImportError:
                logger.warning("umap-learn not installed. Falling back to PCA.")
                self.method = 'pca'

    def fit_transform(self, embeddings: List[List[float]]) -> np.ndarray:
        """
        Fit the model on the provided embeddings and return the 3D coordinates.
        
        Args:
            embeddings: List of high-dimensional embedding vectors
            
        Returns:
            Numpy array of shape (n_samples, 3) containing 3D coordinates
        """
        if not embeddings:
            logger.warning("No embeddings provided to fit_transform")
            return np.array([])
            
        X = np.array(embeddings)
        
        # Handle case with too few samples
        n_samples = X.shape[0]
        if n_samples < self.n_components:
            logger.warning(f"Not enough samples ({n_samples}) for {self.n_components} components. Padding with zeros.")
            if n_samples == 0:
                return np.array([])
            
            # If we have at least 1 sample but fewer than n_components, PCA will fail if we ask for more components than samples
            # So we'll use min(n_samples, n_components) for fitting, then pad output
            actual_components = min(n_samples, self.n_components)
            
            if self.method == 'pca':
                temp_transformer = PCA(n_components=actual_components)
                reduced = temp_transformer.fit_transform(X)
                self.transformer = temp_transformer # Save it even if partial
            else:
                # UMAP needs more samples usually, fallback to PCA logic for tiny datasets
                temp_transformer = PCA(n_components=actual_components)
                reduced = temp_transformer.fit_transform(X)
                self.transformer = temp_transformer
                
            self.is_fitted = True
            
            # Pad columns if needed to reach n_components
            if actual_components < self.n_components:
                padding = np.zeros((n_samples, self.n_components - actual_components))
                reduced = np.hstack((reduced, padding))
                
            return reduced

        try:
            if self.method == 'pca':
                self.transformer = PCA(n_components=self.n_components)
                reduced = self.transformer.fit_transform(X)
            elif self.method == 'umap':
                self.transformer = self._umap_lib.UMAP(
                    n_components=self.n_components,
                    random_state=42,
                    transform_seed=42
                )
                reduced = self.transformer.fit_transform(X)
                
            self.is_fitted = True
            logger.info(f"Successfully fitted {self.method.upper()} model on {n_samples} embeddings")
            return reduced
            
        except Exception as e:
            logger.error(f"Error during fit_transform: {str(e)}")
            # Return zeros as fallback to prevent crash
            return np.zeros((n_samples, self.n_components))

    def transform(self, embedding: List[float]) -> np.ndarray:
        """
        Transform a single embedding or list of embeddings using the fitted model.
        
        Args:
            embedding: Single embedding vector or list of vectors
            
        Returns:
            Numpy array of shape (n_samples, 3) containing 3D coordinates
        """
        if not self.is_fitted or self.transformer is None:
            logger.error("Model is not fitted. Call fit_transform first.")
            # Return zero vector
            return np.zeros((1, self.n_components))
            
        try:
            X = np.array(embedding)
            # Reshape if single sample (1D array)
            if X.ndim == 1:
                X = X.reshape(1, -1)
                
            # Handle dimension mismatch if model was fitted on fewer components
            if hasattr(self.transformer, 'n_components_'):
                # PCA stores actual components
                actual_components = self.transformer.n_components_
            elif hasattr(self.transformer, 'n_components'):
                actual_components = self.transformer.n_components
            else:
                actual_components = self.n_components
                
            reduced = self.transformer.transform(X)
            
            # Pad if needed (e.g. if we fitted on 1 sample and got 1 component)
            if reduced.shape[1] < self.n_components:
                padding = np.zeros((reduced.shape[0], self.n_components - reduced.shape[1]))
                reduced = np.hstack((reduced, padding))
                
            return reduced
            
        except Exception as e:
            logger.error(f"Error during transform: {str(e)}")
            return np.zeros((1, self.n_components))

    def save_model(self, filepath: str):
        """Save the fitted model to disk"""
        if self.transformer and self.is_fitted:
            try:
                with open(filepath, 'wb') as f:
                    pickle.dump({
                        'method': self.method,
                        'transformer': self.transformer,
                        'is_fitted': self.is_fitted
                    }, f)
                logger.info(f"Model saved to {filepath}")
            except Exception as e:
                logger.error(f"Failed to save model: {str(e)}")

    def load_model(self, filepath: str):
        """Load a fitted model from disk"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
                    self.method = data.get('method', 'pca')
                    self.transformer = data.get('transformer')
                    self.is_fitted = data.get('is_fitted', False)
                logger.info(f"Model loaded from {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to load model: {str(e)}")
        return False
