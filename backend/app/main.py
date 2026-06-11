import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root of the backend folder is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.connection import engine
from app.infrastructure.database.models import Base
from app.presentation.api import router

# Automatically create PostgreSQL tables if they don't exist
try:
    print("Creating tables in PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
except Exception as e:
    print(f"Error creating database tables automatically: {e}")
    print("Please verify your PostgreSQL credentials and that the service is running.")

app = FastAPI(
    title="Social Media Automation API",
    description="Backend for social media automated login using DrissionPage",
    version="1.0.0"
)

# CORS config to allow local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For local testing we allow all, or we can restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)

@app.get("/")
def read_root():
    return {"status": "running", "message": "Social Media Login Automation Backend is active"}
