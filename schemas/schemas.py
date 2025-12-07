from pydantic import BaseModel, EmailStr, StringConstraints, HttpUrl, Field, model_validator, field_validator # BaseModel for defining schemas
from typing import Optional, Annotated, List # Optional allows fields to be nullable.
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
import re


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

class UserCreate(BaseModel):
    name: str = Field(example="Alice Smith")
    user_name: str = Field(example="alice.smith01")
    email: EmailStr = Field(example="alice@example.com")
    phone_number: str = Field(example="01234567890")
    location: str = Field(example="Cairo, Egypt")
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
