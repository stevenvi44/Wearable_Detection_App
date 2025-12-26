from passlib.context import CryptContext
from fastapi import BackgroundTasks, HTTPException, WebSocket, Security
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi.security.api_key import APIKeyHeader
from typing import List
import os
from dotenv import load_dotenv
from starlette.status import HTTP_403_FORBIDDEN

# Load environment variables
load_dotenv()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt (truncated to 72 bytes)."""
    truncated_pw = password[:72]  # truncate to 72 characters
    return pwd_context.hash(truncated_pw)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against its hashed version."""
    return pwd_context.verify(plain_password, hashed_password)

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

mail = FastMail(conf)

def send_email_background(background_tasks: BackgroundTasks, subject: str, email: str, body: str):
    """Sends an email asynchronously in the background."""
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html",
    )
    background_tasks.add_task(mail.send_message, message)

# API KEY
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = os.getenv("API_KEY_NAME", "X-API-KEY")  # fallback

if not API_KEY:
    raise Exception("API_KEY is not set in .env!")

# auto_error=False so we manually handle missing or invalid keys
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header_value: str = Security(api_key_header)):
    if not api_key_header_value:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="API Key missing"
        )
    if api_key_header_value != API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key_header_value

# WebSocket Manager - for location
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error broadcasting to connection: {e}")

# WebSocket Manager - for vital
class ConnectionManagerVital:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            import logging
            logging.getLogger(__name__).info("No active connections to broadcast to")
            return  # No connections to broadcast to
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error broadcasting to connection: {e}")
                # Mark for removal if send fails
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

# Enhanced WebSocket Manager - for caregiver-specific routing
class CaregiverConnectionManager:
    """
    Manages WebSocket connections for caregivers with patient-specific routing.
    Tracks which caregivers are connected and which patients they're monitoring.
    """
    def __init__(self):
        # Map: caregiver_id -> List[WebSocket]
        self.caregiver_connections: dict[int, List[WebSocket]] = {}
        # Map: websocket -> caregiver_id
        self.connection_to_caregiver: dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, caregiver_id: int):
        """Connect a caregiver WebSocket and track their ID"""
        await websocket.accept()
        
        if caregiver_id not in self.caregiver_connections:
            self.caregiver_connections[caregiver_id] = []
        
        self.caregiver_connections[caregiver_id].append(websocket)
        self.connection_to_caregiver[websocket] = caregiver_id
        
        import logging
        logging.getLogger(__name__).info(f"Caregiver {caregiver_id} connected. Total caregivers: {len(self.caregiver_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a caregiver WebSocket"""
        if websocket not in self.connection_to_caregiver:
            return
        
        caregiver_id = self.connection_to_caregiver[websocket]
        
        if caregiver_id in self.caregiver_connections:
            if websocket in self.caregiver_connections[caregiver_id]:
                self.caregiver_connections[caregiver_id].remove(websocket)
            
            # Remove empty caregiver entry
            if not self.caregiver_connections[caregiver_id]:
                del self.caregiver_connections[caregiver_id]
        
        del self.connection_to_caregiver[websocket]
        
        import logging
        logging.getLogger(__name__).info(f"Caregiver {caregiver_id} disconnected")

    async def broadcast_to_patient_caregivers(
        self, 
        patient_id: int, 
        message: dict, 
        db: Session,
        connection_type: str = "vitals"
    ):
        """
        Broadcast message to all caregivers assigned to a specific patient.
        
        Args:
            patient_id: The patient whose data is being updated
            message: The message to broadcast
            db: Database session to query caregiver-patient relationships
            connection_type: Type of connection ("vitals" or "location")
        """
        from models.models import PatientCaregiver
        
        # Find all caregivers assigned to this patient
        caregiver_assignments = db.query(PatientCaregiver).filter(
            PatientCaregiver.patient_id == patient_id
        ).all()
        
        if not caregiver_assignments:
            import logging
            logging.getLogger(__name__).debug(f"No caregivers assigned to patient {patient_id}")
            return
        
        caregiver_ids = [assignment.caregiver_id for assignment in caregiver_assignments]
        
        # Send message to all connected caregivers for this patient
        disconnected = []
        sent_count = 0
        
        for caregiver_id in caregiver_ids:
            if caregiver_id in self.caregiver_connections:
                for websocket in self.caregiver_connections[caregiver_id]:
                    try:
                        await websocket.send_json(message)
                        sent_count += 1
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(
                            f"Error sending {connection_type} to caregiver {caregiver_id}: {e}"
                        )
                        disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
        
        import logging
        logging.getLogger(__name__).info(
            f"Broadcasted {connection_type} for patient {patient_id} to {sent_count} caregiver connection(s)"
        )
