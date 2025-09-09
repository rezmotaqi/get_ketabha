#!/usr/bin/env python3
"""
LibGen Dashboard Backend
FastAPI application for LibGen book search with user authentication
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timedelta
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from database import get_db, init_db
from models import User
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from schemas import (
    UserCreate, 
    UserLogin, 
    Token, 
    UserResponse,
    BookSearchRequest,
    BookSearchResponse
)
from libgen_service import LibGenService

# Initialize FastAPI app
app = FastAPI(
    title="LibGen Dashboard API",
    description="Search LibGen books with user authentication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vue dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize LibGen service
libgen_service = LibGenService()

# Initialize database
@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "LibGen Dashboard API", 
        "status": "running",
        "timestamp": datetime.utcnow()
    }

@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        is_active=db_user.is_active,
        created_at=db_user.created_at
    )

@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@app.post("/search", response_model=BookSearchResponse)
async def search_books(
    search_request: BookSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """Search for books in LibGen"""
    try:
        results = await libgen_service.search_books(
            query=search_request.query,
            max_results=search_request.max_results or 50
        )
        
        return BookSearchResponse(
            query=search_request.query,
            total_results=len(results),
            books=results,
            user_id=current_user.id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@app.get("/book/{md5_hash}/download-links")
async def get_download_links(
    md5_hash: str,
    current_user: User = Depends(get_current_user)
):
    """Get download links for a specific book"""
    try:
        links = await libgen_service.get_download_links(md5_hash)
        return {
            "md5": md5_hash,
            "download_links": links,
            "user_id": current_user.id
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get download links: {str(e)}"
        )

@app.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "mirrors_available": len(libgen_service.get_available_mirrors()),
        "server_status": "online",
        "last_updated": datetime.utcnow()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
