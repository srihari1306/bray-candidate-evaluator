"""
Persistence layer for interview sessions.
Primary: Azure Cosmos DB for NoSQL.
Fallback: JSON file-backed in-memory store (for local dev / missing credentials).
"""

import json
import os
import asyncio
import copy
from typing import Optional
from datetime import datetime

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("db.session_db")


# ─── JSON File Fallback Implementation ───────────────────────────────────────

class JSONFileDBClient:
    """JSON file persistence client with in-memory caching (fallback)."""

    def __init__(self):
        settings = get_settings()
        self.file_path = settings.INTERVIEWS_JSON_PATH

        # Resolve path relative to backend directory if not absolute
        if not os.path.isabs(self.file_path):
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
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_to_disk_sync)

    async def create_session(self, session_doc: dict) -> dict:
        """Create a new interview session."""
        async with self.lock:
            session_id = session_doc["id"]
            logger.info(f"[JSON DB] Creating session {session_id} for candidate {session_doc.get('candidate_name', 'unknown')}")
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

    async def list_all_sessions(self) -> list[dict]:
        """Get all sessions."""
        async with self.lock:
            return [dict(s) for s in self._sessions.values()]

    async def delete_session(self, session_id: str, candidate_id: str) -> None:
        """Delete a session."""
        async with self.lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                await self._save_to_disk()
                logger.info(f"[JSON DB] Deleted session {session_id}")


# ─── Cosmos DB Implementation ────────────────────────────────────────────────

class CosmosSessionDBClient:
    """Azure Cosmos DB for NoSQL persistence client for interview sessions."""

    def __init__(self):
        from azure.cosmos import CosmosClient

        settings = get_settings()
        self._client = CosmosClient(
            url=settings.AZURE_COSMOS_ENDPOINT,
            credential=settings.AZURE_COSMOS_KEY,
        )
        self._database = self._client.get_database_client(settings.AZURE_COSMOS_DATABASE)
        self._container = self._database.get_container_client(settings.AZURE_COSMOS_SESSIONS_CONTAINER)
        logger.info("✓ Cosmos DB session store initialized")

    async def create_session(self, session_doc: dict) -> dict:
        """Create or upsert a session document."""
        def _upsert():
            self._container.upsert_item(session_doc)

        logger.info(f"[Cosmos DB] Creating session {session_doc['id']} for candidate {session_doc.get('candidate_name', 'unknown')}")
        await asyncio.to_thread(_upsert)
        return session_doc

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID (cross-partition query since we may not know candidate_id)."""
        def _query():
            items = list(self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": session_id}],
                enable_cross_partition_query=True,
            ))
            return items[0] if items else None

        return await asyncio.to_thread(_query)

    async def update_session(self, session_id: str, candidate_id: str, updates: dict) -> dict:
        """Read → merge → upsert pattern."""
        def _read_merge_upsert():
            # Read
            items = list(self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": session_id}],
                enable_cross_partition_query=True,
            ))
            if not items:
                raise ValueError(f"Session {session_id} not found")

            item = items[0]
            item.update(updates)
            self._container.upsert_item(item)
            return item

        logger.info(f"[Cosmos DB] Updating session {session_id}: keys={list(updates.keys())}")
        return await asyncio.to_thread(_read_merge_upsert)

    async def get_candidate_sessions(self, candidate_id: str, evaluation_id: Optional[str] = None) -> Optional[dict]:
        """Get the latest session for a candidate, optionally filtered by evaluation_id."""
        def _query():
            if evaluation_id:
                query = (
                    "SELECT * FROM c WHERE c.candidate_id = @cid AND c.evaluation_id = @eid "
                    "ORDER BY c.created_at DESC OFFSET 0 LIMIT 1"
                )
                params = [
                    {"name": "@cid", "value": candidate_id},
                    {"name": "@eid", "value": evaluation_id},
                ]
            else:
                query = (
                    "SELECT * FROM c WHERE c.candidate_id = @cid "
                    "ORDER BY c.created_at DESC OFFSET 0 LIMIT 1"
                )
                params = [{"name": "@cid", "value": candidate_id}]

            items = list(self._container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ))
            return items[0] if items else None

        return await asyncio.to_thread(_query)

    async def list_all_sessions(self) -> list[dict]:
        """Get all sessions."""
        def _query():
            return list(self._container.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            ))

        return await asyncio.to_thread(_query)

    async def delete_session(self, session_id: str, candidate_id: str) -> None:
        """Delete a session document."""
        def _delete():
            self._container.delete_item(item=session_id, partition_key=candidate_id)

        logger.info(f"[Cosmos DB] Deleting session {session_id}")
        await asyncio.to_thread(_delete)


# ─── Unified InterviewDB — picks implementation based on config ──────────────

class InterviewDB:
    """
    Unified interview session database.
    Uses Cosmos DB when credentials are configured, otherwise falls back to JSON file.
    """

    def __init__(self):
        settings = get_settings()

        # Determine backend
        endpoint = settings.AZURE_COSMOS_ENDPOINT
        if not endpoint or "your-account" in endpoint or "your-" in endpoint:
            logger.warning("Cosmos DB not configured — falling back to JSON file persistence for sessions")
            self._impl = JSONFileDBClient()
        else:
            try:
                self._impl = CosmosSessionDBClient()
            except Exception as e:
                logger.error(f"Cosmos DB initialization failed: {e} — falling back to JSON file persistence")
                self._impl = JSONFileDBClient()

    async def create_session(self, session_doc: dict) -> dict:
        return await self._impl.create_session(session_doc)

    async def get_session(self, session_id: str) -> Optional[dict]:
        return await self._impl.get_session(session_id)

    async def update_session(self, session_id: str, candidate_id: str, updates: dict) -> dict:
        return await self._impl.update_session(session_id, candidate_id, updates)

    async def get_candidate_sessions(self, candidate_id: str, evaluation_id: Optional[str] = None) -> Optional[dict]:
        return await self._impl.get_candidate_sessions(candidate_id, evaluation_id)

    async def list_all_sessions(self) -> list[dict]:
        return await self._impl.list_all_sessions()

    async def delete_session(self, session_id: str, candidate_id: str) -> None:
        return await self._impl.delete_session(session_id, candidate_id)


# ─── Factory ────────────────────────────────────────────────────────────────

_db_instance: Optional[InterviewDB] = None


def get_interview_db() -> InterviewDB:
    """Get the interview database client singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = InterviewDB()
    return _db_instance