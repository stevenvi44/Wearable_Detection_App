from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from utils import get_api_key
import crud.crud as crud_fall
from schemas.schemas import (
    FallDetectionCreate,
    FallDetectionResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/test/fall-detection",
    tags=["Fall Detection"]
)

# -----------------------
# POST /test/fall-detection
# -----------------------
@router.post("", response_model=FallDetectionResponse, status_code=201)
def create_fall_detection(
    fall_data: FallDetectionCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Create a new fall detection alert for testing.
    
    Accepts user_id and alert_type (string) to create a fall detection record.
    """
    try:
        fall_detection = crud_fall.create_fall_detection(db, fall_data)
        logger.info(f"Fall detection alert created for user {fall_data.user_id}: {fall_data.alert_type}")
        return FallDetectionResponse.model_validate(fall_detection)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fall detection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating fall detection: {str(e)}"
        )

# -----------------------
# GET /test/fall-detection/{user_id}
# -----------------------
@router.get("/{user_id}", response_model=FallDetectionResponse)
def get_fall_detection(
    user_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Get the latest fall detection alert for a user.
    
    Returns the most recent fall detection record for the specified user_id.
    """
    fall_detection = crud_fall.get_fall_detection(db, user_id)
    
    if not fall_detection:
        raise HTTPException(
            status_code=404,
            detail=f"No fall detection alerts found for user {user_id}"
        )
    
    return fall_detection

