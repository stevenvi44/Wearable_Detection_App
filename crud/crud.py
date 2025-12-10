from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from fastapi import HTTPException
from models.models import User, Role, PatientCaregiver, VitalSigns, DeviceConnection
from schemas.schemas import UserCreate, UserUpdate, UserResponse, VitalSignsCreate, VitalSignsResponse, DeviceStatusUpdate
from utils import hash_password
from datetime import datetime



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

# ------------------ Vital ------------------ #
def create_vital_sign(db: Session, vital_data: VitalSignsCreate):
    # Check if user exists
    user = db.query(User).filter(User.user_id == vital_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check patient role
    is_patient = any(role.role_name == "patient" for role in user.roles)
    if not is_patient:
        raise HTTPException(status_code=403, detail="Only patients can submit vitals.")

    # Insert vital signs
    vital = VitalSigns(**vital_data.model_dump())
    db.add(vital)
    db.commit()
    db.refresh(vital)

    return vital

def get_latest_vital(db: Session, user_id: int):
    vital = (
        db.query(VitalSigns)
        .filter(VitalSigns.user_id == user_id)
        .order_by(VitalSigns.created_at.desc())
        .first()
    )

    if not vital:
        return None

    return VitalSignsResponse.model_validate(vital)

def get_vital_history(db: Session, user_id: int, limit: int = 50):
    vitals = (
        db.query(VitalSigns)
        .filter(VitalSigns.user_id == user_id)
        .order_by(VitalSigns.created_at.desc())
        .limit(limit)
        .all()
    )

    return [VitalSignsResponse.model_validate(v) for v in vitals]

def update_device_status(db, data, ip_address: str):

    # Check user exists
    user = db.query(User).filter(User.user_id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with id {data.user_id} does not exist"
        )

    # Get existing device
    device = db.query(DeviceConnection).filter(
        DeviceConnection.user_id == data.user_id
    ).first()

    # Update existing
    if device:
        device.status = data.status
        device.battery = data.battery
        device.last_seen = datetime.utcnow()
        device.ip_address = ip_address

    # Create new
    else:
        device = DeviceConnection(
            user_id=data.user_id,
            status=data.status,
            battery=data.battery,
            ip_address=ip_address,
            last_seen=datetime.utcnow()
        )
        db.add(device)

    db.commit()
    db.refresh(device)
    return device
