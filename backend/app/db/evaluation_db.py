"""
Persistence layer for candidate evaluations.
Primary: Azure Cosmos DB for NoSQL.
Fallback: JSON file-backed in-memory store (for local dev / missing credentials).

IMPORTANT: Several read methods (get_evaluation, get_candidate, get_all_candidates,
get_all_evaluations) are called synchronously (without await) from the routers.
Both implementations keep an in-memory cache so these reads remain synchronous.
"""

import json
import os
import asyncio
import copy
from typing import Optional, Any

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("db.evaluation_db")


# ─── JSON File Fallback Implementation ───────────────────────────────────────

class JSONFileEvaluationDB:
    """JSON file persistence client for evaluation results with in-memory caching (fallback)."""

    def __init__(self):
        settings = get_settings()
        self.file_path = getattr(settings, "EVALUATIONS_JSON_PATH", "data/evaluations.json")

        if not os.path.isabs(self.file_path):
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.file_path = os.path.join(backend_dir, self.file_path)

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        self.lock = asyncio.Lock()
        self._evaluations = {}
        self._candidates = {}
        self._load_from_disk()
        logger.info(f"Initialized JSON evaluation database at {self.file_path} with {len(self._evaluations)} evaluations and {len(self._candidates)} candidates")

    def _load_from_disk(self):
        """Loads evaluations from the JSON file into memory."""
        if not os.path.exists(self.file_path):
            self._evaluations = {}
            self._candidates = {}
            self._save_to_disk_sync()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._evaluations = data
                    self._candidates = {}
                    for eval_id, eval_doc in self._evaluations.items():
                        for cand in eval_doc.get("candidates", []):
                            cand_id = cand.get("id")
                            if cand_id:
                                self._candidates[cand_id] = cand
                else:
                    self._evaluations = {}
                    self._candidates = {}
                    logger.warning("Invalid data format in evaluations JSON database; initialized empty.")
        except Exception as e:
            logger.error(f"Error loading evaluations JSON database: {e}. Starting with empty cache.")
            self._evaluations = {}
            self._candidates = {}

    def _save_to_disk_sync(self):
        """Helper to write the current evaluation state to disk synchronously."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._evaluations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write evaluations to JSON file: {e}")

    async def _save_to_disk(self):
        """Flush memory state to disk asynchronously (with lock held)."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_to_disk_sync)

    async def save_evaluation(self, evaluation_id: str, data: dict) -> dict:
        """Create or update a full candidate evaluation result."""
        async with self.lock:
            logger.info(f"[JSON DB] Saving evaluation {evaluation_id} with {len(data.get('candidates', []))} candidates")

            eval_doc = copy.deepcopy(data)
            self._evaluations[evaluation_id] = eval_doc

            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id:
                    self._candidates[cand_id] = cand

            await self._save_to_disk()
            return eval_doc

    def get_evaluation(self, evaluation_id: str) -> Optional[dict]:
        """Get evaluation by ID (synchronous read, returns a deep copy)."""
        eval_doc = self._evaluations.get(evaluation_id)
        if eval_doc:
            return copy.deepcopy(eval_doc)
        return None

    def get_all_evaluations(self) -> list[dict]:
        """Get all evaluations from cache (returns deep copies)."""
        return copy.deepcopy(list(self._evaluations.values()))

    async def delete_evaluation(self, evaluation_id: str) -> bool:
        """Delete an evaluation and all its associated candidates from cache and disk."""
        async with self.lock:
            if evaluation_id not in self._evaluations:
                logger.warning(f"Evaluation {evaluation_id} not found for deletion")
                return False

            eval_doc = self._evaluations[evaluation_id]
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id in self._candidates:
                    del self._candidates[cand_id]

            del self._evaluations[evaluation_id]
            await self._save_to_disk()
            logger.info(f"[JSON DB] Successfully deleted evaluation {evaluation_id}")
            return True

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        """Get candidate by ID (returns a deep copy)."""
        cand = self._candidates.get(candidate_id)
        if cand:
            return copy.deepcopy(cand)
        return None

    def get_all_candidates(self) -> list[dict]:
        """Get all candidates from cache (returns deep copies)."""
        return copy.deepcopy(list(self._candidates.values()))

    async def update_candidate(self, candidate_id: str, updates: dict) -> Optional[dict]:
        """Update candidate fields (like shortlisted status or notes)."""
        async with self.lock:
            if candidate_id not in self._candidates:
                logger.warning(f"Candidate {candidate_id} not found for update")
                return None

            self._candidates[candidate_id].update(updates)
            updated_candidate = self._candidates[candidate_id]

            found_parent = False
            for eval_id, eval_doc in self._evaluations.items():
                candidates_list = eval_doc.get("candidates", [])
                for idx, cand in enumerate(candidates_list):
                    if cand.get("id") == candidate_id:
                        candidates_list[idx].update(updates)
                        found_parent = True
                        break
                if found_parent:
                    break

            if not found_parent:
                logger.warning(f"Parent evaluation for candidate {candidate_id} not found in _evaluations")

            await self._save_to_disk()
            return copy.deepcopy(updated_candidate)


