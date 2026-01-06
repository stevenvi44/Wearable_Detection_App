import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fastapi import FastAPI
from routers import (
    users,
    auth,
    patient_location,
    vital_signs,
    connection,
    activity,
    medications,
    fall_detection
)

# Initialize FastAPI app
app = FastAPI(
    title="Wearable Fall detection APIs ",
    description="A complete FastAPI backend with multiple routers.",
    version="1.0.0"
)


app.include_router(auth.router)
app.include_router(patient_location.router)
app.include_router(vital_signs.router)
app.include_router(connection.router)
app.include_router(activity.router)
app.include_router(medications.router)
app.include_router(fall_detection.router)
app.include_router(users.router)

@app.get("/")
def read_root():
    return {"message": "Wearable App APIs"}
