## Wearable Backend API

FastAPI backend for a wearable health monitoring app. It handles authentication, medications, activity and sleep, vitals, device connection status, and caregiver–patient features.

---

## Tech Stack

- **Language**: Python 3.11+  
- **Framework**: FastAPI  
- **Database**: PostgreSQL (SQLAlchemy ORM)  
- **Migrations**: Alembic  
- **Auth**: JWT-based authentication  

---

## Getting Started

### 1. Create virtual environment

python -m venv venv
venv\Scripts\activate  # On Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file (or use environment variables) with at least:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/wearable_db
SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
EMAIL_HOST=...
EMAIL_PORT=...
EMAIL_USER=...
EMAIL_PASSWORD=...
API_KEY=your_internal_api_key
```

Match these with the values used in `database.py`, auth utilities, and any email utilities.

### 4. Run database migrations

```bash
alembic upgrade head
```

This creates or updates all tables (users, roles, medications, medication_doses, sleep_logs, device_connections, etc.).

### 5. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000` and interactive docs at:

- `http://127.0.0.1:8000/docs` (Swagger UI)
- `http://127.0.0.1:8000/redoc`

---

## Main Modules & Endpoints (What Each Endpoint Does)

### Auth (`routers/auth.py`)

- **POST** `/auth/register`  
  - Create a new user account (patient or caregiver) with email, password, `age`, and optional `pain_type`.  
- **POST** `/auth/login`  
  - Authenticate a user and return a JWT access token used to call protected APIs.  
- **POST** `/auth/verify-email`  
  - Confirm a user’s email using a 6‑digit code sent by email.  
- **Forgot/reset password endpoints**  
  - Start password reset with email + code, then set a new password.

### Users (`routers/users.py`)

- **POST** `/users/`  
  - Admin/internal endpoint to create a user directly (bypassing email verification).  
- **GET** `/users/`  
  - List users with basic profile information.  
- **GET** `/users/{user_id}`  
  - Get full details for a specific user.  
- **PUT** `/users/{user_id}`  
  - Update user fields such as name, email, phone, `age`, `pain_type`, and roles.  
- **DELETE** `/users/{user_id}`  
  - Permanently delete a user.

### Medications (`routers/medications.py`)

- **POST** `/api/medications`  
  - Define a medication for a user (name, dosage, frequency) without specific times.  
- **GET** `/api/medications/today`  
  - Return all medication doses scheduled **for today** for a given `user_id`, including status (`pending`, `taken`, etc.).  
- **POST** `/api/medications/today`  
  - Create or update **today’s doses** for one or more medications.  
  - Each item can send `scheduled_time` as one time (`"08:00"`) or several times in one string (`"08:00, 20:00"`).  
  - The backend creates one dose per time and returns them grouped per medication with a combined `"08:00, 20:00"` string.  
- **POST** `/api/medications/{dose_id}/take`  
  - Mark a single dose as **taken** and store the timestamp.  
- **POST** `/api/medications/{dose_id}/skip`  
  - Mark a single dose as **skipped**, with a text reason.

### Activity & Sleep (`routers/activity.py`)

- **POST** `/api/activity/weekly-report`  
  - Upsert aggregated weekly activity data (steps, distance, calories, most active day).  
- **GET** `/api/activity/weekly-report`  
  - Read the weekly report for a user and week.  
- **POST** `/api/activity/sleep`  
  - Upsert a sleep log for a specific **weekday** for a user.  
  - Request uses `sleep_day` with short weekday names (`Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`) plus sleep metrics.  
- **GET** `/api/activity/sleep`  
  - Fetch the sleep log for a user and given `sleep_day` (e.g. `"Wed"`).  
- **GET** `/api/activity/weekly-steps`  
  - Get steps per day for a given week (for charts).  
- **GET** `/api/activity/summary`  
  - Return a dashboard‑style summary (steps, active minutes, rest hours, mobility level) for a single date.  
- **POST** `/api/activity/summary`  
  - Upsert dashboard summary metrics for a day.

### Vital Signs (`routers/vital_signs.py`)

- **POST** `/vital-signs`  
  - Store the latest vital signs from the wearable: heart rate, blood pressure, SpO2, temperature, etc.  
- **GET** `/vital-signs/latest/{user_id}`  
  - Get the most recent vital signs snapshot for a user.  
- **GET** `/vital-signs/history/{user_id}`  
  - Get recent historical vital measurements, ordered by time (for trends).  
- **WebSocket** `/vital-signs/ws`  
  - Bi‑directional WebSocket used by the device/app to push live vitals; the backend can broadcast updates to connected clients.

### Device Connection (`routers/connection.py`)

- **POST** `/device/device/status`  
  - Called by the wearable/device to report its **connection status** (`online`, `offline`, `disconnected`) and **battery %`.  
  - Also stores last‑seen timestamp and source IP in `device_connections`.  
- **GET** `/device/device/status/{patient_id}`  
  - For dashboards: return the latest `status` and `battery` associated with that user (`patient_id`).  
- **GET** `/device/caregiver/contact/{patient_id}`  
  - Given a patient, return their assigned caregiver’s ID, name, and phone number.

### Patient Location (`routers/patient_location.py`)

- **POST** `/location`  
  - Update the current GPS location (latitude/longitude) for a patient.  
- **GET** `/location/{patient_id}`  
  - Retrieve the last known location for the patient.  
- **WebSocket** `/location/ws`  
  - Stream location updates in real time for live maps/monitoring.

---

## Data Model Highlights

- `User` – core user record, with `age`, optional `pain_type`, roles, and relations to caregivers/patients.  
- `Medication` / `MedicationDose` – medication definitions and per-day doses.  
- `SleepLog` – sleep metrics keyed by `user_id` and `sleep_day` (weekday text).  
- `DeviceConnection` – current device connection status, battery, IP, timestamps.  
- `VitalSigns` – heart rate, blood pressure, SpO2, temperature, etc.  

---

## Running Tests (if configured)

If you have tests set up (e.g. with `pytest`):

```bash
pytest
```

---

## Notes

- Many endpoints expect an internal `API_KEY` via dependency `get_api_key`; ensure your client includes the correct header/query parameter as implemented in `utils.py`.  
- Use the autogenerated docs (`/docs`) to explore request/response schemas and try endpoints interactively.


