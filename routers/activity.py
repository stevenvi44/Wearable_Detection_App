from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta

from database import get_db
from models.models import WeeklyReport, Dashboard, WeeklySteps, SleepLog, User
from schemas.schemas import *
from utils import get_api_key


def day_name_to_date(day_name: str) -> date:
    """Convert day name (Mon, Tue, etc.) to the most recent occurrence of that day"""
    day_mapping = {
        "Mon": 0,
        "Tue": 1,
        "Wed": 2,
        "Thu": 3,
        "Fri": 4,
        "Sat": 5,
        "Sun": 6,
    }

    target_weekday = day_mapping.get(day_name)
    if target_weekday is None:
        raise ValueError(
            f"Invalid day name: {day_name}. Must be one of: Mon, Tue, Wed, Thu, Fri, Sat, Sun"
        )

    today = date.today()
    current_weekday = today.weekday()  # Monday is 0, Sunday is 6

    # Calculate days to subtract to get to the target day
    days_diff = (current_weekday - target_weekday) % 7
    if days_diff == 0:
        # If today is the target day, return today
        return today
    else:
        # Return the most recent occurrence of the target day
        return today - timedelta(days=days_diff)


router = APIRouter(prefix="/api/activity", tags=["Activity"])

@router.post("/weekly-report", status_code=status.HTTP_201_CREATED)
def upsert_weekly_report(
    payload: WeeklyReportCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Create or update weekly activity report"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {payload.user_id} not found"
        )
    
    record = db.query(WeeklyReport).filter(
        WeeklyReport.user_id == payload.user_id,
        WeeklyReport.activity_date == payload.activity_date
    ).first()

    if record:
        record.average_steps = payload.average_steps
        record.most_active_day = payload.most_active_day
        record.total_distance_km = payload.total_distance_km
        record.calories_burned = payload.calories_burned
    else:
        record = WeeklyReport(
            user_id=payload.user_id,
            activity_date=payload.activity_date,
            average_steps=payload.average_steps,
            most_active_day=payload.most_active_day,
            total_distance_km=payload.total_distance_km,
            calories_burned=payload.calories_burned
        )
        db.add(record)

    try:
        db.commit()
        db.refresh(record)
        return {"message": "Weekly report saved", "id": record.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save weekly report: {str(e)}"
        )

@router.post("/sleep", status_code=status.HTTP_201_CREATED)
def upsert_sleep(
    payload: SleepCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Create or update sleep log"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {payload.user_id} not found"
        )
    
    # Use sleep_day text directly for storage/query (e.g., 'Mon', 'Fri')
    record = (
        db.query(SleepLog)
        .filter(
            SleepLog.user_id == payload.user_id,
            SleepLog.sleep_day == payload.sleep_day,
        )
        .first()
    )

    if record:
        record.sleep_hours = payload.sleep_hours
        record.deep_sleep_hours = payload.deep_sleep_hours
        record.light_sleep_hours = payload.light_sleep_hours
        record.rem_sleep_hours = payload.rem_sleep_hours
        record.awake_minutes = payload.awake_minutes
    else:
        record = SleepLog(
            user_id=payload.user_id,
            sleep_day=payload.sleep_day,
            sleep_hours=payload.sleep_hours,
            deep_sleep_hours=payload.deep_sleep_hours,
            light_sleep_hours=payload.light_sleep_hours,
            rem_sleep_hours=payload.rem_sleep_hours,
            awake_minutes=payload.awake_minutes,
        )
        db.add(record)

    try:
        db.commit()
        db.refresh(record)
        return {"message": "Sleep data saved", "id": record.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save sleep data: {str(e)}"
        )


@router.get("/weekly-steps", response_model=WeeklyStepsResponse)
def get_weekly_steps(
    user_id: int,
    date: date,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Get weekly steps breakdown by day for a specific date"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Get all weekly_steps records for the user
    weekly_steps_records = db.query(WeeklySteps).filter(
        WeeklySteps.user_id == user_id
    ).all()
    
    # Map day names (database uses lowercase, response uses capitalized)
    day_mapping = {
        "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
        "fri": "Fri", "sat": "Sat", "sun": "Sun"
    }
    
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    steps_map = {d: 0 for d in days}
    
    # Populate steps map from weekly_steps records
    for record in weekly_steps_records:
        day_capitalized = day_mapping.get(record.week.lower(), record.week.capitalize())
        if day_capitalized in steps_map:
            steps_map[day_capitalized] = record.steps

    # Calculate ISO week from the provided date for the response
    iso_year, iso_week, _ = date.isocalendar()

    return {
        "week": f"{iso_year}-W{iso_week:02d}",
        "steps": [{"day": k, "steps": v} for k, v in steps_map.items()]
    }

@router.post("/weekly-steps", status_code=status.HTTP_201_CREATED)
def post_weekly_steps(
    payload: WeeklyStepsCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Create or update weekly steps for a specific day"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {payload.user_id} not found"
        )
    
    # Validate and normalize day name
    valid_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_lower = payload.week.lower()
    
    if day_lower not in valid_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day: {payload.week}. Must be one of: {', '.join(valid_days)}"
        )
    
    # Normalize day name to lowercase
    normalized_day = day_lower
    
    # Check if record exists
    weekly_step = db.query(WeeklySteps).filter(
        WeeklySteps.user_id == payload.user_id,
        WeeklySteps.week == normalized_day
    ).first()
    
    if weekly_step:
        # Update existing record
        weekly_step.steps = payload.steps
    else:
        # Create new record
        weekly_step = WeeklySteps(
            user_id=payload.user_id,
            week=normalized_day,
            steps=payload.steps
        )
        db.add(weekly_step)
    
    try:
        db.commit()
        db.refresh(weekly_step)
        
        return {
            "message": "Weekly steps saved successfully",
            "user_id": payload.user_id,
            "week": payload.week,
            "steps": payload.steps
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save weekly steps: {str(e)}"
        )

