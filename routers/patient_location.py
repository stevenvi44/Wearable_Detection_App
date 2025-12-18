from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import text
from database import engine
from schemas.schemas import PatientLocationUpdate, PatientLocationResponse
from utils import ConnectionManager, get_api_key
from utils import API_KEY, API_KEY_NAME


router = APIRouter(prefix="/patient/location", tags=["Patient Location"])
manager = ConnectionManager()


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

    # Broadcast new location to all connected WebSocket clients
    await manager.broadcast({
        "patient_id": loc.patient_id,
        "latitude": loc.latitude,
        "longitude": loc.longitude
    })

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

# WebSocket Endpoint
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
