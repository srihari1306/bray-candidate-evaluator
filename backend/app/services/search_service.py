"""
Azure AI Search service for hybrid vector + keyword search.
Implements HNSW vector search, BM25, and semantic reranking.
"""

import uuid
from typing import Optional

from app.config import get_settings
from app.services.chunking_service import TextChunk
from app.utils.logger import get_logger
from app.utils.retry import retry_async

logger = get_logger("search")


class SearchDocument:
    """Document to be indexed in Azure AI Search."""

    def __init__(
        self,
        doc_id: str,
        candidate_name: str,
        resume_text: str,
        skills: list[str],
        projects: str,
        experience: str,
        resume_link: str,
        content_vector: list[float],
        chunk_index: int = 0,
        total_chunks: int = 1,
        metadata: dict = None,
        skill_tags: list[str] = None,
    ):
        self.doc_id = doc_id
        self.candidate_name = candidate_name
        self.resume_text = resume_text
        self.skills = skills
        self.projects = projects
        self.experience = experience
        self.resume_link = resume_link
        self.content_vector = content_vector
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.metadata = metadata or {}
        self.skill_tags = skill_tags or []

    def to_dict(self) -> dict:
        return {
            "id": self.doc_id,
            "candidate_name": self.candidate_name,
            "resume_text": self.resume_text,
            "skills": ",".join(self.skills),
            "projects": self.projects,
            "experience": self.experience,
            "resume_link": self.resume_link,
            "content_vector": self.content_vector,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "metadata": str(self.metadata),
            "skill_tags": ",".join(self.skill_tags),
        }


class SearchService:
    """Azure AI Search service with hybrid search capabilities."""

    def __init__(self):
        self.settings = get_settings()
        self._search_client = None
        self._index_client = None

    def _get_index_client(self):
        if self._index_client is None:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents.indexes import SearchIndexClient

            self._index_client = SearchIndexClient(
                endpoint=self.settings.AZURE_SEARCH_ENDPOINT,
                credential=AzureKeyCredential(self.settings.AZURE_SEARCH_API_KEY),
            )
        return self._index_client

    def _get_search_client(self):
        if self._search_client is None:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            self._search_client = SearchClient(
                endpoint=self.settings.AZURE_SEARCH_ENDPOINT,
                index_name=self.settings.AZURE_SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(self.settings.AZURE_SEARCH_API_KEY),
            )
        return self._search_client

    async def create_or_update_index(self):
        """Create or update the search index with vector and semantic configuration."""
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SearchField,
            SearchFieldDataType,
            SearchableField,
            SimpleField,
            VectorSearch,
            HnswAlgorithmConfiguration,
            VectorSearchProfile,
            SemanticConfiguration,
            SemanticPrioritizedFields,
            SemanticField,
            SemanticSearch,
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="candidate_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="resume_text", type=SearchFieldDataType.String),
            SearchableField(name="skills", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="projects", type=SearchFieldDataType.String),
            SearchableField(name="experience", type=SearchFieldDataType.String),
            SimpleField(name="resume_link", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.settings.EMBEDDING_DIMENSIONS,
                vector_search_profile_name="resume-vector-profile",
            ),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
            SimpleField(name="total_chunks", type=SearchFieldDataType.Int32),
            SimpleField(name="metadata", type=SearchFieldDataType.String),
            SearchableField(name="skill_tags", type=SearchFieldDataType.String, filterable=True),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="resume-hnsw-config")],
            profiles=[VectorSearchProfile(name="resume-vector-profile", algorithm_configuration_name="resume-hnsw-config")],
        )

        semantic_config = SemanticConfiguration(
            name="resume-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="resume_text")],
                title_field=SemanticField(field_name="candidate_name"),
                keywords_fields=[SemanticField(field_name="skills")],
            ),
        )

        index = SearchIndex(
            name=self.settings.AZURE_SEARCH_INDEX_NAME,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )

        client = self._get_index_client()
        client.create_or_update_index(index)
        logger.info(f"Search index '{self.settings.AZURE_SEARCH_INDEX_NAME}' created/updated")

    async def index_documents(self, documents: list[SearchDocument]):
        """Upload documents to the search index."""
        client = self._get_search_client()
        batch = [doc.to_dict() for doc in documents]

        # Upload in batches of 1000
        batch_size = 1000
        for i in range(0, len(batch), batch_size):
            chunk = batch[i : i + batch_size]
            result = client.upload_documents(documents=chunk)
            succeeded = sum(1 for r in result if r.succeeded)
            logger.info(f"Indexed {succeeded}/{len(chunk)} documents (batch {i // batch_size + 1})")

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        top: int = 10,
        filter_expr: Optional[str] = None,
    ) -> list[dict]:
        """
        Execute hybrid search combining BM25 keyword search,
        HNSW vector search, and semantic reranking.
        """
        from azure.search.documents.models import VectorizedQuery

        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=50,
            fields="content_vector",
        )

        client = self._get_search_client()
        results = client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            query_type="semantic",
            semantic_configuration_name="resume-semantic-config",
            top=top,
            filter=filter_expr,
            select=["id", "candidate_name", "resume_text", "skills", "projects", "experience", "resume_link", "skill_tags"],
        )

        search_results = []
        for result in results:
            search_results.append({
                "id": result["id"],
                "candidate_name": result["candidate_name"],
                "resume_text": result["resume_text"],
                "skills": result.get("skills", ""),
                "projects": result.get("projects", ""),
                "experience": result.get("experience", ""),
                "resume_link": result.get("resume_link", ""),
                "skill_tags": result.get("skill_tags", ""),
                "score": result.get("@search.score", 0),
                "reranker_score": result.get("@search.reranker_score", 0),
            })

        logger.info(f"Hybrid search returned {len(search_results)} results")
        return search_results

    async def delete_all_documents(self):
        """Delete all documents from the index (for reindexing)."""
        client = self._get_search_client()
        # Search for all document IDs
        results = client.search(search_text="*", select=["id"], top=1000)
        doc_ids = [{"id": r["id"]} for r in results]
        if doc_ids:
            client.delete_documents(documents=doc_ids)
            logger.info(f"Deleted {len(doc_ids)} documents from index")


