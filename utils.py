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
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

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
