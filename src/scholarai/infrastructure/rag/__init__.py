"""RAG pipeline: chunking, ingestion, and retrieval over the policy knowledge base.

``Documents -> Text extraction -> Chunking -> Embeddings -> Vector database ->
Retriever -> Policy Agent`` (build spec §10).
"""
