import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
from app.core.database import db_manager

# Resilient in-memory fallback store
_memory_store: Dict[str, Dict[str, Dict[str, Any]]] = {
    "users": {},
    "resumes": {},
    "assessments": {},
    "readiness_records": {},
    "learning_paths": {}
}

def _to_clean_dict(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d["_id"])
        del d["_id"]
    return d

class BaseRepo:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def col(self):
        if db_manager.is_connected and db_manager.db is not None:
            return db_manager.db[self.collection_name]
        return None

    async def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(data)
        now = datetime.now(timezone.utc).isoformat()
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now

        if self.col is not None:
            result = await self.col.insert_one(data)
            data["id"] = str(result.inserted_id)
            if "_id" in data:
                del data["_id"]
            return data
        else:
            item_id = str(uuid.uuid4())
            data["id"] = item_id
            _memory_store[self.collection_name][item_id] = data
            return data

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.col is not None:
            mongo_query = dict(query)
            if "id" in mongo_query:
                try:
                    mongo_query["_id"] = ObjectId(mongo_query.pop("id"))
                except Exception:
                    pass
            doc = await self.col.find_one(mongo_query)
            return _to_clean_dict(doc)
        else:
            for item in _memory_store[self.collection_name].values():
                matches = True
                for k, v in query.items():
                    if item.get(k) != v:
                        matches = False
                        break
                if matches:
                    return dict(item)
            return None

    async def find_many(self, query: Dict[str, Any], sort_key: str = "created_at", limit: int = 50) -> List[Dict[str, Any]]:
        if self.col is not None:
            cursor = self.col.find(query).sort(sort_key, -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [_to_clean_dict(d) for d in docs]
        else:
            results = []
            for item in _memory_store[self.collection_name].values():
                matches = True
                for k, v in query.items():
                    if item.get(k) != v:
                        matches = False
                        break
                if matches:
                    results.append(dict(item))
            results.sort(key=lambda x: x.get(sort_key, ""), reverse=True)
            return results[:limit]

    async def update(self, filter_query: Dict[str, Any], update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        update_data["updated_at"] = now

        if self.col is not None:
            mongo_query = dict(filter_query)
            if "id" in mongo_query:
                try:
                    mongo_query["_id"] = ObjectId(mongo_query.pop("id"))
                except Exception:
                    pass
            await self.col.update_one(mongo_query, {"$set": update_data})
            return await self.find_one(filter_query)
        else:
            item = await self.find_one(filter_query)
            if item:
                item_id = item["id"]
                _memory_store[self.collection_name][item_id].update(update_data)
                return dict(_memory_store[self.collection_name][item_id])
            return None

users_repo = BaseRepo("users")
resumes_repo = BaseRepo("resumes")
assessments_repo = BaseRepo("assessments")
readiness_repo = BaseRepo("readiness_records")
learning_paths_repo = BaseRepo("learning_paths")
