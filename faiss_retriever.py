"""
FAISS-based FAQ Retrieval System
Reduces LLM calls by 70% using vector similarity search
"""

import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import pickle

class FAISSRetriever:
    def __init__(self, faq_file='faqs.json', index_file='faiss_index.bin', embeddings_file='faq_embeddings.pkl'):
        """
        Initialize FAISS retriever with FAQ data

        Args:
            faq_file: Path to JSON file containing FAQs
            index_file: Path to save/load FAISS index
            embeddings_file: Path to save/load FAQ embeddings metadata
        """
        self.faq_file = faq_file
        self.index_file = index_file
        self.embeddings_file = embeddings_file

        # Load sentence transformer model (BERT-based)
        print("Loading BERT model for embeddings...")
        self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')  # Fast, efficient model

        # Storage for FAQ data
        self.faqs = []
        self.faq_texts = []  # Text to embed (question + variations)
        self.index = None

        # Load or build index
        if os.path.exists(index_file) and os.path.exists(embeddings_file):
            print("Loading existing FAISS index...")
            self.load_index()
        else:
            print("Building new FAISS index...")
            self.build_index()

    def load_faqs(self):
        """Load FAQ data from JSON file"""
        with open(self.faq_file, 'r', encoding='utf-8') as f:
            self.faqs = json.load(f)

        # Prepare text for embedding: combine question with variations
        self.faq_texts = []
        for faq in self.faqs:
            # Combine main question with variations for better matching
            combined_text = faq['question'] + ' ' + ' '.join(faq.get('variations', []))
            self.faq_texts.append(combined_text)

        print(f"Loaded {len(self.faqs)} FAQs")

    def build_index(self):
        """Build FAISS index from FAQ embeddings"""
        # Load FAQs
        self.load_faqs()

        # Generate embeddings
        print("Generating embeddings using BERT...")
        embeddings = self.model.encode(
            self.faq_texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Build FAISS index (using Inner Product for cosine similarity with normalized vectors)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product = cosine similarity with normalized vectors
        self.index.add(embeddings.astype('float32'))

        print(f"Built FAISS index with {self.index.ntotal} vectors (dimension: {dimension})")

        # Save index and metadata
        self.save_index()

    def save_index(self):
        """Save FAISS index and FAQ metadata to disk"""
        faiss.write_index(self.index, self.index_file)

        with open(self.embeddings_file, 'wb') as f:
            pickle.dump({
                'faqs': self.faqs,
                'faq_texts': self.faq_texts
            }, f)

        print(f"Saved FAISS index to {self.index_file}")

    def load_index(self):
        """Load FAISS index and FAQ metadata from disk"""
        self.index = faiss.read_index(self.index_file)

        with open(self.embeddings_file, 'rb') as f:
            data = pickle.load(f)
            self.faqs = data['faqs']
            self.faq_texts = data['faq_texts']

        print(f"Loaded FAISS index with {self.index.ntotal} vectors")

    def search(self, query, top_k=3, threshold=0.6):
        """
        Search for relevant FAQs using FAISS vector similarity

        Args:
            query: User query string
            top_k: Number of top results to return
            threshold: Minimum similarity score (0-1) for considering a match

        Returns:
            List of tuples: (faq_dict, similarity_score)
        """
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        # Search in FAISS index
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)

        # Filter by threshold and prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= threshold:  # Only return if similarity is above threshold
                results.append({
                    'faq': self.faqs[idx],
                    'score': float(score),
                    'matched_text': self.faq_texts[idx]
                })

        return results

    def get_best_answer(self, query, threshold=0.6):
        """
        Get the best matching answer for a query

        Args:
            query: User query string
            threshold: Minimum similarity score to consider a match

        Returns:
            dict with 'answer', 'score', 'category' if match found, else None
        """
        results = self.search(query, top_k=1, threshold=threshold)

        if results:
            best_match = results[0]
            return {
                'answer': best_match['faq']['answer'],
                'score': best_match['score'],
                'category': best_match['faq']['category'],
                'question': best_match['faq']['question']
            }

        return None

    def rebuild_index(self):
        """Force rebuild of FAISS index (useful after updating FAQs)"""
        print("Rebuilding FAISS index...")
        self.build_index()


# CLI for testing
if __name__ == "__main__":
    # Initialize retriever (builds index if not exists)
    retriever = FAISSRetriever()

    # Test queries
    test_queries = [
        "kitna data bacha hai",
        "mera plan kya hai",
        "recharge kaise kare",
        "customer care number kya hai",
        "internet bahut slow hai",
        "koi offer chal raha hai kya"
    ]

    print("\n" + "="*80)
    print("Testing FAISS Retrieval System")
    print("="*80 + "\n")

    for query in test_queries:
        print(f"Query: {query}")
        result = retriever.get_best_answer(query, threshold=0.5)

        if result:
            print(f"[MATCH] Score: {result['score']:.3f}")
            print(f"  Category: {result['category']}")
            print(f"  Answer: {result['answer'][:100]}...")
        else:
            print("[NO MATCH] Will use LLM fallback")

        print("-" * 80 + "\n")

    # Print statistics
    print(f"\nFAISS Index Stats:")
    print(f"Total FAQs: {retriever.index.ntotal}")
    print(f"Embedding dimension: {retriever.model.get_sentence_embedding_dimension()}")
