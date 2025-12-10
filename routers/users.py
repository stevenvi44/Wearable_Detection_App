from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db  # Database session dependency
from schemas.schemas import UserCreate, UserUpdate, UserResponse
from crud.crud import create_user, get_user, get_users, update_user, delete_user
from utils import get_api_key

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# CREATE USER 
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def api_create_user(user_data: UserCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)) -> UserResponse:
    """
    Create a new user with hashed password and optional roles.
    """
    try:
        user = create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# GET ALL USERS
@router.get("/", response_model=List[UserResponse])
def api_get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)) -> List[UserResponse]:
    """
    Get a list of users with optional pagination.
    """
    return get_users(db, skip=skip, limit=limit)

# GET USER BY ID 
@router.get("/{user_id}", response_model=UserResponse)
def api_get_user(user_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)) -> UserResponse:
    """
    Get a single user by their ID.
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# UPDATE USER 
@router.put("/{user_id}", response_model=UserResponse)
def api_update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)) -> UserResponse:
    """
    Update a user’s information, password, or roles.
    """
    try:
        user = update_user(db, user_id, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# DELETE USER
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_user(user_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)) -> None:
    """
    Delete a user by their ID.
    """
    try:
        delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
