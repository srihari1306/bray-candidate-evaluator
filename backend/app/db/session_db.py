"""
Persistence layer for interview sessions.
Primary: Azure Cosmos DB for NoSQL.
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



class CosmosSessionDBClient:
    def __init__(self):
        from azure.cosmos import CosmosClient

        settings = get_settings()
        self._client = CosmosClient(
            url=settings.AZURE_COSMOS_ENDPOINT,
            credential=settings.AZURE_COSMOS_KEY,
        )
        self._database = self._client.get_database_client(settings.AZURE_COSMOS_DATABASE)
        self._container = self._database.get_container_client(settings.AZURE_COSMOS_SESSIONS_CONTAINER)
        logger.info("Cosmos DB session store initialized")

    async def create_session(self, session_doc: dict) -> dict:
        def _upsert():
            self._container.upsert_item(session_doc)

        logger.info(f"[Cosmos DB] Creating session {session_doc['id']} for candidate {session_doc.get('candidate_name', 'unknown')}")
        await asyncio.to_thread(_upsert)
        return session_doc

    async def get_session(self, session_id: str) -> Optional[dict]:
        def _query():
            items = list(self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": session_id}],
                enable_cross_partition_query=True,
            ))
            return items[0] if items else None

        return await asyncio.to_thread(_query)

    async def update_session(self, session_id: str, candidate_id: str, updates: dict) -> dict:
        def _read_merge_upsert():
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
        def _query():
            return list(self._container.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            ))

        return await asyncio.to_thread(_query)

    async def delete_session(self, session_id: str, candidate_id: str) -> None:
        def _delete():
            self._container.delete_item(item=session_id, partition_key=candidate_id)

        logger.info(f"[Cosmos DB] Deleting session {session_id}")
        await asyncio.to_thread(_delete)


class InterviewDB:

    def __init__(self):
        settings = get_settings()

        endpoint = settings.AZURE_COSMOS_ENDPOINT
        if not endpoint or "your-account" in endpoint or "your-" in endpoint:
            logger.warning("Cosmos DB not configured")
        else:
            try:
                self._impl = CosmosSessionDBClient()
            except Exception as e:
                logger.error(f"Cosmos DB initialization failed: {e}")

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



_db_instance: Optional[InterviewDB] = None


def get_interview_db() -> InterviewDB:
    global _db_instance
    if _db_instance is None:
        _db_instance = InterviewDB()
    return _db_instance