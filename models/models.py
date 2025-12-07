# app/models/models.py OR split into user.py and role.py
from sqlalchemy import CheckConstraint, PrimaryKeyConstraint, Column, Integer, String, Table, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(60), nullable=False, unique=True)
    name = Column(String(60), nullable=False)
    email = Column(String(60), nullable=False, unique=True)
    password = Column(String(60), nullable=False)
    phone_number = Column(String(20), nullable=False)
    location = Column(String(200), nullable=True)
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