# ─── Cosmos DB Implementation ────────────────────────────────────────────────

class CosmosEvaluationDBClient:
    """
    Azure Cosmos DB for NoSQL persistence client for evaluations.

    Maintains an in-memory cache so that synchronous read methods
    (get_evaluation, get_candidate, get_all_evaluations, get_all_candidates)
    work without await — matching the existing calling convention in routers.
    """

    def __init__(self):
        from azure.cosmos import CosmosClient

        settings = get_settings()
        self._client = CosmosClient(
            url=settings.AZURE_COSMOS_ENDPOINT,
            credential=settings.AZURE_COSMOS_KEY,
        )
        self._database = self._client.get_database_client(settings.AZURE_COSMOS_DATABASE)
        self._container = self._database.get_container_client(settings.AZURE_COSMOS_EVALUATIONS_CONTAINER)

        # In-memory caches for synchronous reads
        self._evaluations: dict[str, dict] = {}
        self._candidates: dict[str, dict] = {}

        # Load existing data from Cosmos into the cache
        self._load_cache_from_cosmos()
        logger.info(f"✓ Cosmos DB evaluation store initialized with {len(self._evaluations)} evaluations and {len(self._candidates)} candidates")

    def _load_cache_from_cosmos(self):
        """Synchronously load all evaluations from Cosmos into the in-memory cache."""
        try:
            items = list(self._container.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            ))
            self._evaluations = {}
            self._candidates = {}
            for item in items:
                eval_id = item.get("id")
                if eval_id:
                    self._evaluations[eval_id] = item
                    for cand in item.get("candidates", []):
                        cand_id = cand.get("id")
                        if cand_id:
                            self._candidates[cand_id] = cand
        except Exception as e:
            logger.error(f"Failed to load evaluations from Cosmos DB: {e}")
            self._evaluations = {}
            self._candidates = {}

    def _rebuild_candidate_cache(self):
        """Rebuild the candidates cache from the evaluations cache."""
        self._candidates = {}
        for eval_doc in self._evaluations.values():
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id:
                    self._candidates[cand_id] = cand

    async def save_evaluation(self, evaluation_id: str, data: dict) -> dict:
        """Create or update a full candidate evaluation result."""
        eval_doc = copy.deepcopy(data)
        # Ensure 'id' field is set for Cosmos
        eval_doc["id"] = evaluation_id

        def _upsert():
            self._container.upsert_item(eval_doc)

        logger.info(f"[Cosmos DB] Saving evaluation {evaluation_id} with {len(data.get('candidates', []))} candidates")
        await asyncio.to_thread(_upsert)

        # Update in-memory cache
        self._evaluations[evaluation_id] = eval_doc
        for cand in eval_doc.get("candidates", []):
            cand_id = cand.get("id")
            if cand_id:
                self._candidates[cand_id] = cand

        return eval_doc

    def get_evaluation(self, evaluation_id: str) -> Optional[dict]:
        """Get evaluation by ID (synchronous read from cache, returns a deep copy)."""
        eval_doc = self._evaluations.get(evaluation_id)
        if eval_doc:
            return copy.deepcopy(eval_doc)
        return None

    def get_all_evaluations(self) -> list[dict]:
        """Get all evaluations from cache (returns deep copies)."""
        return copy.deepcopy(list(self._evaluations.values()))

    async def delete_evaluation(self, evaluation_id: str) -> bool:
        """Delete an evaluation from Cosmos and the in-memory cache."""
        if evaluation_id not in self._evaluations:
            logger.warning(f"Evaluation {evaluation_id} not found for deletion")
            return False

        def _delete():
            # Partition key is /id, so both item and partition_key are evaluation_id
            self._container.delete_item(item=evaluation_id, partition_key=evaluation_id)

        try:
            await asyncio.to_thread(_delete)
        except Exception as e:
            logger.error(f"Cosmos DB delete failed for evaluation {evaluation_id}: {e}")
            return False

        # Remove from cache
        eval_doc = self._evaluations.pop(evaluation_id, None)
        if eval_doc:
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id in self._candidates:
                    del self._candidates[cand_id]

        logger.info(f"[Cosmos DB] Successfully deleted evaluation {evaluation_id}")
        return True

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        """Get candidate by ID (synchronous read from cache)."""
        cand = self._candidates.get(candidate_id)
        if cand:
            return copy.deepcopy(cand)
        return None

    def get_all_candidates(self) -> list[dict]:
        """Get all candidates from cache (returns deep copies)."""
        return copy.deepcopy(list(self._candidates.values()))

    async def update_candidate(self, candidate_id: str, updates: dict) -> Optional[dict]:
        """Update candidate fields, then upsert the parent evaluation to Cosmos."""
        if candidate_id not in self._candidates:
            logger.warning(f"Candidate {candidate_id} not found for update")
            return None

        # Update in-memory candidate cache
        self._candidates[candidate_id].update(updates)
        updated_candidate = copy.deepcopy(self._candidates[candidate_id])

        # Find parent evaluation and update the nested candidate
        parent_eval_id = None
        for eval_id, eval_doc in self._evaluations.items():
            candidates_list = eval_doc.get("candidates", [])
            for idx, cand in enumerate(candidates_list):
                if cand.get("id") == candidate_id:
                    candidates_list[idx].update(updates)
                    parent_eval_id = eval_id
                    break
            if parent_eval_id:
                break

        if not parent_eval_id:
            logger.warning(f"Parent evaluation for candidate {candidate_id} not found in cache")
            return updated_candidate

        # Persist the updated parent evaluation to Cosmos
        parent_doc = self._evaluations[parent_eval_id]

        def _upsert():
            self._container.upsert_item(parent_doc)

        try:
            await asyncio.to_thread(_upsert)
        except Exception as e:
            logger.error(f"Cosmos DB upsert failed for evaluation {parent_eval_id} during candidate update: {e}")

        return updated_candidate


