from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import settings
import logging

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    """
    Establish MongoDB Connection with explicit Database name
    """
    try:
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # We explicitly specify 'arthsavora' as the database name
        # This prevents the "No default database name" error
        db_instance.db = db_instance.client.arthsavora
        
        # Verify connection by pinging the admin database
        await db_instance.client.admin.command('ping')
        print("LOG: Successfully connected to MongoDB Atlas (Database: arthsavora)")
    except Exception as e:
        print(f"LOG: Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        print("LOG: Closed MongoDB connection")

def get_database():
    return db_instance.db