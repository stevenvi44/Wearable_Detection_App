from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import date, datetime, time as time_type

from database import get_db
from models.models import Medication, MedicationDose, User
from schemas.schemas import (
    TodayMedicationRequest,
    TodayMedicationResponse,
    TakeMedicationResponse,
    SkipMedicationRequest,
    SkipMedicationResponse,
    MedicationCreate,
    MedicationResponse
)

router = APIRouter(
    prefix="/api/medications",
    tags=["Medications"]
)


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
def add_medication(
    payload: MedicationCreate,
    db: Session = Depends(get_db)
):
    """Add a new medication to user's medication list"""
    # Validate user_id
    if payload.user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer"
        )
    
    # Validate user exists
    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {payload.user_id} not found"
        )
    
    # Validate name
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medication name is required and cannot be empty"
        )
    
    if len(payload.name) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medication name cannot exceed 200 characters"
        )
    
    # Validate dosage
    if not payload.dosage or not payload.dosage.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosage is required and cannot be empty"
        )
    
    if len(payload.dosage) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosage cannot exceed 50 characters"
        )
    
    # Validate frequency
    if not payload.frequency or not payload.frequency.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frequency is required and cannot be empty"
        )
    
    try:
        # Create new medication
        medication = Medication(
            user_id=payload.user_id,
            name=payload.name.strip(),
            dosage=payload.dosage.strip(),
            frequency=payload.frequency.strip()
        )
        
        db.add(medication)
        db.commit()
        db.refresh(medication)
        
        return {
            "medication_id": medication.medication_id,
            "user_id": medication.user_id,
            "name": medication.name,
            "dosage": medication.dosage,
            "frequency": medication.frequency
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create medication: {str(e)}"
        )


@router.post("/{dose_id}/take", response_model=TakeMedicationResponse)
def take_medication(
    dose_id: int,
    db: Session = Depends(get_db)
):
    """Mark medication dose as taken"""
    # Validate dose_id
    if dose_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dose_id must be a positive integer"
        )
    
    # Check if dose exists
    dose = db.query(MedicationDose).filter_by(dose_id=dose_id).first()

    if not dose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Dose with id {dose_id} not found"
        )
    
    # Validate dose is for today
    today = date.today()
    if dose.scheduled_date != today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot take medication scheduled for {dose.scheduled_date}. Only today's medications can be taken."
        )
    
    # Check if already taken
    if dose.status == "taken":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This medication has already been marked as taken"
        )

    try:
        dose.status = "taken"
        dose.action_time = datetime.utcnow()
        db.commit()
        db.refresh(dose)

        return {
            "message": "Medication marked as taken",
            "taken_at": dose.action_time.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update medication: {str(e)}"
        )

@router.post("/{dose_id}/skip", response_model=SkipMedicationResponse)
def skip_medication(
    dose_id: int,
    payload: SkipMedicationRequest,
    db: Session = Depends(get_db)
):
    """Mark medication dose as skipped"""
    # Validate dose_id
    if dose_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dose_id must be a positive integer"
        )
    
    # Validate reason
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required and cannot be empty"
        )
    
    # Check if dose exists
    dose = db.query(MedicationDose).filter_by(dose_id=dose_id).first()

    if not dose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Dose with id {dose_id} not found"
        )
    
    # Validate dose is for today
    today = date.today()
    if dose.scheduled_date != today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot skip medication scheduled for {dose.scheduled_date}. Only today's medications can be skipped."
        )
    
    # Check if already taken
    if dose.status == "taken":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot skip medication that has already been taken"
        )
    
    # Check if already skipped
    if dose.status == "skipped":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This medication has already been marked as skipped"
        )

    try:
        dose.status = "skipped"
        dose.action_time = datetime.utcnow()
        # Note: reason is accepted but not stored in current schema
        # Could add a reason field to MedicationDose model if needed
        db.commit()
        db.refresh(dose)

        return {
            "message": "Medication skipped"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update medication: {str(e)}"
        )

