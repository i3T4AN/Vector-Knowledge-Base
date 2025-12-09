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
    # Model's max sequence length - chunks must not exceed this
    MAX_MODEL_TOKENS = 500  # Leave some buffer below the 512 hard limit
    
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

    def _split_oversized_text(self, text: str, max_tokens: int = None) -> List[str]:
        """
        Split text that exceeds max token limit into smaller pieces.
        Uses word boundaries to avoid breaking mid-word.
        """
        max_tokens = max_tokens or self.MAX_MODEL_TOKENS
        
        if self._count_tokens(text) <= max_tokens:
            return [text]
        
        # Split by words and rebuild chunks
        words = text.split()
        pieces = []
        current_piece = []
        current_tokens = 0
        
        for word in words:
            word_tokens = self._count_tokens(word)
            if current_tokens + word_tokens > max_tokens and current_piece:
                pieces.append(' '.join(current_piece))
                current_piece = []
                current_tokens = 0
            current_piece.append(word)
            current_tokens += word_tokens
        
        if current_piece:
            pieces.append(' '.join(current_piece))
        
        return pieces

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
        
        # 2. Split any oversized sentences that exceed model limits
        processed_sentences = []
        for sentence in sentences:
            if self._count_tokens(sentence) > self.MAX_MODEL_TOKENS:
                # Split this oversized sentence into smaller pieces
                pieces = self._split_oversized_text(sentence, self.MAX_MODEL_TOKENS)
                processed_sentences.extend(pieces)
            else:
                processed_sentences.append(sentence)
        sentences = processed_sentences
        
        # OPTIMIZATION: Pre-compute token counts for all sentences (cache to avoid redundant tokenization)
        sentence_token_counts = [self._count_tokens(s) for s in sentences]
        
        chunks = []
        i = 0
        
        while i < len(sentences):
            current_chunk = []
            current_chunk_tokens = []  # Store token counts for this chunk
            current_tokens = 0
            
            # Build a chunk
            while i < len(sentences):
                sentence = sentences[i]
                tokens = sentence_token_counts[i]  # Use cached token count
                
                if current_tokens + tokens > self.chunk_size and current_chunk:
                    break
                
                current_chunk.append(sentence)
                current_chunk_tokens.append(tokens)  # Cache for overlap calculation
                current_tokens += tokens
                i += 1
            
            # Save chunk
            chunks.append({
                'text': ' '.join(current_chunk),
                'chunk_index': len(chunks),
                'token_count': current_tokens,
                'metadata': metadata.copy()
            })
            
            # OVERLAP: Backtrack to include last N tokens in next chunk
            if i < len(sentences):
                overlap_tokens = 0
                overlap_sentences = 0
                
                for j in range(len(current_chunk) - 1, -1, -1):
                    overlap_tokens += current_chunk_tokens[j]  # Use cached token count (no re-tokenization!)
                    
                    # Prevent infinite loop: ensure at least one sentence advances
                    if overlap_sentences + 1 >= len(current_chunk):
                        break
                        
                    overlap_sentences += 1
                    if overlap_tokens >= self.chunk_overlap:
                        break
                
                # Rewind i to repeat these sentences in next chunk
                i -= overlap_sentences
        
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
                    # Skip nodes without line info (rare edge case)
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
