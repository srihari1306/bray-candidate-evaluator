"""
JSON file-backed persistence layer for interview sessions.
Maintains in-memory dictionary and flushes to data/interviews.json.
Provides thread-safe and async-safe CRUD interfaces.
"""

import json
import os
import asyncio
from typing import Optional
from datetime import datetime

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("db.session_db")


class InterviewDB:
    """Abstract interface for interview session storage."""

    async def create_session(self, session_doc: dict) -> dict:
        raise NotImplementedError

    async def get_session(self, session_id: str) -> Optional[dict]:
        raise NotImplementedError

    async def update_session(self, session_id: str, candidate_id: str, updates: dict) -> dict:
        raise NotImplementedError

    async def get_candidate_sessions(self, candidate_id: str, evaluation_id: Optional[str] = None) -> Optional[dict]:
        raise NotImplementedError


class JSONFileDBClient(InterviewDB):
    """JSON file persistence client with in-memory caching."""

    def __init__(self):
        settings = get_settings()
        self.file_path = settings.INTERVIEWS_JSON_PATH
        
        # Resolve path relative to backend directory if not absolute
        if not os.path.isabs(self.file_path):
            # Resolve relative to project root or backend root
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.file_path = os.path.join(backend_dir, self.file_path)
            
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Async lock for serialization safety
        self.lock = asyncio.Lock()
        
        # In-memory session cache: {session_id: session_doc}
        self._sessions = {}
        self._load_from_disk()
        logger.info(f"Initialized JSON file database at {self.file_path} with {len(self._sessions)} sessions")

    def _load_from_disk(self):
        """Loads sessions from the JSON file into memory."""
        if not os.path.exists(self.file_path):
            self._sessions = {}
            self._save_to_disk_sync()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._sessions = data
                else:
                    self._sessions = {}
                    logger.warning("Invalid data format in JSON database; initialized empty.")
        except Exception as e:
            logger.error(f"Error loading JSON database: {e}. Starting with empty cache.")
            self._sessions = {}

    def _save_to_disk_sync(self):
        """Helper to write the current session state to disk synchronously."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write sessions to JSON file: {e}")

    async def _save_to_disk(self):
        """Flush memory state to disk asynchronously (with lock held)."""
        # Run synchronous write in a separate executor thread so it doesn't block the event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_to_disk_sync)

    async def create_session(self, session_doc: dict) -> dict:
        """Create a new interview session."""
        async with self.lock:
            session_id = session_doc["id"]
            logger.info(f"[JSON DB] Creating session {session_id} for candidate {session_doc['candidate_name']}")
            self._sessions[session_id] = session_doc
            await self._save_to_disk()
            return session_doc

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID."""
        async with self.lock:
            session = self._sessions.get(session_id)
            if session:
                return dict(session)  # Return a copy to avoid mutation side-effects
            return None

    async def update_session(self, session_id: str, candidate_id: str, updates: dict) -> dict:
        """Update an existing session."""
        async with self.lock:
            if session_id not in self._sessions:
                raise ValueError(f"Session {session_id} not found")
            
            logger.info(f"[JSON DB] Updating session {session_id}: keys={list(updates.keys())}")
            self._sessions[session_id].update(updates)
            await self._save_to_disk()
            return dict(self._sessions[session_id])

    async def get_candidate_sessions(self, candidate_id: str, evaluation_id: Optional[str] = None) -> Optional[dict]:
        """Get the latest session for a candidate, optionally filtered by evaluation_id."""
        async with self.lock:
            candidate_sessions = []
            for doc in self._sessions.values():
                if doc.get("candidate_id") == candidate_id:
                    session_eval_id = doc.get("evaluation_id")
                    if evaluation_id is not None:
                        if session_eval_id and session_eval_id == evaluation_id:
                            candidate_sessions.append(doc)
                    else:
                        candidate_sessions.append(doc)
            
            if not candidate_sessions:
                return None
                
            # Sort by created_at DESC
            candidate_sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
            return dict(candidate_sessions[0])


# ─── Factory ────────────────────────────────────────────────────────────────

_db_instance: Optional[InterviewDB] = None


def get_interview_db() -> InterviewDB:
    """Get the JSON file database client singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = JSONFileDBClient()
    return _db_instance
