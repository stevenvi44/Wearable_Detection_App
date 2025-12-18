from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.models import User, PatientCaregiver, DeviceConnection
from schemas.schemas import (
    DeviceStatusUpdate,
    DeviceStatusResponse,
    CaregiverContactResponse,
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

@router.get("/caregiver/contact/{patient_id}", response_model=CaregiverContactResponse)
def get_caregiver_contact(patient_id: int, db: Session = Depends(get_db)):
    # 1. Find caregiver assigned to patient
    connection = db.query(PatientCaregiver).filter(
        PatientCaregiver.patient_id == patient_id
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="No caregiver assigned to this patient")

    # 2. Get caregiver user record
    caregiver = db.query(User).filter(
        User.user_id == connection.caregiver_id
    ).first()

    if not caregiver:
        raise HTTPException(status_code=404, detail="Caregiver user not found")

    # 3. Return caregiver contact details
    return CaregiverContactResponse(
        caregiver_id=caregiver.user_id,
        caregiver_name=caregiver.name,
        phone_number=caregiver.phone_number,
    )