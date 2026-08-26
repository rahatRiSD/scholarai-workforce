import math

import pytest

from scholarai.infrastructure.embeddings.hashing import HashingEmbedder


@pytest.mark.asyncio
async def test_embedding_is_l2_normalized():
    embedder = HashingEmbedder(dimensions=64)
    vector = await embedder.embed("financial need scholarship policy")
    norm = math.sqrt(sum(v * v for v in vector))
    assert math.isclose(norm, 1.0, abs_tol=1e-6)


@pytest.mark.asyncio
async def test_embedding_is_deterministic_across_calls():
    embedder = HashingEmbedder(dimensions=64)
    a = await embedder.embed("minimum CGPA requirement")
    b = await embedder.embed("minimum CGPA requirement")
    assert a == b


@pytest.mark.asyncio
async def test_similar_text_scores_higher_than_unrelated_text():
    embedder = HashingEmbedder(dimensions=128)
    query = await embedder.embed("minimum CGPA requirement for scholarship")
    close = await embedder.embed("the minimum CGPA requirement for the scholarship is 3.5")
    far = await embedder.embed("weekend volunteer shifts at the community clinic")

    def cosine(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    assert cosine(query, close) > cosine(query, far)


@pytest.mark.asyncio
async def test_embed_many_matches_individual_embed_calls():
    embedder = HashingEmbedder(dimensions=32)
    texts = ["alpha", "beta"]
    batch = await embedder.embed_many(texts)
    individual = [await embedder.embed(t) for t in texts]
    assert batch == individual


def test_rejects_too_few_dimensions():
    with pytest.raises(ValueError, match="dimensions must be at least 8"):
        HashingEmbedder(dimensions=2)
