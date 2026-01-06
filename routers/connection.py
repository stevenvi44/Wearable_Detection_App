from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.models import User, PatientCaregiver, DeviceConnection
from datetime import datetime
from utils import get_api_key
from schemas.schemas import (
    DeviceStatusUpdate,
    DeviceStatusResponse,
    CaregiverContactResponse,
    DeviceRegisterCreate,
    DeviceRegisterResponse,
    CaregiverPatientsResponse,
    PatientListItem,
    PatientDashboardResponse
)
import crud.crud as crud


router = APIRouter(prefix="/device", tags=["Device Connection"])

@router.post("/device/status")
def update_device_status_endpoint(
    data: DeviceStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host
    return crud.update_device_status(db, data, ip)

@router.get("/device/status/{patient_id}", response_model=DeviceStatusResponse)
def get_device_status(patient_id: int, db: Session = Depends(get_db)):
    """
    Get latest device connection status and battery for a patient.
    `patient_id` here refers to the user's `user_id`.
    """
    device = (
        db.query(DeviceConnection)
        .filter(DeviceConnection.user_id == patient_id)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"No device connection found for patient_id {patient_id}",
        )

    return DeviceStatusResponse(status=device.status, battery=device.battery or 0)

@router.get("/caregiver/contact/{patient_id}", response_model=list[CaregiverContactResponse])
def get_caregiver_contact(patient_id: int, db: Session = Depends(get_db)):
    """
    Get all caregivers assigned to a patient.
    
    Returns a list of all caregivers with their contact information.
    If no caregivers are assigned, returns an empty list.
    """
    # 1. Find all caregivers assigned to patient
    connections = db.query(PatientCaregiver).filter(
        PatientCaregiver.patient_id == patient_id
    ).all()

    if not connections:
        return []  # Return empty list if no caregivers assigned

    # 2. Get all caregiver user records
    caregiver_ids = [conn.caregiver_id for conn in connections]
    caregivers = db.query(User).filter(
        User.user_id.in_(caregiver_ids)
    ).all()

    if not caregivers:
        return []  # Return empty list if caregivers not found

    # 3. Return list of caregiver contact details
    return [
        CaregiverContactResponse(
            caregiver_id=caregiver.user_id,
            caregiver_name=caregiver.name,
            phone_number=caregiver.phone_number,
        )
        for caregiver in caregivers
    ]

@router.post("/register", response_model=DeviceRegisterResponse, status_code=201)
def register_device_endpoint(
    data: DeviceRegisterCreate,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Register/pair a watch device to a user.
    
    This endpoint is used when pairing a watch to a user account.
    The device_identifier should be unique (e.g., MAC address or serial number).
    """
    ip = request.client.host
    device = crud.register_device(db, data, ip)
    
    # Convert to response model
    return DeviceRegisterResponse(
        device_id=device.device_id,
        user_id=device.user_id,
        device_identifier=device.device_identifier or "",
        device_name=device.device_name,
        device_type=device.device_type,
        status=device.status,
        battery=device.battery,
        paired_at=device.last_seen or datetime.utcnow()
    )

@router.get("/caregiver/patients/{caregiver_id}", response_model=CaregiverPatientsResponse)
def get_caregiver_patients(
    caregiver_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Get all patients assigned to a caregiver.
    
    This endpoint allows caregivers to see the list of patients they are monitoring.
    """
    # Verify caregiver exists
    caregiver = db.query(User).filter(User.user_id == caregiver_id).first()
    if not caregiver:
        raise HTTPException(status_code=404, detail="Caregiver not found")
    
    # Get all patient-caregiver relationships for this caregiver
    connections = db.query(PatientCaregiver).filter(
        PatientCaregiver.caregiver_id == caregiver_id
    ).all()
    
    if not connections:
        return CaregiverPatientsResponse(
            caregiver_id=caregiver_id,
            patients=[]
        )
    
    # Get patient details
    patient_ids = [conn.patient_id for conn in connections]
    patients = db.query(User).filter(User.user_id.in_(patient_ids)).all()
    
    patient_list = [
        PatientListItem(
            patient_id=patient.user_id,
            patient_name=patient.name,
            patient_email=patient.email,
            patient_phone=patient.phone_number,
            age=patient.age
        )
        for patient in patients
    ]
    
    return CaregiverPatientsResponse(
        caregiver_id=caregiver_id,
        patients=patient_list
    )

@router.get("/caregiver/dashboard/{caregiver_id}/{patient_id}", response_model=PatientDashboardResponse)
def get_patient_dashboard(
    caregiver_id: int,
    patient_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Get complete dashboard data for a patient (vitals, connection status, location).
    
    This endpoint combines all patient monitoring data in one response for caregivers.
    """
    # Verify caregiver-patient relationship
    connection = db.query(PatientCaregiver).filter(
        PatientCaregiver.caregiver_id == caregiver_id,
        PatientCaregiver.patient_id == patient_id
    ).first()
    
    if not connection:
        raise HTTPException(
            status_code=403,
            detail="Caregiver is not assigned to this patient"
        )
    
    # Get patient info
    patient = db.query(User).filter(User.user_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get latest vitals
    from crud.crud import get_latest_vital
    latest_vitals = get_latest_vital(db, patient_id)
    
    # Get device status
    device = db.query(DeviceConnection).filter(
        DeviceConnection.user_id == patient_id
    ).first()
    device_status = None
    if device:
        device_status = DeviceStatusResponse(
            status=device.status,
            battery=device.battery or 0
        )
    
    # Get location
    from sqlalchemy import text
    from database import engine
    location = None
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT patient_id, latitude, longitude, updated_at
            FROM patient_last_location
            WHERE patient_id = :pid
        """), {"pid": patient_id}).fetchone()
        
        if result:
            from schemas.schemas import PatientLocationResponse
            location = PatientLocationResponse(
                patient_id=result.patient_id,
                latitude=result.latitude,
                longitude=result.longitude,
                updated_at=str(result.updated_at)
            )
    
    return PatientDashboardResponse(
        patient_id=patient_id,
        patient_name=patient.name,
        latest_vitals=latest_vitals,
        device_status=device_status,
        location=location
    )