import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from dotenv import load_dotenv
import logging
from contextlib import contextmanager
from typing import Optional

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _connection_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.database_url = os.getenv('NEON_DATABASE_URL')
            if not self.database_url:
                raise ValueError("NEON_DATABASE_URL environment variable is required")
            
            self.min_connections = int(os.getenv('NEON_MIN_CONNECTIONS', '1'))
            self.max_connections = int(os.getenv('NEON_MAX_CONNECTIONS', '10'))
            self.initialized = True
    
    def _create_pool(self):
        """Create connection pool if it doesn't exist"""
        if self._connection_pool is None:
            try:
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    self.min_connections,
                    self.max_connections,
                    self.database_url,
                    cursor_factory=RealDictCursor
                )
                logger.info(f"Created connection pool with {self.min_connections}-{self.max_connections} connections")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise
    
    @contextmanager
    def get_connection(self):
        """Context manager to get database connection from pool"""
        if self._connection_pool is None:
            self._create_pool()
        
        connection = None
        try:
            connection = self._connection_pool.getconn()
            if connection:
                yield connection
            else:
                raise Exception("Unable to get connection from pool")
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                self._connection_pool.putconn(connection)
    
    def execute_query(self, query: str, params=None):
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchall()
    
    def execute_one(self, query: str, params=None):
        """Execute a SELECT query and return single result"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchone()
    
    def execute_count(self, query: str, params=None):
        """Execute a COUNT query and return the count value"""
        result = self.execute_one(query, params)
        if result and 'total' in result:
            return result['total']
        elif result and 'count' in result:
            return result['count']
        return 0
    
    def close_pool(self):
        """Close all connections in the pool"""
        if self._connection_pool:
            self._connection_pool.closeall()
            self._connection_pool = None
            logger.info("Closed database connection pool")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_connection():
    """Get database connection context manager"""
    return db_manager.get_connection()

def execute_query(query: str, params=None):
    """Execute query and return all results"""
    return db_manager.execute_query(query, params)

def execute_one(query: str, params=None):
    """Execute query and return single result"""
    return db_manager.execute_one(query, params)

def execute_count(query: str, params=None):
    """Execute count query and return count value"""
    return db_manager.execute_count(query, params)