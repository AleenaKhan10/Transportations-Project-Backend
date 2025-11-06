from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from models.drivers_trigger_calls import DriverTriggersCalls
from helpers import logger
from config import settings
import requests
import json

router = APIRouter(prefix="/driver_triggers_calls", tags=["driver_triggers_calls"])

# ============================================================
# 📦 SCHEMAS
# ============================================================

class ViolationDetails(BaseModel):
    type: str
    description: str

class Violations(BaseModel):
    tripId: Optional[str] = None
    violationDetails: List[ViolationDetails]

class DriverPayload(BaseModel):
    driverId: str
    driverName: str
    phoneNumber: str
    customRules: Optional[str]
    violations: Violations

class CreateCallPayload(BaseModel):
    callType: str
    timestamp: str
    drivers: List[DriverPayload]

class SaveCallPayload(BaseModel):
    call_id: str
    driver_id: str
    driver_name: str
    phone: Optional[str]
    call_summary: Optional[str]
    call_duration: Optional[int]

# ============================================================
# 1️⃣ POST /make-call — Create Outbound Call using VAPI
# ============================================================
@router.post("/make-call")
def make_vapi_call(payload: CreateCallPayload):
    """
    Step 1 — Create outbound call using VAPI
    """
    try:
        driver = payload.drivers[0]  # Handle one driver per call

        # ✅ Format phone number properly
        phone = driver.phoneNumber
        phone = phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        if not phone.startswith("+"):
            phone = f"+1{phone}"

        # ✅ Correct Vapi payload (based on official documentation)
        vapi_payload = {
            "type": "outboundPhoneCall",  # ✅ Correct field
            "assistantId": settings.VAPI_ASSISTANT_ID,
            "phoneNumberId": settings.VAPI_PHONENUMBER_ID,
            "customer": {
                "number": phone,
                "name": driver.driverName
            },
            "assistantOverrides": {
                "metadata": {
                    "driverId": driver.driverId,
                    "callType": payload.callType,
                    "customRules": driver.customRules,
                    "violations": [v.dict() for v in driver.violations.violationDetails]
                }
            }
        }

        headers = {
            "Authorization": f"Bearer {settings.VAPI_API_KEY}",
            "Content-Type": "application/json"
        }

        # ✅ Make API request
        response = requests.post("https://api.vapi.ai/call", headers=headers, data=json.dumps(vapi_payload))
        if response.status_code not in (200, 201):
            logger.error(f"VAPI create call failed: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        # ✅ Extract call_id
        data = response.json()
        call_id = data.get("id")
        if not call_id:
            raise HTTPException(status_code=500, detail="No call_id returned from Vapi response")

        return {
            "message": "Call initiated successfully",
            "call_id": call_id,
            "vapi_response": data
        }

    except Exception as e:
        logger.error(f"Error creating VAPI call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2️⃣ GET /get-call/{call_id} — Fetch Call Details from VAPI
# ============================================================
@router.get("/get-call/{call_id}")
def get_call_details(call_id: str):
    """
    Step 2 — Fetch call details and summary from VAPI
    """
    try:
        headers = {"Authorization": f"Bearer {settings.VAPI_API_KEY}"}
        response = requests.get(f"https://api.vapi.ai/call/{call_id}", headers=headers)

        if response.status_code not in (200, 201):
            logger.error(f"VAPI get call failed: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        data = response.json()

        # Vapi response typically includes: id, duration, messages, summary, etc.
        return {"message": "Call details fetched successfully", "data": data}

    except Exception as e:
        logger.error(f"Error fetching VAPI call details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3️⃣ POST /save-call — Save Call Data to Database
# ============================================================
@router.post("/save-call")
def save_call_to_db(payload: SaveCallPayload):
    """
    Step 3 — Save fetched call data to Supabase (via SQLModel)
    """
    try:
        record = DriverTriggersCalls(
            call_id=payload.call_id,
            driver_id=payload.driver_id,
            driver_name=payload.driver_name,
            phone=payload.phone,
            call_summary=payload.call_summary,
            call_duration=payload.call_duration,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with DriverTriggersCalls.get_session() as session:
            session.add(record)
            session.commit()

        return {"message": "Call data saved successfully", "data": payload.dict()}

    except Exception as e:
        logger.error(f"Error saving call data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 4️⃣ GET /get-all — Fetch All Saved Calls from Database
# ============================================================
@router.get("/get-all")
def get_all_calls():
    """
    Step 4 — Fetch all stored call records
    """
    try:
        records = DriverTriggersCalls.get_all()
        return {"message": "All driver calls fetched successfully", "data": records}
    except Exception as e:
        logger.error(f"Error fetching calls: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