@router.get("/today", response_model=TodayMedicationResponse)
def get_today_medications(
    user_id: int = Query(..., gt=0, description="The ID of the user"),
    db: Session = Depends(get_db)
):
    """Get today's medications for a user"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    today = date.today()

    doses = (
        db.query(
            MedicationDose.dose_id,
            Medication.medication_id,
            Medication.name,
            Medication.dosage,
            Medication.frequency,
            MedicationDose.scheduled_time,
            MedicationDose.status
        )
        .join(Medication)
        .filter(
            Medication.user_id == user_id,
            MedicationDose.scheduled_date == today
        )
        .order_by(Medication.medication_id, MedicationDose.scheduled_time)
        .all()
    )

    # Group doses by medication_id and combine scheduled times
    medication_groups = {}
    for d in doses:
        key = d.medication_id
        if key not in medication_groups:
            medication_groups[key] = {
                "dose_id": d.dose_id,  # Use first dose_id
                "medication_id": d.medication_id,
                "name": d.name,
                "dosage": d.dosage,
                "frequency": d.frequency,
                "scheduled_times": [],
                "statuses": []
            }
        medication_groups[key]["scheduled_times"].append(d.scheduled_time.strftime("%H:%M"))
        medication_groups[key]["statuses"].append(d.status or "pending")

    # Build response items with combined scheduled times
    items = []
    for med_data in medication_groups.values():
        # Sort scheduled times
        med_data["scheduled_times"].sort()
        # Combine scheduled times with comma and space
        scheduled_time_str = ", ".join(med_data["scheduled_times"])
        # Use the most relevant status (prefer "pending" if any is pending, otherwise use first)
        status = "pending" if "pending" in med_data["statuses"] else med_data["statuses"][0] if med_data["statuses"] else "pending"
        
        items.append({
            "dose_id": med_data["dose_id"],
            "medication_id": med_data["medication_id"],
            "name": med_data["name"],
            "dosage": med_data["dosage"],
            "frequency": med_data["frequency"],
            "scheduled_time": scheduled_time_str,
            "status": status
        })

    return {
        "date": today.isoformat(),
        "items": items
    }

@router.post("/today", response_model=TodayMedicationResponse, status_code=status.HTTP_201_CREATED)
def post_today_medications(
    payload: TodayMedicationRequest,
    db: Session = Depends(get_db)
):
    """Create or update today's medications and doses"""
    # Validate user_id
    if payload.user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer"
        )
    
    # Validate user exists
    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {payload.user_id} not found"
        )
    
    # Validate items array
    if not payload.items or len(payload.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="items array cannot be empty. At least one medication item is required."
        )
    
    # Validate items array size
    if len(payload.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process more than 100 medication items at once"
        )
    
    today = date.today()
    processed_doses = []
    valid_statuses = ["pending", "taken", "skipped", "overdue"]

    try:
        for idx, item in enumerate(payload.items):
            # Validate medication_id
            if item.medication_id < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: medication_id cannot be negative"
                )
            
            # Validate dose_id
            if item.dose_id < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: dose_id cannot be negative. Use 0 to create a new dose."
                )
            
            # Validate name
            if not item.name or not item.name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: name is required and cannot be empty"
                )
            
            if len(item.name) > 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: name cannot exceed 200 characters"
                )
            
            # Validate dosage
            if not item.dosage or not item.dosage.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: dosage is required and cannot be empty"
                )
            
            if len(item.dosage) > 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: dosage cannot exceed 50 characters"
                )
            
            # Validate frequency
            if not item.frequency or not item.frequency.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: frequency is required and cannot be empty"
                )
            
            # Validate time format
            if not item.scheduled_time or not item.scheduled_time.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: time is required and cannot be empty"
                )
            
            # Parse time string(s) - can be single time (HH:MM) or comma-separated times (HH:MM, HH:MM, ...)
            scheduled_times = []
            try:
                # Split by comma to handle multiple times
                time_strings = [t.strip() for t in item.scheduled_time.split(",") if t.strip()]
                
                if not time_strings:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Item {idx + 1}: No valid times found in '{item.scheduled_time}'. Expected format: HH:MM or HH:MM, HH:MM (e.g., '09:30' or '08:00, 20:00')"
                    )
                
                # Parse each time string
                for time_str in time_strings:
                    time_parts = time_str.split(":")
                    if len(time_parts) != 2:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Item {idx + 1}: Invalid time format '{time_str}'. Expected format: HH:MM (24-hour format, e.g., '09:30', '14:00')"
                        )
                    
                    try:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Item {idx + 1}: Invalid time format '{time_str}'. Hour and minute must be numbers."
                        )
                    
                    if hour < 0 or hour > 23:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Item {idx + 1}: hour must be between 0 and 23. Got: {hour} in '{time_str}'"
                        )
                    
                    if minute < 0 or minute > 59:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Item {idx + 1}: minute must be between 0 and 59. Got: {minute} in '{time_str}'"
                        )
                    
                    scheduled_times.append(time_type(hour, minute))
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {idx + 1}: Invalid time format '{item.scheduled_time}'. Expected format: HH:MM or HH:MM, HH:MM (e.g., '09:30' or '08:00, 20:00'). Error: {str(e)}"
                )
            
            # Validate status
            if item.status:
                if item.status not in valid_statuses:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Item {idx + 1}: status must be one of: {', '.join(valid_statuses)}. Got: '{item.status}'"
                    )

            # Handle medication - create or update
            medication = None
            if item.medication_id and item.medication_id > 0:
                # Look for existing medication
                medication = db.query(Medication).filter(
                    Medication.medication_id == item.medication_id,
                    Medication.user_id == payload.user_id
                ).first()
                
                if medication:
                    # Update existing medication details
                    if item.name:
                        medication.name = item.name
                    if item.dosage:
                        medication.dosage = item.dosage
                    if item.frequency:
                        medication.frequency = item.frequency
                else:
                    # Create medication with specified ID
                    medication = Medication(
                        medication_id=item.medication_id,
                        user_id=payload.user_id,
                        name=item.name,
                        dosage=item.dosage,
                        frequency=item.frequency
                    )
                    db.add(medication)
            else:
                # Create new medication (ID will be auto-generated)
                medication = Medication(
                    user_id=payload.user_id,
                    name=item.name,
                    dosage=item.dosage,
                    frequency=item.frequency
                )
                db.add(medication)
            
            db.flush()  # Flush to get the medication_id for new medications

            # Use the medication_id from the medication object (handles auto-generated IDs)
            current_medication_id = medication.medication_id
            
            # Handle multiple scheduled times - create a dose for each time
            # If dose_id is provided and there's only one time, try to update that specific dose
            # Otherwise, create new doses for all times
            if len(scheduled_times) == 1 and item.dose_id and item.dose_id > 0:
                # Single time with dose_id - try to update existing dose
                scheduled_time = scheduled_times[0]
                dose = db.query(MedicationDose).filter(
                    MedicationDose.dose_id == item.dose_id,
                    MedicationDose.medication_id == current_medication_id,
                    MedicationDose.scheduled_date == today
                ).first()
                
                if dose:
                    # Update existing dose
                    dose.scheduled_time = scheduled_time
                    dose.status = item.status or dose.status or "pending"
                    processed_doses.append(dose)
                else:
                    # Dose not found, create new one
                    dose = MedicationDose(
                        medication_id=current_medication_id,
                        scheduled_date=today,
                        scheduled_time=scheduled_time,
                        status=item.status or "pending"
                    )
                    db.add(dose)
                    processed_doses.append(dose)
            else:
                # Multiple times or no dose_id - create new doses for each time
                # If dose_id was provided but we have multiple times, we'll create new doses
                # (dose_id is ignored in this case)
                for scheduled_time in scheduled_times:
                    dose = MedicationDose(
                        medication_id=current_medication_id,
                        scheduled_date=today,
                        scheduled_time=scheduled_time,
                        status=item.status or "pending"
                    )
                    db.add(dose)
                    processed_doses.append(dose)

        db.commit()
        
        # Refresh all records to get IDs
        for dose in processed_doses:
            db.refresh(dose)

        # Query all doses for today to return complete list
        all_doses = (
            db.query(
                MedicationDose.dose_id,
                Medication.medication_id,
                Medication.name,
                Medication.dosage,
                Medication.frequency,
                MedicationDose.scheduled_time,
                MedicationDose.status
            )
            .join(Medication)
            .filter(
                Medication.user_id == payload.user_id,
                MedicationDose.scheduled_date == today
            )
            .order_by(Medication.medication_id, MedicationDose.scheduled_time)
            .all()
        )

        # Group doses by medication_id and combine scheduled times
        medication_groups = {}
        for d in all_doses:
            key = d.medication_id
            if key not in medication_groups:
                medication_groups[key] = {
                    "dose_id": d.dose_id,  # Use first dose_id
                    "medication_id": d.medication_id,
                    "name": d.name or "",
                    "dosage": d.dosage or "",
                    "frequency": d.frequency or "",
                    "scheduled_times": [],
                    "statuses": []
                }
            medication_groups[key]["scheduled_times"].append(d.scheduled_time.strftime("%H:%M"))
            medication_groups[key]["statuses"].append(d.status or "pending")

        # Build response items with combined scheduled times
        items = []
        for med_data in medication_groups.values():
            # Sort scheduled times
            med_data["scheduled_times"].sort()
            # Combine scheduled times with comma and space
            scheduled_time_str = ", ".join(med_data["scheduled_times"])
            # Use the most relevant status (prefer "pending" if any is pending, otherwise use first)
            combined_status = (
                "pending"
                if "pending" in med_data["statuses"]
                else med_data["statuses"][0]
                if med_data["statuses"]
                else "pending"
            )

            items.append({
                "dose_id": med_data["dose_id"],
                "medication_id": med_data["medication_id"],
                "name": med_data["name"],
                "dosage": med_data["dosage"],
                "frequency": med_data["frequency"],
                "scheduled_time": scheduled_time_str,
                "status": combined_status,
            })

        return {
            "date": today.isoformat(),
            "items": items
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save medications: {str(e)}"
        )