import numpy as np

# 1. Prepare toy text vectors (stand-ins for embeddings)
# In production a model would turn sentences into numbers like these.
vector_a = np.array([0.1, 0.5, -0.2])
vector_b = np.array([0.12, 0.48, -0.21])  # similar meaning
vector_c = np.array([-0.5, 0.1, 0.9])  # different meaning


def cosine_similarity(v1, v2):
    """
    Cosine similarity: (v1 · v2) / (||v1||_2 * ||v2||_2)
    Uses np.dot and np.linalg.norm.
    """
    # Cosine similarity formula: (v1 · v2) / (||v1|| * ||v2||)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    # Guard against zero-norm vectors (undefined cosine)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return dot_product / (norm_v1 * norm_v2)


# 2. Print similarity checks
print(f"Similarity A vs B: {cosine_similarity(vector_a, vector_b)}")
print(f"Similarity A vs C: {cosine_similarity(vector_a, vector_c)}")
