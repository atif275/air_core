"""Unified database manager for both facial analysis and chatbot."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import sqlite3
import threading
from typing import Tuple, Optional, Generator
from contextlib import contextmanager
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import config after adding to path
from src.config import DB_PATH

Base = declarative_base()

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.db_path = DB_PATH  # Use the absolute path from config
        self._ensure_db_directory()
        
        # SQLAlchemy setup
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
        # Raw SQLite connection pool
        self._sqlite_connections = {}
        self._sqlite_locks = {}
        
        # Initialize tables
        Base.metadata.create_all(self.engine)
        
        self._initialized = True
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def get_sqlalchemy_session(self):
        """Get a SQLAlchemy session with proper cleanup."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_sqlite_connection(self, thread_id: Optional[int] = None) -> Generator[Tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
        """Get a SQLite connection and cursor for the current thread."""
        if thread_id is None:
            thread_id = threading.get_ident()
            
        if thread_id not in self._sqlite_connections:
            with self._lock:
                if thread_id not in self._sqlite_connections:
                    conn = sqlite3.connect(self.db_path)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA foreign_keys = ON")
                    self._sqlite_connections[thread_id] = conn
                    self._sqlite_locks[thread_id] = threading.Lock()
        
        with self._sqlite_locks[thread_id]:
            try:
                cursor = self._sqlite_connections[thread_id].cursor()
                yield self._sqlite_connections[thread_id], cursor
                self._sqlite_connections[thread_id].commit()
            except Exception:
                self._sqlite_connections[thread_id].rollback()
                raise
    
    def cleanup(self):
        """Clean up all database connections."""
        with self._lock:
            for conn in self._sqlite_connections.values():
                conn.close()
            self._sqlite_connections.clear()
            self._sqlite_locks.clear()
            self.Session.remove()

# Create singleton instance
db_manager = DatabaseManager() 