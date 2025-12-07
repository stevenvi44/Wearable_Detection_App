import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fastapi import FastAPI, Depends
from database import engine, Base
from utils import get_api_key
from routers import (
    users,
    auth
)

# Initialize FastAPI app
app = FastAPI(
    title="Wearable Fall detection APIs ",
    description="A complete FastAPI backend with multiple routers.",
    version="1.0.0",
    dependencies=[Depends(get_api_key)]
)


# Create tables in the database
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error creating tables: {e}")

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def read_root():
    return {"message": "Wearable App APIs"}
