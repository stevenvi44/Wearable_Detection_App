from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    Time,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(60), nullable=False, unique=True)
    name = Column(String(60), nullable=False)
    email = Column(String(60), nullable=False, unique=True)
    password = Column(String(60), nullable=False)
    phone_number = Column(String(20), nullable=False)
    location = Column(String(200), nullable=True)
    age = Column(Integer, nullable=True)
    pain_type = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            r"user_name ~ '^[a-z0-9.]+$'",
            name="valid_username"
        ),
    )

    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    caregivers = relationship(
        "User",
        secondary="patient_caregivers",
        primaryjoin="User.user_id==PatientCaregiver.patient_id",
        secondaryjoin="User.user_id==PatientCaregiver.caregiver_id",
        backref="patients"
    )
    vital_signs = relationship("VitalSigns", back_populates="user")


# Roles table
class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Relationship to users (many-to-many)
    users = relationship("User", secondary="user_roles", back_populates="roles")

# Junction table for user_roles (many-to-many)
class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)

# Junction table for patient_caregivers (many-to-many)
class PatientCaregiver(Base):
    __tablename__ = "patient_caregivers"

    patient_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    caregiver_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))

    __table_args__ = (
        PrimaryKeyConstraint("patient_id", "caregiver_id"),
    )

# Patient Location
class PatientLocation(Base):
    __tablename__ = "patient_locations"

    id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Double, nullable=False)
    longitude = Column(Double, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

class PatientLastLocation(Base):
    __tablename__ = "patient_last_location"

    patient_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    latitude = Column(Double, nullable=False)
    longitude = Column(Double, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class VitalSigns(Base):
    __tablename__ = "vital_signs"

    vital_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    heart_rate = Column(Integer, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    spo2 = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    breathing_rate = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationship back to User
    user = relationship("User", back_populates="vital_signs")

class DeviceConnection(Base):
    __tablename__ = "device_connections"

    device_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    device_identifier = Column(String, nullable=True, unique=True)  # MAC address or serial number
    device_name = Column(String, nullable=True)  # e.g., "Apple Watch Series 9"
    device_type = Column(String, nullable=True)  # e.g., "smartwatch"
    status = Column(String, nullable=False)
    battery = Column(Integer)
    ip_address = Column(String)
    last_seen = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class WeeklyReport(Base):
    __tablename__ = "weekly_report"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))

    activity_date = Column(Date, nullable=False)

    average_steps = Column(Integer)
    total_distance_km = Column(Float)
    calories_burned = Column(Integer)
    most_active_day = Column(String(20))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Dashboard(Base):
    __tablename__ = "dashboard"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))

    date = Column(Date, nullable=False)
    daily_steps = Column(Integer, default=0)
    active_minutes = Column(Integer, default=0)
    rest_hours = Column(Float, default=0.0)
    mobility_level = Column(String(20), nullable=False)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class WeeklySteps(Base):
    __tablename__ = "weekly_steps"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    week = Column(String(10), nullable=False)
    steps = Column(Integer, default=0, nullable=False)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("id"),
    )


class SleepLog(Base):
    __tablename__ = "sleep_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))

    # Database column is named 'sleep_day' and stores weekday text (e.g., 'Mon')
    sleep_day = Column("sleep_day", String(10), nullable=False)
    sleep_hours = Column(Float)
    deep_sleep_hours = Column(Float)
    light_sleep_hours = Column(Float)
    rem_sleep_hours = Column(Float)
    awake_minutes = Column(Integer)
    sleep_quality = Column(String(20))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class Medication(Base):
    __tablename__ = "medications"

    medication_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    name = Column(String)
    dosage = Column(String)
    frequency = Column(String)

    # Relationship to MedicationDose
    doses = relationship("MedicationDose", back_populates="medication")

class MedicationDose(Base):
    __tablename__ = "medication_doses"

    dose_id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(
        Integer,
        ForeignKey("medications.medication_id"),
        nullable=False
    )

    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time, nullable=False)

    status = Column(String(20), default="pending")
    action_time = Column(DateTime)

    medication = relationship(
        "Medication",
        back_populates="doses"
    )

