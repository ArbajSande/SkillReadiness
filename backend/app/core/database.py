import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("skillreadiness.database")

class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    is_connected: bool = False
    last_error: Optional[str] = None

    async def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000
            )
            # Ping database to verify connection
            await self.client.admin.command('ping')
            self.db = self.client[settings.DB_NAME]
            self.is_connected = True
            self.last_error = None
            logger.info(f"Successfully connected to MongoDB database: {settings.DB_NAME}")
            
            # Ensure indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.resumes.create_index("user_id")
            await self.db.assessments.create_index("user_id")
            await self.db.readiness_records.create_index("user_id")
            await self.db.learning_paths.create_index("user_id")
        except Exception as e:
            self.is_connected = False
            self.last_error = str(e)
            logger.warning(f"Could not connect to primary MongoDB ({e}). Memory fallback store initialized.")

    async def disconnect(self):
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("MongoDB connection closed.")

    async def check_health(self) -> Dict[str, Any]:
        if self.client and self.is_connected:
            try:
                ping_res = await self.client.admin.command('ping')
                return {
                    "status": "connected",
                    "database": settings.DB_NAME,
                    "engine": "MongoDB",
                    "ping": ping_res
                }
            except Exception as e:
                self.is_connected = False
                self.last_error = str(e)
                return {
                    "status": "error",
                    "database": settings.DB_NAME,
                    "engine": "MongoDB",
                    "error": str(e)
                }
        return {
            "status": "disconnected" if not self.is_connected else "connected",
            "database": settings.DB_NAME,
            "engine": "MongoDB (Fallback mode)" if not self.is_connected else "MongoDB",
            "details": self.last_error or "Not connected"
        }

db_manager = DatabaseManager()

def get_db() -> Optional[AsyncIOMotorDatabase]:
    return db_manager.db
