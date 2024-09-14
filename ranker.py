from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class Ranker:
    def __init__(self):
        self.vectorizer = TfidfVectorizer() 

    def rank_documents(self, query, documents, top_k=10):
        # 1. Extract content from retrieved documents
        document_texts = [doc[1] for doc in documents] 

        # 2. Fit TF-IDF vectorizer on documents and transform query
        document_vectors = self.vectorizer.fit_transform(document_texts)
        query_vector = self.vectorizer.transform([query])

        # 3. Calculate cosine similarity
        similarity_scores = cosine_similarity(query_vector, document_vectors).flatten()

        # 4. Get indices of top-k similar documents
        top_indices = np.argsort(similarity_scores)[::-1][:top_k] 

        # 5. Create results list with document IDs and scores
        results = []
        for index in top_indices:
            doc_id = documents[index][0] 
            score = similarity_scores[index]
            results.append({"document_id": doc_id, "score": score})

        return results