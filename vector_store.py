from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

_chunks = []
_vectors = None
_vectorizer = TfidfVectorizer()

def add_chunks(chunks):
    global _chunks, _vectors
    _chunks.extend(chunks)
    _vectors = _vectorizer.fit_transform(_chunks)

def search(query, top_k=5):
    if _vectors is None:
        return []

    query_vec = _vectorizer.transform([query])
    scores = cosine_similarity(query_vec, _vectors)[0]

    top_indices = scores.argsort()[-top_k:][::-1]
    return [_chunks[i] for i in top_indices]
