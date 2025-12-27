from typing import Optional, Annotated, List 
from datetime import datetime, date
import re
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)


class UserBase(BaseModel):
    name: str  
    user_name: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=60,
            pattern=r"^[a-z0-9.]+$"   # lowercase letters, digits, dots only
        )
    ]
    email: EmailStr
    phone_number: Annotated[
        str,
        StringConstraints(
            pattern=r"^(010|011|012|015)[0-9]{8}$",
            min_length=11,
            max_length=11
        )
    ]
    location: str
    age: Optional[int] = None
    pain_type: Optional[str] = None

class UserCreate(BaseModel):
    name: str = Field(example="Alice Smith")
    user_name: str = Field(example="alice.smith01")
    email: EmailStr = Field(example="alice@example.com")
    phone_number: str = Field(example="01234567890")
    location: str = Field(example="Cairo, Egypt")
    age: Optional[int] = Field(default=None, example=68)
    pain_type: Optional[str] = Field(default=None, example="Chronic back pain")
    password: Annotated[
        str,
        StringConstraints(min_length=8, max_length=72)
    ] = Field(example="StrongPass1!")
    role_ids: Optional[List[int]] = Field(default=[], example=[1])

    @field_validator("phone_number")
    def validate_phone_number(cls, v: str) -> str:
            import re
            pattern = r"^(010|011|012|015)[0-9]{8}$"
            if not re.fullmatch(pattern, v):
                raise ValueError("Invalid phone number. Must start with 010, 011, 012, or 015 and have 11 digits.")
            return v    

    # Validate role_ids
    @field_validator("role_ids")
    def validate_role_ids(cls, v: List[int]) -> List[int]:
        for item in v:
            if item not in (1, 2):
                raise ValueError("role_ids must be 1 (patient) or 2 (caregiver)")
        return v

    # Strong password validation
    @field_validator("password")
    def validate_strong_password(cls, value: str) -> str:
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[@#$%^&+=!]", value):
            raise ValueError(
                "Password must contain at least one special character (@#$%^&+=!)."
            )
        return value

class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, example="Alice Smith")
    user_name: Optional[str] = Field(default=None, example="alice.smith01")
    email: Optional[EmailStr] = Field(default=None, example="alice@example.com")
    phone_number: Optional[
        Annotated[
            str,
            StringConstraints(
                pattern=r"^(010|011|012|015)[0-9]{8}$",
                min_length=11,
                max_length=11
            )
        ]
    ] = Field(default=None, example="01234567890")
    location: Optional[str] = Field(default=None, example="Cairo, Egypt")
    age: Optional[int] = Field(default=None, example=68)
    pain_type: Optional[str] = Field(default=None, example="Chronic back pain")
    role_ids: Optional[List[int]] = Field(default=None, example=[2])
    password: Optional[Annotated[str, StringConstraints(min_length=8, max_length=72)]] = Field(default=None, example="NewStrongPass1!")
    reset_token: Optional[str] = Field(default=None, example="abc123resettoken")

    # Validate role_ids
    @field_validator("role_ids")
    def validate_role_ids(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            for item in v:
                if item not in (1, 2):
                    raise ValueError("role_ids must be 1 (patient) or 2 (caregiver)")
        return v

    # Strong password validation
    @field_validator("password")
    def validate_strong_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[@#$%^&+=!]", value):
            raise ValueError(
                "Password must contain at least one special character (@#$%^&+=!)."
            )
        return value

class ResetPasswordSchema(BaseModel):
    email: str
    code: str
    new_password: str

    # Strong password validation
    @field_validator("new_password")
    def validate_strong_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[@#$%^&+=!]", value):
            raise ValueError(
                "Password must contain at least one special character (@#$%^&+=!)."
            )
        return value

class RoleMiniResponse(BaseModel):
    role_id: int
    role_name: str

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    user_id: int
    reset_token: Optional[str] = None
    roles: Optional[List[RoleMiniResponse]] = []
    is_active: bool

    class Config:
        from_attributes = True

# Role Schema
class RoleBase(BaseModel):
    role_name: str = Field(..., max_length=50)
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None

class UserMiniResponse(BaseModel):
    user_id: int
    username: str

    class Config:
        from_attributes = True

class RoleResponse(RoleBase):
    role_id: int
    users: Optional[List[UserMiniResponse]] = []

    class Config:
        from_attributes = True

# Assign a role to a user schema
class UserRoleBase(BaseModel):
    user_id: int
    role_id: int

class UserRoleCreate(UserRoleBase):
    pass

class UserRoleResponse(UserRoleBase):
    class Config:
        from_attributes = True

# Assign a caregiver to a patient schema
class PatientCaregiverBase(BaseModel):
    patient_id: int
    caregiver_id: int


class PatientCaregiverCreate(BaseModel):
    patient_id: int
    caregiver_id: int


class PatientCaregiverResponse(PatientCaregiverBase):
    class Config:
        from_attributes = True


class VerifyCode(BaseModel):
    email: EmailStr
    code: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class LoginSchema(BaseModel):
    username: str
    password: str


class PatientLocationUpdate(BaseModel):
    patient_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class PatientLocationResponse(BaseModel):
    patient_id: int
    latitude: float
    longitude: float
    updated_at: str

class PatientListItem(BaseModel):
    patient_id: int
    patient_name: str
    patient_email: str
    patient_phone: str
    age: Optional[int] = None
    
    model_config = {
        "from_attributes": True
    }

class CaregiverPatientsResponse(BaseModel):
    caregiver_id: int
    patients: List[PatientListItem]

class PatientDashboardResponse(BaseModel):
    patient_id: int
    patient_name: str
    # Vitals
    latest_vitals: Optional[VitalSignsResponse] = None
    # Device Connection
    device_status: Optional[DeviceStatusResponse] = None
    # Location
    location: Optional[PatientLocationResponse] = None

# Vital Schema
class VitalSignsBase(BaseModel):
    hr: Optional[int] = None
    spo2: Optional[int] = None
    temp: Optional[float] = None
    stress: Optional[str] = None

class VitalSignsCreate(VitalSignsBase):
    user_id: int

class MLPredictionResponse(BaseModel):
    emergency_status: Optional[str] = None  # "safe_now", "warning_soon", "critical"
    confidence: Optional[float] = None
    status: Optional[str] = None  # "waiting_for_more_data", "insufficient_data", "error"
    message: Optional[str] = None

class VitalSignsResponse(BaseModel):
    vital_id: int
    user_id: int
    hr: int | None = None
    spo2: int | None = None
    temp: float | None = None
    stress: str | None = None
    created_at: datetime
    ml_prediction: Optional[MLPredictionResponse] = None  # ML prediction if available

    model_config = {
        "from_attributes": True
    }

class DeviceStatusUpdate(BaseModel):
    user_id: int
    status: str
    battery: int

    # Validate battery (%)
    @field_validator("battery")
    def validate_battery(cls, v):
        if v < 0 or v > 100:
            raise ValueError("battery must be between 0 and 100")
        return v

    # Validate status value
    @field_validator("status")
    def validate_status(cls, v):
        allowed = {"online", "offline", "disconnected"}
        if v.lower() not in allowed:
            raise ValueError(f"status must be one of: {allowed}")
        return v.lower()


class DeviceStatusResponse(BaseModel):
    status: str
    battery: int

    model_config = {
        "from_attributes": True
    }

class DeviceRegisterCreate(BaseModel):
    user_id: int
    device_identifier: str = Field(..., description="Unique device identifier (MAC address or serial number)")
    device_name: Optional[str] = Field(None, description="Device name, e.g., 'Apple Watch Series 9'")
    device_type: Optional[str] = Field(None, description="Device type, e.g., 'smartwatch'")

class DeviceRegisterResponse(BaseModel):
    device_id: int
    user_id: int
    device_identifier: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    status: str
    battery: Optional[int] = None
    paired_at: datetime

    model_config = {
        "from_attributes": True
    }

class VitalSignsBatchItem(BaseModel):
    hr: Optional[int] = None
    spo2: Optional[int] = None
    temp: Optional[float] = None
    stress: Optional[str] = None
    created_at: Optional[datetime] = None  # Optional timestamp for historical data

class VitalSignsBatchCreate(BaseModel):
    user_id: int
    vitals: List[VitalSignsBatchItem] = Field(..., min_length=1, description="List of vital signs to upload")

class VitalSignsBatchResponse(BaseModel):
    message: str
    created_count: int
    failed_count: int
    failed_items: Optional[List[dict]] = None

class CaregiverContactResponse(BaseModel):
    caregiver_id: int
    caregiver_name: str
    phone_number: str

    model_config = {
        "from_attributes": True
    }

class DashboardSummaryResponse(BaseModel):
    date: str
    daily_steps: int
    active_minutes: int
    rest_hours: float
    mobility_level: str

class DashboardSummaryCreate(BaseModel):
    user_id: int
    date: date
    daily_steps: int
    active_minutes: int
    rest_hours: float
    mobility_level: str

class WeeklyStepsItem(BaseModel):
    day: str
    steps: int

class WeeklyStepsResponse(BaseModel):
    week: str
    steps: List[WeeklyStepsItem]

class WeeklyStepsCreate(BaseModel):
    user_id: int
    week: str  # day name: mon, tue, wed, thu, fri, sat, sun
    steps: int

class WeeklyReportResponse(BaseModel):
    week: str
    average_steps: int
    total_distance_km: float
    most_active_day: str
    calories_burned: int

class SleepResponse(BaseModel):
    user_id: int
    sleep_date: str
    sleep_hours: float | None
    deep_sleep_hours: float | None
    light_sleep_hours: float | None
    rem_sleep_hours: float | None
    awake_minutes: int | None

class ActivityDailyCreate(BaseModel):
    user_id: int
    activity_date: date
    average_steps: int
    most_active_day: str
    total_distance_km: float
    calories_burned: int

class WeeklyReportCreate(BaseModel):
    user_id: int
    activity_date: date
    average_steps: int
    most_active_day: str
    total_distance_km: float
    calories_burned: int


class SleepCreate(BaseModel):
    user_id: int
    sleep_day: str  # Accepts day name: Mon, Tue, Wed, Thu, Fri, Sat, Sun
    sleep_hours: float
    deep_sleep_hours: float
    light_sleep_hours: float
    rem_sleep_hours: float
    awake_minutes: int

    @field_validator("sleep_day")
    def validate_sleep_day(cls, v: str) -> str:
        valid_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if v not in valid_days:
            raise ValueError(
                f"sleep_day must be one of: {', '.join(valid_days)}. Got: '{v}'"
            )
        return v

class TodayMedicationItem(BaseModel):
    dose_id: int
    medication_id: int
    name: str
    dosage: str
    frequency: str
    scheduled_time: str
    status: Optional[str] = None

    class Config:
        from_attributes = True

class TodayMedicationResponse(BaseModel):
    date: str
    items: List[TodayMedicationItem]

class TakeMedicationResponse(BaseModel):
    message: str
    taken_at: str

class SkipMedicationRequest(BaseModel):
    reason: str

class SkipMedicationResponse(BaseModel):
    message: str

class TodayMedicationRequest(BaseModel):
    user_id: int
    items: List[TodayMedicationItem]

class MedicationCreate(BaseModel):
    user_id: int
    name: str
    dosage: str
    frequency: str

class MedicationResponse(BaseModel):
    medication_id: int
    user_id: int
    name: str
    dosage: str
    frequency: str

    class Config:
        from_attributes = True
