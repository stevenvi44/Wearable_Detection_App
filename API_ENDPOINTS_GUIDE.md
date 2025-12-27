# API Endpoints Guide - Easy Explanation

## 📋 Table of Contents

1. [Authentication Endpoints](#1-authentication-endpoints)
2. [User Management](#2-user-management)
3. [Vital Signs](#3-vital-signs)
4. [Device & Connection](#4-device--connection)
5. [Patient Location](#5-patient-location)
6. [Activity & Sleep](#6-activity--sleep)
7. [Medications](#7-medications)
8. [WebSocket Endpoints](#8-websocket-endpoints)

---

## 🔐 1. Authentication Endpoints

**Base URL:** `/auth`

### Register New User
**`POST /auth/register`**
- **What it does:** Creates a new user account
- **Who uses it:** Mobile app (when user signs up)
- **What you send:** Name, email, password, phone, etc.
- **What you get:** Confirmation message + verification code sent to email

### Verify Email
**`POST /auth/verify-email`**
- **What it does:** Verifies user's email address
- **Who uses it:** Mobile app (after registration)
- **What you send:** Email + verification code
- **What you get:** Account activated

### Login
**`POST /auth/login`**
- **What it does:** Logs user in and gives them access token
- **Who uses it:** Mobile app (every time user opens app)
- **What you send:** Username/email + password
- **What you get:** Access token, refresh token, user_id

### Refresh Token
**`POST /auth/refresh`**
- **What it does:** Gets a new access token when old one expires
- **Who uses it:** Mobile app (automatically)
- **What you send:** Refresh token
- **What you get:** New access token

### Forgot Password
**`POST /auth/forgot-password`**
- **What it does:** Sends password reset code to email
- **Who uses it:** Mobile app (when user forgets password)
- **What you send:** Email address
- **What you get:** Reset code sent to email

### Reset Password
**`POST /auth/reset-password`**
- **What it does:** Changes user's password
- **Who uses it:** Mobile app (after forgot password)
- **What you send:** Email + reset code + new password
- **What you get:** Password changed successfully

### Connect Patient & Caregiver
**`POST /auth/connect`**
- **What it does:** Links a caregiver to a patient
- **Who uses it:** Admin or during setup
- **What you send:** patient_id + caregiver_id
- **What you get:** Confirmation that they're linked

---

## 👥 2. User Management

**Base URL:** `/users`

### Create User
**`POST /users/`**
- **What it does:** Creates a new user (admin function)
- **Who uses it:** Admin panel
- **What you send:** User details
- **What you get:** Created user info

### Get All Users
**`GET /users/`**
- **What it does:** Gets list of all users
- **Who uses it:** Admin panel
- **What you send:** Nothing (optional: skip, limit for pagination)
- **What you get:** List of all users

### Get User by ID
**`GET /users/{user_id}`**
- **What it does:** Gets details of one specific user
- **Who uses it:** Mobile app, admin panel
- **What you send:** User ID in URL
- **What you get:** User details (name, email, phone, etc.)

### Update User
**`PUT /users/{user_id}`**
- **What it does:** Updates user information
- **Who uses it:** Mobile app (user profile page)
- **What you send:** User ID + updated fields
- **What you get:** Updated user info

### Delete User
**`DELETE /users/{user_id}`**
- **What it does:** Deletes a user account
- **Who uses it:** Admin panel
- **What you send:** User ID
- **What you get:** User deleted (no content)

---

## ❤️ 3. Vital Signs

**Base URL:** `/vitals`

### Update Vital Signs
**`POST /vitals/update`**
- **What it does:** Saves new vital signs reading from watch
- **Who uses it:** **Watch (embedded device)** ⭐
- **What you send:** user_id, hr (heart rate), spo2, temp, stress
- **What you get:** Saved vital signs + **ML prediction** (safe_now/warning_soon/critical)
- **Special:** Automatically sends to caregivers via WebSocket

### Get Latest Vital Signs
**`GET /vitals/latest/{user_id}`**
- **What it does:** Gets the most recent vital signs for a patient
- **Who uses it:** Mobile app (caregiver or patient view)
- **What you send:** User ID in URL
- **What you get:** Latest vital signs reading

### Get Vital Signs History
**`GET /vitals/history/{user_id}`**
- **What it does:** Gets past vital signs readings (for charts/graphs)
- **Who uses it:** Mobile app (to show trends over time)
- **What you send:** User ID in URL
- **What you get:** List of past vital signs

### Get ML Prediction
**`GET /vitals/prediction/{user_id}`**
- **What it does:** Gets emergency status prediction from ML model
- **Who uses it:** Mobile app (to check patient status)
- **What you send:** User ID in URL
- **What you get:** Prediction: safe_now, warning_soon, or critical + confidence

### Batch Upload Vital Signs
**`POST /vitals/batch`**
- **What it does:** Uploads multiple vital signs at once
- **Who uses it:** **Watch (when reconnecting after being offline)** ⭐
- **What you send:** user_id + array of vital signs
- **What you get:** Count of successful/failed uploads

---

## 📱 4. Device & Connection

**Base URL:** `/device`

### Update Device Status
**`POST /device/device/status`**
- **What it does:** Updates watch connection status and battery level
- **Who uses it:** **Watch (as heartbeat every 5-10 minutes)** ⭐
- **What you send:** user_id, status (online/offline), battery (0-100)
- **What you get:** Updated device status

### Get Device Status
**`GET /device/device/status/{patient_id}`**
- **What it does:** Gets current device status for a patient
- **Who uses it:** Mobile app (to show if watch is connected)
- **What you send:** Patient ID in URL
- **What you get:** Status (online/offline) + battery level

### Register Device
**`POST /device/register`**
- **What it does:** Registers/pairs a watch to a user
- **Who uses it:** Mobile app (during initial watch setup)
- **What you send:** user_id, device_identifier (MAC/serial), device_name
- **What you get:** Device registration info

### Get Caregiver's Patients
**`GET /device/caregiver/patients/{caregiver_id}`**
- **What it does:** Gets list of all patients assigned to a caregiver
- **Who uses it:** Mobile app (caregiver's patient list)
- **What you send:** Caregiver ID in URL
- **What you get:** List of patients with their info

### Get Patient Dashboard
**`GET /device/caregiver/dashboard/{caregiver_id}/{patient_id}`**
- **What it does:** Gets ALL patient data in one request (vitals + connection + location)
- **Who uses it:** Mobile app (caregiver's patient dashboard)
- **What you send:** Caregiver ID + Patient ID in URL
- **What you get:** Complete patient info (vitals, device status, location)

### Get Caregiver Contact
**`GET /device/caregiver/contact/{patient_id}`**
- **What it does:** Gets caregiver's contact info for a patient
- **Who uses it:** Watch or emergency systems
- **What you send:** Patient ID in URL
- **What you get:** Caregiver's name and phone number

---

## 📍 5. Patient Location

**Base URL:** `/patient/location`

### Update Location
**`POST /patient/location/update`**
- **What it does:** Updates patient's GPS location
- **Who uses it:** **Watch or mobile app** ⭐
- **What you send:** patient_id, latitude, longitude
- **What you get:** Location saved + sent to caregivers via WebSocket

### Get Latest Location
**`GET /patient/location/latest/{patient_id}`**
- **What it does:** Gets patient's current location
- **Who uses it:** Mobile app (to show on map)
- **What you send:** Patient ID in URL
- **What you get:** Latest GPS coordinates

---

## 🏃 6. Activity & Sleep

**Base URL:** `/api/activity`

### Upload Weekly Report
**`POST /api/activity/weekly-report`**
- **What it does:** Saves weekly activity summary
- **Who uses it:** Watch or mobile app
- **What you send:** user_id, date, average_steps, calories, etc.
- **What you get:** Report saved

### Get Weekly Report
**`GET /api/activity/weekly-report`**
- **What it does:** Gets weekly activity report
- **Who uses it:** Mobile app
- **What you send:** user_id + date
- **What you get:** Weekly activity summary

### Upload Sleep Data
**`POST /api/activity/sleep`**
- **What it does:** Saves sleep tracking data
- **Who uses it:** Watch
- **What you send:** user_id, sleep_day (Mon-Sun), sleep hours, deep sleep, etc.
- **What you get:** Sleep data saved

### Get Sleep Data
**`GET /api/activity/sleep`**
- **What it does:** Gets sleep data for a specific day
- **Who uses it:** Mobile app
- **What you send:** user_id + sleep_day
- **What you get:** Sleep data for that day

### Upload Weekly Steps
**`POST /api/activity/weekly-steps`**
- **What it does:** Saves daily step count
- **Who uses it:** Watch
- **What you send:** user_id, week (mon-sun), steps
- **What you get:** Steps saved

### Get Weekly Steps
**`GET /api/activity/weekly-steps`**
- **What it does:** Gets step counts for a week
- **Who uses it:** Mobile app (for charts)
- **What you send:** user_id + date
- **What you get:** Steps for each day of the week

### Upload Dashboard Summary
**`POST /api/activity/summary`**
- **What it does:** Saves daily activity summary
- **Who uses it:** Watch
- **What you send:** user_id, date, steps, active_minutes, rest_hours, mobility_level
- **What you get:** Summary saved

### Get Dashboard Summary
**`GET /api/activity/summary`**
- **What it does:** Gets daily activity summary
- **Who uses it:** Mobile app (dashboard view)
- **What you send:** user_id + date
- **What you get:** Daily activity summary

---

## 💊 7. Medications

**Base URL:** `/api/medications`

### Add Medication
**`POST /api/medications`**
- **What it does:** Adds a new medication to patient's list
- **Who uses it:** Mobile app (caregiver or patient)
- **What you send:** user_id, name, dosage, frequency
- **What you get:** Medication added

### Get Today's Medications
**`GET /api/medications/today`**
- **What it does:** Gets all medications scheduled for today
- **Who uses it:** Mobile app (medication reminder screen)
- **What you send:** user_id + date (optional)
- **What you get:** List of medications due today

### Upload Today's Medications
**`POST /api/medications/today`**
- **What it does:** Sets medications for a specific day
- **Who uses it:** Mobile app
- **What you send:** user_id + list of medications
- **What you get:** Medications scheduled

### Take Medication
**`POST /api/medications/{dose_id}/take`**
- **What it does:** Marks medication as taken
- **Who uses it:** Mobile app (when patient takes medicine)
- **What you send:** Dose ID in URL
- **What you get:** Confirmation + timestamp

### Skip Medication
**`POST /api/medications/{dose_id}/skip`**
- **What it does:** Marks medication as skipped
- **Who uses it:** Mobile app (when patient skips medicine)
- **What you send:** Dose ID + reason
- **What you get:** Confirmation

---

## 🔄 8. WebSocket Endpoints

**Real-time connections for instant updates**

### Vital Signs - General
**`WS /vitals/ws/vitals?X-API-KEY=key`**
- **What it does:** Receives ALL vital signs updates from ALL patients
- **Who uses it:** Testing, general monitoring
- **Privacy:** ⚠️ Low (sees everyone's data)
- **Use:** Testing only

### Vital Signs - Caregiver Specific ⭐
**`WS /vitals/ws/vitals/caregiver/{caregiver_id}?X-API-KEY=key`**
- **What it does:** Receives vital signs ONLY for assigned patients
- **Who uses it:** **Caregiver mobile app** ⭐
- **Privacy:** ✅ High (only assigned patients)
- **Use:** **Production - Recommended!**

### Location - General
**`WS /patient/location/ws/location?X-API-KEY=key`**
- **What it does:** Receives ALL location updates from ALL patients
- **Who uses it:** Testing, general monitoring
- **Privacy:** ⚠️ Low (sees everyone's location)
- **Use:** Testing only

### Location - Caregiver Specific ⭐
**`WS /patient/location/ws/location/caregiver/{caregiver_id}?X-API-KEY=key`**
- **What it does:** Receives location updates ONLY for assigned patients
- **Who uses it:** **Caregiver mobile app** ⭐
- **Privacy:** ✅ High (only assigned patients)
- **Use:** **Production - Recommended!**

---

## 🎯 Quick Reference by User Type

### For Watch (Embedded Device)
- ✅ `POST /vitals/update` - Send vital signs
- ✅ `POST /vitals/batch` - Sync offline data
- ✅ `POST /device/device/status` - Heartbeat
- ✅ `POST /device/register` - Initial pairing
- ✅ `POST /patient/location/update` - Send location

### For Mobile App (Patient)
- ✅ `POST /auth/login` - Login
- ✅ `GET /vitals/latest/{user_id}` - View own vitals
- ✅ `GET /vitals/history/{user_id}` - View history
- ✅ `GET /api/medications/today` - View medications
- ✅ `POST /api/medications/{id}/take` - Mark taken

### For Mobile App (Caregiver)
- ✅ `POST /auth/login` - Login
- ✅ `GET /device/caregiver/patients/{id}` - Get patient list
- ✅ `GET /device/caregiver/dashboard/{caregiver_id}/{patient_id}` - View patient dashboard
- ✅ `WS /vitals/ws/vitals/caregiver/{id}` - Real-time vitals
- ✅ `WS /patient/location/ws/location/caregiver/{id}` - Real-time location

---

## 🔑 Authentication

**All endpoints require:**
- **API Key** in header: `X-API-KEY: your_api_key`

**Some endpoints also require:**
- **JWT Token** in header: `Authorization: Bearer <token>` (after login)

---

## 📊 Data Flow Examples

### Example 1: Watch Sends Vitals
```
Watch → POST /vitals/update
       ↓
Backend saves to database
       ↓
ML model generates prediction
       ↓
Backend broadcasts to caregivers (WebSocket)
       ↓
Caregiver app receives update instantly
```

### Example 2: Caregiver Views Patient
```
Caregiver app → GET /device/caregiver/dashboard/88/87
              ↓
Backend returns: vitals + connection + location
              ↓
Caregiver sees complete patient status
```

### Example 3: Real-Time Monitoring
```
Caregiver connects → WS /vitals/ws/vitals/caregiver/88
                  ↓
Patient sends vitals → POST /vitals/update
                  ↓
Backend automatically sends to caregiver
                  ↓
Caregiver receives update instantly (no refresh needed!)
```

---

## ✅ Summary

**Total Endpoints:** ~40+ endpoints

**Main Categories:**
- 🔐 Authentication (7 endpoints)
- 👥 Users (5 endpoints)
- ❤️ Vital Signs (5 endpoints + 2 WebSocket)
- 📱 Device (6 endpoints)
- 📍 Location (2 endpoints + 2 WebSocket)
- 🏃 Activity (8 endpoints)
- 💊 Medications (5 endpoints)

**Key Endpoints for Watch:**
- `POST /vitals/update` ⭐
- `POST /vitals/batch` ⭐
- `POST /device/device/status` ⭐
- `POST /device/register` ⭐

**Key Endpoints for Caregivers:**
- `GET /device/caregiver/dashboard/{caregiver_id}/{patient_id}` ⭐
- `WS /vitals/ws/vitals/caregiver/{caregiver_id}` ⭐
- `WS /patient/location/ws/location/caregiver/{caregiver_id}` ⭐

---

## 🚀 That's It!

All endpoints are documented with:
- ✅ What they do
- ✅ Who uses them
- ✅ What to send
- ✅ What you get back

**Need more details?** Check the FastAPI docs at `http://localhost:8000/docs` for interactive API testing!

