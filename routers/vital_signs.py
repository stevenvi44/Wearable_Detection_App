from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from utils import ConnectionManagerVital, CaregiverConnectionManager, get_api_key
import crud.crud as crud_vitals
from schemas.schemas import (
    VitalSignsCreate, 
    VitalSignsResponse,
    VitalSignsBatchCreate,
    VitalSignsBatchResponse,
    MLPredictionResponse
)
from utils import API_KEY, API_KEY_NAME
from ml_service import predict_emergency_status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vitals",
    tags=["Vital Signs"]
)

manager = ConnectionManagerVital()
caregiver_manager = CaregiverConnectionManager()

# -----------------------
# POST /vitals/update
# -----------------------
@router.post("/update", response_model=VitalSignsResponse)
async def update_vital_signs(
    vital_data: VitalSignsCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    vital = crud_vitals.create_vital_sign(db, vital_data)
    
    # Get ML prediction
    ml_prediction = None
    try:
        prediction_result = predict_emergency_status(
            user_id=vital_data.user_id,
            hr=vital_data.hr,
            spo2=vital_data.spo2,
            temp=vital_data.temp,
            stress=vital_data.stress
        )
        ml_prediction = MLPredictionResponse(**prediction_result)
        logger.info(f"ML prediction for user {vital_data.user_id}: {prediction_result}")
        
        # Store prediction in database if it's a valid prediction (has emergency_status)
        if prediction_result.get("emergency_status"):
            try:
                crud_vitals.store_ml_prediction(db, vital_data.user_id, prediction_result)
                logger.info(f"Stored ML prediction for user {vital_data.user_id}")
            except Exception as e:
                logger.error(f"Error storing ML prediction: {e}")
                # Continue even if storage fails
    except Exception as e:
        logger.error(f"Error getting ML prediction: {e}")
        # Continue without prediction if ML fails
    
    # Convert to response model
    vital_response = VitalSignsResponse.model_validate(vital)
    # Add ML prediction (not in database model)
    vital_response.ml_prediction = ml_prediction
    vital_dict = vital_response.model_dump(mode='json', exclude_none=True)
    
    # Log for debugging
    logger.info(f"Broadcasting vital sign update for patient {vital_data.user_id}")
    logger.info(f"Vital sign data: {vital_dict}")
    
    # Broadcast to all connected clients (legacy support)
    await manager.broadcast(vital_dict)
    
    # Broadcast to caregivers assigned to this patient
    await caregiver_manager.broadcast_to_patient_caregivers(
        patient_id=vital_data.user_id,
        message=vital_dict,
        db=db,
        connection_type="vitals"
    )
    
    return vital_response


# GET /vitals/latest/{user_id}
@router.get("/latest/{user_id}", response_model=VitalSignsResponse)
def get_latest(user_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    data = crud_vitals.get_latest_vital(db, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="No vital signs found for this user")
    return data

@router.get("/history/{user_id}", response_model=list[VitalSignsResponse])
def get_history(user_id: int, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    history = crud_vitals.get_vital_history(db, user_id)
    
    if not history:  # if the list is empty, assume user not found or no vitals
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return history

@router.get("/prediction/{user_id}", response_model=MLPredictionResponse)
def get_ml_prediction(
    user_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Get the latest stored ML prediction for a user.
    
    Returns the most recent prediction that was stored. If no prediction has been 
    stored yet, returns "waiting".
    """
    # Get latest stored prediction
    stored_prediction = crud_vitals.get_latest_ml_prediction(db, user_id)
    
    if not stored_prediction:
        # No prediction stored yet, return waiting
        return MLPredictionResponse(status="waiting")
    
    # Return the stored prediction
    return MLPredictionResponse(**stored_prediction)

@router.post("/batch", response_model=VitalSignsBatchResponse, status_code=201)
async def batch_upload_vital_signs(
    batch_data: VitalSignsBatchCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Upload multiple vital signs records in a single request.
    
    This endpoint is useful when the watch has been offline and needs to sync
    accumulated data. Each vital sign record can optionally include a timestamp
    for historical data.
    """
    result = crud_vitals.create_vital_signs_batch(db, batch_data)
    
    # Broadcast the latest vital sign if any were created
    if result["created_count"] > 0:
        # Get the latest vital sign for this user to broadcast
        latest = crud_vitals.get_latest_vital(db, batch_data.user_id)
        if latest:
            vital_dict = latest.model_dump(mode='json')
            logger.info(f"Broadcasting latest vital sign from batch upload for patient {batch_data.user_id}")
            
            # Broadcast to all connected clients (legacy support)
            await manager.broadcast(vital_dict)
            
            # Broadcast to caregivers assigned to this patient
            await caregiver_manager.broadcast_to_patient_caregivers(
                patient_id=batch_data.user_id,
                message=vital_dict,
                db=db,
                connection_type="vitals"
            )
    
    return VitalSignsBatchResponse(
        message=f"Successfully uploaded {result['created_count']} vital signs record(s)",
        created_count=result["created_count"],
        failed_count=result["failed_count"],
        failed_items=result.get("failed_items")
    )

# Vital websocket (legacy - broadcasts to all)
@router.websocket("/ws/vitals")
async def websocket_vitals(websocket: WebSocket):
    # Check API key from query params
    api_key = websocket.query_params.get(API_KEY_NAME)
    if not api_key:
        await websocket.close(code=1008, reason="API Key missing")
        return
    if api_key != API_KEY:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    # Accept connection
    await manager.connect(websocket)
    logger.info(f"WebSocket connected. Total connections: {len(manager.active_connections)}")
    
    # Send welcome message to confirm connection
    try:
        await websocket.send_json({"type": "connection", "message": "Connected to vital signs WebSocket"})
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

    try:
        while True:
            # Keep the connection alive - wait for messages from client
            data = await websocket.receive_text()
            logger.info(f"Received message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(manager.active_connections)}")

# Caregiver-specific vital signs WebSocket
@router.websocket("/ws/vitals/caregiver/{caregiver_id}")
async def websocket_vitals_caregiver(websocket: WebSocket, caregiver_id: int):
    """
    WebSocket endpoint for caregivers to receive vital signs updates for their assigned patients.
    
    Only receives updates for patients assigned to this caregiver.
    """
    from database import get_db
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
        logger.info(f"Caregiver {caregiver_id} connected for vital signs. Monitoring {len(patient_ids)} patient(s)")
        
        # Send welcome message with patient list
        await websocket.send_json({
            "type": "connection",
            "message": f"Connected to vital signs WebSocket for caregiver {caregiver_id}",
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
            logger.info(f"Caregiver {caregiver_id} disconnected from vital signs WebSocket")
    finally:
        db.close()