# ─── Mock Implementation ────────────────────────────────────────────────────

class MockSearchService(SearchService):
    """In-memory search service for local development."""

    def __init__(self):
        super().__init__()
        self._documents: list[SearchDocument] = []

    async def create_or_update_index(self):
        logger.info("[MOCK] Index created (in-memory)")

    async def index_documents(self, documents: list[SearchDocument]):
        self._documents.extend(documents)
        logger.info(f"[MOCK] Indexed {len(documents)} documents (total: {len(self._documents)})")

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        top: int = 10,
        filter_expr: Optional[str] = None,
    ) -> list[dict]:
        """Simple cosine similarity search on in-memory documents."""
        if not self._documents:
            return []

        # Compute cosine similarity
        import numpy as np

        query_vec = np.array(query_vector)
        scored = []

        for doc in self._documents:
            doc_vec = np.array(doc.content_vector)
            cos_sim = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-8)

            # Also add keyword overlap score
            query_words = set(query_text.lower().split())
            doc_words = set(doc.resume_text.lower().split())
            keyword_overlap = len(query_words & doc_words) / max(len(query_words), 1)

            combined_score = 0.7 * cos_sim + 0.3 * keyword_overlap

            scored.append((doc, combined_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate by candidate name (return highest scoring chunk per candidate)
        seen_candidates = set()
        results = []
        for doc, score in scored:
            if doc.candidate_name in seen_candidates:
                continue
            seen_candidates.add(doc.candidate_name)
            results.append({
                "id": doc.doc_id,
                "candidate_name": doc.candidate_name,
                "resume_text": doc.resume_text,
                "skills": ",".join(doc.skills),
                "projects": doc.projects,
                "experience": doc.experience,
                "resume_link": doc.resume_link,
                "skill_tags": ",".join(doc.skill_tags),
                "score": float(score),
                "reranker_score": float(score),
            })
            if len(results) >= top:
                break

        logger.info(f"[MOCK] Search returned {len(results)} results")
        return results

    async def delete_all_documents(self):
        self._documents.clear()
        logger.info("[MOCK] All documents deleted")


def get_search_service() -> SearchService:
    """Factory for search service."""
    settings = get_settings()
    if settings.MOCK_MODE:
        return MockSearchService()
    return SearchService()
