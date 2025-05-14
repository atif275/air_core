"""Database models and operations for the chatbot."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from .database_manager import Base, db_manager

class Person(Base):
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(50), nullable=False)
    ethnicity = Column(String(100), nullable=False)
    language = Column(String(50), nullable=False)
    personality_traits = Column(Text, nullable=False)  # JSON string of traits
    image = Column(LargeBinary)  # Added
    features = Column(LargeBinary)  # Added
    timestamp = Column(String)  # Added
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="person")
    face_embeddings = relationship("FaceEmbedding", back_populates="person")

class Active(Base):
    __tablename__ = 'active'
    
    person_id = Column(Integer, ForeignKey('persons.id'), primary_key=True)
    is_active = Column(Boolean, default=True)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    person = relationship("Person")

class Conversation(Base):
    __tablename__ = 'summary'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)
    summary = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Relationship
    person = relationship("Person", back_populates="conversations")

class FaceEmbedding(Base):
    __tablename__ = 'face_embeddings'
    
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'), nullable=False)
    features = Column(LargeBinary, nullable=False)
    quality_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    person = relationship("Person", back_populates="face_embeddings")

def get_database():
    """Get a database session using the unified database manager."""
    return db_manager.Session()  # Return the session directly instead of the context manager 