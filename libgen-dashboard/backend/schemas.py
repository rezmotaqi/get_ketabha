#!/usr/bin/env python3
"""
Pydantic schemas for request/response models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    preferred_language: Optional[str] = None
    books_per_page: Optional[int] = Field(None, ge=10, le=100)

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    email: Optional[str] = None

# Book search schemas
class BookSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: Optional[int] = Field(50, ge=1, le=200)
    search_type: Optional[str] = "title"  # title, author, isbn, etc.

class BookInfo(BaseModel):
    title: str
    author: Optional[str] = None
    year: Optional[str] = None
    pages: Optional[str] = None
    language: Optional[str] = None
    size: Optional[str] = None
    extension: Optional[str] = None
    md5: Optional[str] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None

class BookSearchResponse(BaseModel):
    query: str
    total_results: int
    books: List[BookInfo]
    user_id: int
    search_timestamp: datetime = Field(default_factory=datetime.utcnow)

class DownloadLink(BaseModel):
    url: str
    type: str
    mirror: Optional[str] = None
    quality: Optional[str] = None

class DownloadLinksResponse(BaseModel):
    md5: str
    download_links: List[DownloadLink]
    user_id: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

# Search history schemas
class SearchHistoryCreate(BaseModel):
    query: str
    results_count: int

class SearchHistoryResponse(BaseModel):
    id: int
    query: str
    results_count: int
    search_timestamp: datetime

    class Config:
        from_attributes = True

# Bookmark schemas
class BookmarkCreate(BaseModel):
    book_md5: str
    book_title: str
    book_author: Optional[str] = None
    book_extension: Optional[str] = None
    book_size: Optional[str] = None
    book_year: Optional[str] = None

class BookmarkResponse(BaseModel):
    id: int
    book_md5: str
    book_title: str
    book_author: Optional[str] = None
    book_extension: Optional[str] = None
    book_size: Optional[str] = None
    book_year: Optional[str] = None
    bookmarked_at: datetime

    class Config:
        from_attributes = True

# Dashboard stats schema
class DashboardStats(BaseModel):
    total_searches: int
    total_bookmarks: int
    recent_searches: List[SearchHistoryResponse]
    popular_books: List[BookmarkResponse]
    user_stats: Dict[str, Any]

# API response schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
