from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from fastapi import HTTPException
from models.models import User, Role, PatientCaregiver
from schemas.schemas import UserCreate, UserUpdate, UserResponse
from utils import hash_password

# ------------------ CREATE USER ------------------ #
def create_user(db: Session, user_data: UserCreate) -> UserResponse:
    # Hash the password
    hashed_password = hash_password(user_data.password)
    
    # Fetch roles from DB if role_ids are provided
    roles = []
    if user_data.role_ids:
        roles = db.query(Role).filter(Role.role_id.in_(user_data.role_ids)).all()
    
    new_user = User(
        user_name=user_data.user_name,
        name=user_data.name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        location=user_data.location,
        password=hashed_password,
        roles=roles
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"User creation failed: {e.orig}")

# ------------------ GET USER BY ID ------------------ #
def get_user(db: Session, user_id: int) -> Optional[UserResponse]:
    return db.query(User).filter(User.user_id == user_id).first()

# ------------------ GET ALL USERS ------------------ #
def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[UserResponse]:
    return db.query(User).offset(skip).limit(limit).all()

# ------------------ UPDATE USER ------------------ #
def update_user(db: Session, user_id: int, user_data: UserUpdate) -> UserResponse:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError("User not found")

    # Update fields if provided
    for field, value in user_data.dict(exclude_unset=True).items():
        if field == "password" and value is not None:
            setattr(user, field, hash_password(value))
        elif field == "role_ids" and value is not None:
            roles = db.query(Role).filter(Role.role_id.in_(value)).all()
            user.roles = roles
        else:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user

# ------------------ DELETE USER ------------------ #
def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError("User not found")
    db.delete(user)
    db.commit()
    return True

# ------------------ link patient and caregiver ------------------ #
def verify_role(db: Session, user_id: int, required_role: str):
    user = db.query(User).options(joinedload(User.roles)).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, f"User {user_id} not found")
    roles = [r.role_name for r in user.roles]
    if required_role not in roles:
        raise HTTPException(400, f"User {user_id} must have role '{required_role}'")
    return True

def link_patient_and_caregiver(db: Session, patient_id: int, caregiver_id: int):
    # Validate roles
    verify_role(db, patient_id, "patient")
    verify_role(db, caregiver_id, "caregiver")

    # Prevent duplicates
    existing = db.query(PatientCaregiver).filter_by(
        patient_id=patient_id,
        caregiver_id=caregiver_id
    ).first()
    if existing:
        return existing

    # Create link
    link = PatientCaregiver(patient_id=patient_id, caregiver_id=caregiver_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


