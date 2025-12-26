from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from fastapi import HTTPException
from models.models import User, Role, PatientCaregiver, VitalSigns, DeviceConnection
from schemas.schemas import (
    UserCreate, UserUpdate, UserResponse, 
    VitalSignsCreate, VitalSignsResponse,
    DeviceRegisterCreate, DeviceRegisterResponse,
    VitalSignsBatchCreate, VitalSignsBatchItem
)
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
        age=user_data.age,
        pain_type=user_data.pain_type,
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

def register_device(db: Session, data: DeviceRegisterCreate, ip_address: str):
    """Register/pair a new device to a user"""
    # Check user exists
    user = db.query(User).filter(User.user_id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with id {data.user_id} does not exist"
        )
    
    # Check if device_identifier already exists (another device with same ID)
    existing_device = db.query(DeviceConnection).filter(
        DeviceConnection.device_identifier == data.device_identifier
    ).first()
    
    if existing_device:
        # If same device_identifier but different user, update it
        if existing_device.user_id != data.user_id:
            existing_device.user_id = data.user_id
            existing_device.device_name = data.device_name
            existing_device.device_type = data.device_type
            existing_device.status = "online"
            existing_device.ip_address = ip_address
            existing_device.last_seen = datetime.utcnow()
            db.commit()
            db.refresh(existing_device)
            return existing_device
        # If same device_identifier and same user, just update info
        else:
            existing_device.device_name = data.device_name
            existing_device.device_type = data.device_type
            existing_device.status = "online"
            existing_device.ip_address = ip_address
            existing_device.last_seen = datetime.utcnow()
            db.commit()
            db.refresh(existing_device)
            return existing_device
    
    # Check if user already has a device (optional: you might want to allow multiple devices)
    user_device = db.query(DeviceConnection).filter(
        DeviceConnection.user_id == data.user_id
    ).first()
    
    if user_device:
        # Update existing device for this user
        user_device.device_identifier = data.device_identifier
        user_device.device_name = data.device_name
        user_device.device_type = data.device_type
        user_device.status = "online"
        user_device.ip_address = ip_address
        user_device.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(user_device)
        return user_device
    
    # Create new device
    device = DeviceConnection(
        user_id=data.user_id,
        device_identifier=data.device_identifier,
        device_name=data.device_name,
        device_type=data.device_type,
        status="online",
        battery=None,  # Will be updated later
        ip_address=ip_address,
        last_seen=datetime.utcnow()
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

def create_vital_signs_batch(db: Session, batch_data: VitalSignsBatchCreate):
    """Create multiple vital signs records in a batch"""
    # Check user exists
    user = db.query(User).filter(User.user_id == batch_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    created_count = 0
    failed_count = 0
    failed_items = []
    
    for idx, vital_item in enumerate(batch_data.vitals):
        try:
            # Create vital sign record
            vital_dict = vital_item.model_dump(exclude={'created_at'})
            vital_dict['user_id'] = batch_data.user_id
            
            # Create VitalSigns object
            vital = VitalSigns(**vital_dict)
            
            # If created_at is provided, set it explicitly (overrides server_default)
            if vital_item.created_at:
                vital.created_at = vital_item.created_at
            
            db.add(vital)
            created_count += 1
        except Exception as e:
            failed_count += 1
            failed_items.append({
                "index": idx,
                "error": str(e),
                "data": vital_item.model_dump()
            })
    
    # Commit all successful records
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save batch vitals: {str(e)}"
        )
    
    return {
        "created_count": created_count,
        "failed_count": failed_count,
        "failed_items": failed_items if failed_items else None
    }
