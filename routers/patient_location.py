from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import engine, get_db
from schemas.schemas import PatientLocationUpdate, PatientLocationResponse
from utils import ConnectionManager, CaregiverConnectionManager, get_api_key
from utils import API_KEY, API_KEY_NAME
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patient/location", tags=["Patient Location"])
manager = ConnectionManager()
caregiver_manager = CaregiverConnectionManager()


# 1) Patient sends live location (update + history)
@router.post("/update")
async def update_location(loc: PatientLocationUpdate, api_key: str = Depends(get_api_key)):
    with engine.begin() as conn:
        # Save history
        conn.execute(text("""
            INSERT INTO patient_locations (patient_id, latitude, longitude)
            VALUES (:pid, :lat, :lng)
        """), {
            "pid": loc.patient_id,
            "lat": loc.latitude,
            "lng": loc.longitude
        })

        # UPSERT last location
        conn.execute(text("""
            INSERT INTO patient_last_location (patient_id, latitude, longitude, updated_at)
            VALUES (:pid, :lat, :lng, NOW())
            ON CONFLICT (patient_id)
            DO UPDATE SET 
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                updated_at = NOW();
        """), {
            "pid": loc.patient_id,
            "lat": loc.latitude,
            "lng": loc.longitude
        })

    # Broadcast new location to all connected WebSocket clients (legacy support)
    location_message = {
        "patient_id": loc.patient_id,
        "latitude": loc.latitude,
        "longitude": loc.longitude
    }
    await manager.broadcast(location_message)
    
    # Broadcast to caregivers assigned to this patient
    db = next(get_db())
    try:
        await caregiver_manager.broadcast_to_patient_caregivers(
            patient_id=loc.patient_id,
            message=location_message,
            db=db,
            connection_type="location"
        )
    finally:
        db.close()

    return {"status": "success", "message": "Location updated"}


# 2) Caregiver fetches the latest patient location
@router.get("/latest/{patient_id}", response_model=PatientLocationResponse)
def get_latest_location(patient_id: int, api_key: str = Depends(get_api_key)):

    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT patient_id, latitude, longitude, updated_at
            FROM patient_last_location
            WHERE patient_id = :pid
        """), {"pid": patient_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Location not found")

    return PatientLocationResponse(
        patient_id=result.patient_id,
        latitude=result.latitude,
        longitude=result.longitude,
        updated_at=str(result.updated_at)
    )

# WebSocket Endpoint (legacy - broadcasts to all)
@router.websocket("/ws/location")
async def websocket_endpoint(websocket: WebSocket):
    # Manually get API key from query params
    api_key = websocket.query_params.get(API_KEY_NAME)
    if not api_key:
        await websocket.close(code=1008, reason="API Key missing")  # 1008 = policy violation
        return
    if api_key != API_KEY:
        await websocket.close(code=1008, reason="Invalid API Key")  
        return

    # Accept connection and store it
    await manager.connect(websocket)

    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Caregiver-specific location WebSocket
@router.websocket("/ws/location/caregiver/{caregiver_id}")
async def websocket_location_caregiver(websocket: WebSocket, caregiver_id: int):
    """
    WebSocket endpoint for caregivers to receive location updates for their assigned patients.
    
    Only receives updates for patients assigned to this caregiver.
    """
    from models.models import User, PatientCaregiver
    
    # Check API key from query params
    api_key = websocket.query_params.get(API_KEY_NAME)
    if not api_key:
        await websocket.close(code=1008, reason="API Key missing")
        return
    if api_key != API_KEY:
        await websocket.close(code=1008, reason="Invalid API Key")
        return
    
    # Verify caregiver exists and has patients assigned
    db = next(get_db())
    try:
        caregiver = db.query(User).filter(User.user_id == caregiver_id).first()
        if not caregiver:
            await websocket.close(code=1008, reason="Caregiver not found")
            return
        
        # Get assigned patients
        assignments = db.query(PatientCaregiver).filter(
            PatientCaregiver.caregiver_id == caregiver_id
        ).all()
        
        if not assignments:
            await websocket.close(code=1008, reason="No patients assigned to this caregiver")
            return
        
        patient_ids = [a.patient_id for a in assignments]
        
        # Connect caregiver
        await caregiver_manager.connect(websocket, caregiver_id)
        logger.info(f"Caregiver {caregiver_id} connected for location. Monitoring {len(patient_ids)} patient(s)")
        
        # Send welcome message with patient list
        await websocket.send_json({
            "type": "connection",
            "message": f"Connected to location WebSocket for caregiver {caregiver_id}",
            "caregiver_id": caregiver_id,
            "monitoring_patients": patient_ids
        })
        
        try:
            while True:
                # Keep the connection alive
                data = await websocket.receive_text()
                logger.debug(f"Received message from caregiver {caregiver_id}: {data}")
        except WebSocketDisconnect:
            caregiver_manager.disconnect(websocket)
            logger.info(f"Caregiver {caregiver_id} disconnected from location WebSocket")
    finally:
        db.close()