# ─── Unified EvaluationDB — picks implementation based on config ─────────────

class EvaluationDB:
    """
    Unified evaluation database.
    Uses Cosmos DB when credentials are configured, otherwise falls back to JSON file.
    """

    def __init__(self):
        settings = get_settings()

        endpoint = settings.AZURE_COSMOS_ENDPOINT
        if not endpoint or "your-account" in endpoint or "your-" in endpoint:
            logger.warning("Cosmos DB not configured — falling back to JSON file persistence for evaluations")
            self._impl = JSONFileEvaluationDB()
        else:
            try:
                self._impl = CosmosEvaluationDBClient()
            except Exception as e:
                logger.error(f"Cosmos DB initialization failed for evaluations: {e} — falling back to JSON file persistence")
                self._impl = JSONFileEvaluationDB()

    async def save_evaluation(self, evaluation_id: str, data: dict) -> dict:
        return await self._impl.save_evaluation(evaluation_id, data)

    def get_evaluation(self, evaluation_id: str) -> Optional[dict]:
        return self._impl.get_evaluation(evaluation_id)

    def get_all_evaluations(self) -> list[dict]:
        return self._impl.get_all_evaluations()

    async def delete_evaluation(self, evaluation_id: str) -> bool:
        return await self._impl.delete_evaluation(evaluation_id)

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        return self._impl.get_candidate(candidate_id)

    def get_all_candidates(self) -> list[dict]:
        return self._impl.get_all_candidates()

    async def update_candidate(self, candidate_id: str, updates: dict) -> Optional[dict]:
        return await self._impl.update_candidate(candidate_id, updates)


# ─── Factory ────────────────────────────────────────────────────────────────

_db_instance: Optional[EvaluationDB] = None


def get_evaluation_db() -> EvaluationDB:
    """Get the evaluation database client singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EvaluationDB()
    return _db_instance