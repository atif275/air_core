from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Person(Base):
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    age = Column(Integer)
    gender = Column(String(50))
    ethnicity = Column(String(100))
    language = Column(String(50))
    personality_traits = Column(Text)  # JSON string of traits
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="person")

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
    person_id = Column(Integer, ForeignKey('persons.id'))
    summary = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Relationship
    person = relationship("Person", back_populates="conversations")

# Database connection
def get_database():
    engine = create_engine('sqlite:///data/database.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session() 