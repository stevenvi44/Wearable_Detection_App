from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from utils import ConnectionManagerVital, get_api_key
import crud.crud as crud_vitals
from schemas.schemas import VitalSignsCreate, VitalSignsResponse
from utils import API_KEY, API_KEY_NAME
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/vitals",
    tags=["Vital Signs"]
)

manager = ConnectionManagerVital()

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
    # Convert to response model and then to dict for broadcasting
    vital_response = VitalSignsResponse.model_validate(vital)
    vital_dict = vital_response.model_dump(mode='json')
    
    # Log for debugging
    logger.info(f"Broadcasting vital sign update to {len(manager.active_connections)} connections")
    logger.info(f"Vital sign data: {vital_dict}")
    
    # Broadcast new vital sign to all connected WebSocket clients
    await manager.broadcast(vital_dict)
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

# Vital websocket
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