#!/usr/bin/env python3
"""
SQLAlchemy models for the LibGen Dashboard
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Optional profile fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Search preferences
    preferred_language = Column(String(10), default="en")
    books_per_page = Column(Integer, default=20)
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"

class SearchHistory(Base):
    """Store user search history for analytics and quick access"""
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)  # Foreign key to users
    query = Column(String(500), nullable=False)
    results_count = Column(Integer, default=0)
    search_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, query='{self.query}')>"

class BookmarkHistory(Base):
    """Store user bookmarked books"""
    __tablename__ = "bookmark_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)  # Foreign key to users
    book_md5 = Column(String(32), nullable=False)  # MD5 hash of the book
    book_title = Column(String(500), nullable=False)
    book_author = Column(String(300), nullable=True)
    book_extension = Column(String(10), nullable=True)
    book_size = Column(String(20), nullable=True)
    book_year = Column(String(10), nullable=True)
    bookmarked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<BookmarkHistory(id={self.id}, user_id={self.user_id}, title='{self.book_title}')>"
