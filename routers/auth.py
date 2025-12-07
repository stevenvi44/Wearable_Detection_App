import os
import random
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from schemas.schemas import UserCreate, UserUpdate, UserResponse
from database import get_db
from models.models import User, Role, UserRole
from crud.crud import link_patient_and_caregiver
from schemas.schemas import (
    UserCreate,
    VerifyCode,
    ForgotPasswordRequest,
    UserResponse,
    LoginSchema,
    ResetPasswordSchema,
    PatientCaregiverCreate
)

from dotenv import load_dotenv

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Environment Variables
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "test_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Email Configuration
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
router = APIRouter(prefix="/auth", tags=["Authentication"])


# TOKEN CREATION
def create_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user: User):
    return create_token(
        {"sub": user.email},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

def create_refresh_token(user: User):
    return create_token(
        {"sub": user.email},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )


# PASSWORD UTILS
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


# SEND EMAIL
async def send_email_background(background_tasks: BackgroundTasks, subject: str, email: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html"
    )
    background_tasks.add_task(mail.send_message, message)


# CURRENT USER
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")


# REGISTER USER
@router.post("/register")
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check email unique
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(400, "Email already exists")

    verification_code = str(random.randint(100000, 999999))

    # Check if username already exists
    existing_user = db.query(User).filter(User.user_name == user_data.user_name).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user_data.name,
        user_name=user_data.user_name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        location=user_data.location,
        password=hash_password(user_data.password),
        is_active=False,
        verification_code=verification_code
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Assign roles (many-to-many)
    if user_data.role_ids:
        for rid in user_data.role_ids:
            if db.query(Role).filter(Role.role_id == rid).first():
                db.add(UserRole(user_id=new_user.user_id, role_id=rid))
        db.commit()

    # Send verification email
    email_body = f"<h3>Your verification code is: <b>{verification_code}</b></h3>"
    await send_email_background(
        background_tasks, "Verify Email", new_user.email, email_body
    )

    return {"message": "User registered. Please verify your email."}


# VERIFY EMAIL
@router.post("/verify-email")
def verify_email(data: VerifyCode, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email == data.email,
        User.verification_code == data.code
    ).first()

    if not user:
        raise HTTPException(400, "Invalid code")

    user.verification_code = None
    user.is_active = True
    db.commit()

    return {"message": "Email verified successfully"}


# LOGIN
@router.post("/login")
def login_user(
    credentials: LoginSchema,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.email == credentials.username) | (User.user_name == credentials.username)
    ).first()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(credentials.password, user.password):
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Verify your email first")

    access = create_access_token(user)
    refresh = create_refresh_token(user)

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user_id": user.user_id,
        "user_name": user.user_name
    }



# REFRESH TOKEN
@router.post("/refresh")
def refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        return {
            "access_token": create_token(
                {"sub": email},
                timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
        }

    except JWTError:
        raise HTTPException(400, "Invalid refresh token")


# FORGOT PASSWORD
@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(404, "User not found")

    reset_code = str(random.randint(100000, 999999))
    user.verification_code = reset_code
    db.commit()

    email_body = f"<h3>Your password reset code is: <b>{reset_code}</b></h3>"
    await send_email_background(
        background_tasks, "Reset Password", user.email, email_body
    )

    return {"message": "Reset code sent to your email"}


# RESET PASSWORD
@router.post("/reset-password")
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email == payload.email,
        User.verification_code == payload.code
    ).first()

    if not user:
        raise HTTPException(400, "Invalid reset code")

    user.password = hash_password(payload.new_password)
    user.verification_code = None
    db.commit()

    return {"message": "Password reset successfully"}


# ADMIN PROTECTION
def get_admin_user(user: User = Depends(get_current_user)):
    # you have many-to-many roles: check if user has "admin" role
    role_names = [role.role_name for role in user.roles]
    
    if "admin" not in role_names:
        raise HTTPException(403, "Admin access required")

    return user

@router.post("/connect")
def connect_patient_and_caregiver(
    data: PatientCaregiverCreate,
    db: Session = Depends(get_db)
):
    link_patient_and_caregiver(db, data.patient_id, data.caregiver_id)
    return {"message": "Caregiver linked to patient successfully"}