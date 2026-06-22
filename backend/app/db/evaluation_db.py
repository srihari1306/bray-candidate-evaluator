"""
Persistence layer for candidate evaluations.
Primary: Azure Cosmos DB for NoSQL.

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
        self._candidates = {}
        for eval_doc in self._evaluations.values():
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id:
                    self._candidates[cand_id] = cand

    async def save_evaluation(self, evaluation_id: str, data: dict) -> dict:
        eval_doc = copy.deepcopy(data)
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
        eval_doc = self._evaluations.get(evaluation_id)
        if eval_doc:
            return copy.deepcopy(eval_doc)
        return None

    def get_all_evaluations(self) -> list[dict]:
        return copy.deepcopy(list(self._evaluations.values()))

    async def delete_evaluation(self, evaluation_id: str) -> bool:
        if evaluation_id not in self._evaluations:
            logger.warning(f"Evaluation {evaluation_id} not found for deletion")
            return False

        def _delete():
            self._container.delete_item(item=evaluation_id, partition_key=evaluation_id)

        try:
            await asyncio.to_thread(_delete)
        except Exception as e:
            logger.error(f"Cosmos DB delete failed for evaluation {evaluation_id}: {e}")
            return False

        eval_doc = self._evaluations.pop(evaluation_id, None)
        if eval_doc:
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id in self._candidates:
                    del self._candidates[cand_id]

        logger.info(f"[Cosmos DB] Successfully deleted evaluation {evaluation_id}")
        return True

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        cand = self._candidates.get(candidate_id)
        if cand:
            return copy.deepcopy(cand)
        return None

    def get_all_candidates(self) -> list[dict]:
        return copy.deepcopy(list(self._candidates.values()))

    async def update_candidate(self, candidate_id: str, updates: dict) -> Optional[dict]:
        if candidate_id not in self._candidates:
            logger.warning(f"Candidate {candidate_id} not found for update")
            return None

        self._candidates[candidate_id].update(updates)
        updated_candidate = copy.deepcopy(self._candidates[candidate_id])

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

        parent_doc = self._evaluations[parent_eval_id]

        def _upsert():
            self._container.upsert_item(parent_doc)

        try:
            await asyncio.to_thread(_upsert)
        except Exception as e:
            logger.error(f"Cosmos DB upsert failed for evaluation {parent_eval_id} during candidate update: {e}")

        return updated_candidate


class EvaluationDB:
    """
    Unified evaluation database.
    """

    def __init__(self):
        settings = get_settings()

        endpoint = settings.AZURE_COSMOS_ENDPOINT
        if not endpoint or "your-account" in endpoint or "your-" in endpoint:
            logger.warning("Cosmos DB not configured")
        else:
            try:
                self._impl = CosmosEvaluationDBClient()
            except Exception as e:
                logger.error(f"Cosmos DB initialization failed for evaluations: {e}")

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


_db_instance: Optional[EvaluationDB] = None


def get_evaluation_db() -> EvaluationDB:
    """Get the evaluation database client singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EvaluationDB()
    return _db_instance