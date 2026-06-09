"""
JSON file-backed persistence layer for candidate evaluations.
Maintains in-memory dictionary of evaluations and flushes to data/evaluations.json.
Provides thread-safe and async-safe CRUD interfaces.
"""

import json
import os
import asyncio
from typing import Optional, Any
import copy

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("db.evaluation_db")


class EvaluationDB:
    """JSON file persistence client for evaluation results with in-memory caching."""

    def __init__(self):
        settings = get_settings()
        # Use data/evaluations.json as the default storage path
        self.file_path = getattr(settings, "EVALUATIONS_JSON_PATH", "data/evaluations.json")
        
        # Resolve path relative to backend directory if not absolute
        if not os.path.isabs(self.file_path):
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.file_path = os.path.join(backend_dir, self.file_path)
            
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Async lock for serialization safety
        self.lock = asyncio.Lock()
        
        # In-memory evaluation cache: {evaluation_id: evaluation_doc}
        self._evaluations = {}
        # In-memory candidate cache: {candidate_id: candidate_doc}
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
                    # Rebuild the candidates cache from the nested evaluations
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
            logger.info(f"[Evaluation DB] Saving evaluation {evaluation_id} with {len(data.get('candidates', []))} candidates")
            
            # Save copy of the evaluation
            eval_doc = copy.deepcopy(data)
            self._evaluations[evaluation_id] = eval_doc
            
            # Re-index candidates from this evaluation in our candidate map
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id:
                    self._candidates[cand_id] = cand
                    
            await self._save_to_disk()
            return eval_doc

    def get_evaluation(self, evaluation_id: str) -> Optional[dict]:
        """Get evaluation by ID (synchronous read, returns a deep copy)."""
        # Read from cache is thread-safe as dictionary reads are atomic, returning copy
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
            
            # Retrieve evaluation to find its candidates
            eval_doc = self._evaluations[evaluation_id]
            for cand in eval_doc.get("candidates", []):
                cand_id = cand.get("id")
                if cand_id in self._candidates:
                    del self._candidates[cand_id]
                    
            del self._evaluations[evaluation_id]
            await self._save_to_disk()
            logger.info(f"[Evaluation DB] Successfully deleted evaluation {evaluation_id}")
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
        """
        Update candidate fields (like shortlisted status or notes).
        Ensures both _candidates in-memory cache and the nested candidate inside _evaluations
        are updated, then flushes to disk once.
        """
        async with self.lock:
            if candidate_id not in self._candidates:
                logger.warning(f"Candidate {candidate_id} not found for update")
                return None
            
            # Update cache copy
            self._candidates[candidate_id].update(updates)
            updated_candidate = self._candidates[candidate_id]
            
            # Find the parent evaluation that contains this candidate
            # and update the candidate object inside it.
            found_parent = False
            for eval_id, eval_doc in self._evaluations.items():
                candidates_list = eval_doc.get("candidates", [])
                for idx, cand in enumerate(candidates_list):
                    if cand.get("id") == candidate_id:
                        # Update the candidate inside the list
                        candidates_list[idx].update(updates)
                        found_parent = True
                        break
                if found_parent:
                    break
            
            if not found_parent:
                logger.warning(f"Parent evaluation for candidate {candidate_id} not found in _evaluations")
                
            await self._save_to_disk()
            return copy.deepcopy(updated_candidate)


# ─── Factory ────────────────────────────────────────────────────────────────

_db_instance: Optional[EvaluationDB] = None


def get_evaluation_db() -> EvaluationDB:
    """Get the JSON evaluation database client singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = EvaluationDB()
    return _db_instance
