import numpy as np

def cosine_similarity(emb1, emb2):
    emb1, emb2 = np.array(emb1), np.array(emb2)
    dot_product = np.dot(emb1, emb2)
    norm_emb1, norm_emb2 = np.linalg.norm(emb1), np.linalg.norm(emb2)
    return dot_product / (norm_emb1 * norm_emb2)