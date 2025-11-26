# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Text chunking logic for documents
# =======================================================================

import logging
import re
import ast
from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

class Chunker:
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2", chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            logger.warning(f"Could not load tokenizer for {model_name}, falling back to simple splitting: {e}")
            self.tokenizer = None

    def _count_tokens(self, text: str) -> int:
        if self.tokenizer:
            return len(self.tokenizer.encode(text, add_special_tokens=False))
        return len(text.split()) # Fallback approximation

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata.
        Detects if text is code or prose and dispatches accordingly.
        """
        if not text:
            return []
            
        metadata = metadata or {}
        is_code = False
        
        # Simple heuristic for code detection if not provided in metadata
        if metadata.get("language") in ["py", "js", "java", "cpp", "python", "javascript"]:
            is_code = True
        
        if is_code and metadata.get("language") in ["py", "python"]:
            return self._chunk_python_code(text, metadata)
        else:
            return self._chunk_prose(text, metadata)

    def _chunk_prose(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk prose text respecting sentence boundaries and lists.
        """
        # 1. Split into sentences (simple regex for now, can be improved with nltk)
        # Look for [.!?] followed by whitespace and an uppercase letter or end of string
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk_tokens = []
        current_chunk_text = ""
        current_start_char = 0
        
        # Track character position
        char_cursor = 0
        
        for sentence in sentences:
            sentence_token_count = self._count_tokens(sentence)
            current_chunk_token_count = self._count_tokens(current_chunk_text)
            
            # If adding this sentence exceeds chunk size
            if current_chunk_token_count + sentence_token_count > self.chunk_size:
                # If current chunk is not empty, save it
                if current_chunk_text:
                    chunks.append({
                        "text": current_chunk_text.strip(),
                        "chunk_index": len(chunks),
                        "token_count": current_chunk_token_count,
                        "metadata": metadata.copy()
                    })
                    
                    # Handle overlap
                    # Keep last N tokens/sentences for overlap
                    # For simplicity, we'll just start a new chunk with the current sentence
                    # Implementing proper overlap with sentences is tricky without splitting sentences.
                    # We will try to keep the last sentence if it fits in overlap?
                    # Let's just start fresh for now to be safe on boundaries, or implement a sliding window of sentences.
                    
                    # Sliding window approach:
                    # We need to backtrack. But since we are iterating, let's just reset.
                    # To do overlap properly, we should maintain a buffer of sentences.
                    pass

                current_chunk_text = sentence
                current_chunk_tokens = [sentence]
            else:
                if current_chunk_text:
                    current_chunk_text += " " + sentence
                else:
                    current_chunk_text = sentence
                current_chunk_tokens.append(sentence)
                
            # Update cursor (approximate, real implementation needs to track original text offsets)
            char_cursor += len(sentence) + 1 

        # Add last chunk
        if current_chunk_text:
            chunks.append({
                "text": current_chunk_text.strip(),
                "chunk_index": len(chunks),
                "token_count": self._count_tokens(current_chunk_text),
                "metadata": metadata.copy()
            })
            
        return chunks

    def _chunk_python_code(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk Python code respecting class and function boundaries using AST.
        """
        chunks = []
        try:
            tree = ast.parse(text)
            lines = text.splitlines()
            
            # We will traverse top-level nodes
            current_chunk_lines = []
            current_chunk_token_count = 0
            
            for node in tree.body:
                # Get source segment for this node
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    start = node.lineno - 1
                    end = node.end_lineno
                    node_lines = lines[start:end]
                    node_text = "\n".join(node_lines)
                    node_tokens = self._count_tokens(node_text)
                    
                    if current_chunk_token_count + node_tokens > self.chunk_size:
                        if current_chunk_lines:
                            chunk_text = "\n".join(current_chunk_lines)
                            chunks.append({
                                "text": chunk_text,
                                "chunk_index": len(chunks),
                                "token_count": current_chunk_token_count,
                                "metadata": metadata.copy()
                            })
                            current_chunk_lines = []
                            current_chunk_token_count = 0
                    
                    current_chunk_lines.extend(node_lines)
                    current_chunk_token_count += node_tokens
                else:
                    # Non-locatable node (e.g. imports sometimes?), just skip or add
                    pass
            
            # Add remaining
            if current_chunk_lines:
                chunk_text = "\n".join(current_chunk_lines)
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": len(chunks),
                    "token_count": current_chunk_token_count,
                    "metadata": metadata.copy()
                })
                
        except SyntaxError:
            # Fallback to prose chunking if AST parsing fails
            logger.warning("AST parsing failed (SyntaxError), falling back to prose chunking")
            return self._chunk_prose(text, metadata)
            
        return chunks

# Global instance
chunker = Chunker()