@router.get("/weekly-report", response_model=WeeklyReportResponse)
def weekly_report(
    user_id: int,
    activity_date: date,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Get weekly activity report"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Query weekly_report table using user_id and activity_date
    report = db.query(WeeklyReport).filter(
        WeeklyReport.user_id == user_id,
        WeeklyReport.activity_date == activity_date
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Weekly report not found for user {user_id} on {activity_date}"
        )

    # Calculate ISO week from activity_date for the response
    iso_year, iso_week, _ = activity_date.isocalendar()

    return {
        "week": f"{iso_year}-W{iso_week:02d}",
        "average_steps": report.average_steps or 0,
        "total_distance_km": report.total_distance_km or 0.0,
        "most_active_day": report.most_active_day or "N/A",
        "calories_burned": report.calories_burned or 0
    }

@router.get("/sleep", response_model=SleepResponse)
def get_sleep(
    user_id: int,
    sleep_day: str = Query(
        ..., description="Day name: Mon, Tue, Wed, Thu, Fri, Sat, Sun"
    ),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Get sleep data for a specific weekday (Mon, Tue, ..., Sun)"""
    # Validate day name
    valid_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if sleep_day not in valid_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sleep_day must be one of: {', '.join(valid_days)}. Got: '{sleep_day}'",
        )

    # Validate user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    sleep = (
        db.query(SleepLog)
        .filter(
            SleepLog.user_id == user_id,
            SleepLog.sleep_day == sleep_day,
        )
        .first()
    )

    if not sleep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sleep data found for user {user_id} on {sleep_day}",
        )

    return {
        "user_id": sleep.user_id,
        # sleep_day is stored as plain text (e.g., 'Mon'), return it directly
        "sleep_date": sleep.sleep_day,
        "sleep_hours": sleep.sleep_hours,
        "deep_sleep_hours": sleep.deep_sleep_hours,
        "light_sleep_hours": sleep.light_sleep_hours,
        "rem_sleep_hours": sleep.rem_sleep_hours,
        "awake_minutes": sleep.awake_minutes,
    }

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    user_id: int,
    date: date,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Get dashboard summary for a specific date"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Query dashboard table
    dashboard = db.query(Dashboard).filter(
        Dashboard.user_id == user_id,
        Dashboard.date == date
    ).first()

    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No dashboard data found for user {user_id} on {date}"
        )

    return {
        "date": dashboard.date.isoformat(),
        "daily_steps": dashboard.daily_steps,
        "active_minutes": dashboard.active_minutes,
        "rest_hours": dashboard.rest_hours,
        "mobility_level": dashboard.mobility_level
    }

@router.post("/summary", response_model=DashboardSummaryResponse, status_code=status.HTTP_201_CREATED)
def post_dashboard_summary(
    payload: DashboardSummaryCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Create or update dashboard summary for a specific date"""
    # Validate user exists
    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {payload.user_id} not found"
        )
    
    # Validate mobility_level
    valid_mobility_levels = ["Low", "Moderate", "High"]
    if payload.mobility_level not in valid_mobility_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"mobility_level must be one of: {', '.join(valid_mobility_levels)}"
        )
    
    # Upsert dashboard record
    dashboard = db.query(Dashboard).filter(
        Dashboard.user_id == payload.user_id,
        Dashboard.date == payload.date
    ).first()

    if dashboard:
        # Update existing record
        dashboard.daily_steps = payload.daily_steps
        dashboard.active_minutes = payload.active_minutes
        dashboard.rest_hours = payload.rest_hours
        dashboard.mobility_level = payload.mobility_level
    else:
        # Create new record
        dashboard = Dashboard(
            user_id=payload.user_id,
            date=payload.date,
            daily_steps=payload.daily_steps,
            active_minutes=payload.active_minutes,
            rest_hours=payload.rest_hours,
            mobility_level=payload.mobility_level
        )
        db.add(dashboard)

    try:
        db.commit()
        db.refresh(dashboard)
        
        return {
            "date": dashboard.date.isoformat(),
            "daily_steps": dashboard.daily_steps,
            "active_minutes": dashboard.active_minutes,
            "rest_hours": dashboard.rest_hours,
            "mobility_level": dashboard.mobility_level
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save dashboard summary: {str(e)}"
        )