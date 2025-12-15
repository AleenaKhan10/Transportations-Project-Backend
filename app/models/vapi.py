from typing import List, Optional, Dict
from pydantic import BaseModel


# --- Request Schema ---
class ViolationDetail(BaseModel):
    type: str
    description: str


class Violations(BaseModel):
    tripId: Optional[str] = (
        None  # Optional - will be fetched automatically from driverId
    )
    violationDetails: List[ViolationDetail]


class DriverData(BaseModel):
    driverId: str
    driverName: str
    phoneNumber: str
    violations: Violations
    customRules: Optional[str] = None


class BatchCallRequest(BaseModel):
    callType: str
    timestamp: str
    drivers: List[DriverData]
    trip_id: Optional[str] = (
        None  # Optional - will be fetched automatically from driver's active trip
    )
    user_id: int = 0  # Default to 0 for scheduler-triggered calls
    # Retry tracking fields
    retry_count: int = 0  # Current retry attempt (0 = first try)
    parent_call_sid: Optional[str] = None  # Link to original call for retries


# --- Request Schema CLOSE ---


class VAPICallRequest(BaseModel):
    driverIds: List[str]
    vapiData: Optional[Dict[str, "VAPIData"]] = None  # Map of driverId to VAPIData


class VAPIData(BaseModel):
    tripId: Optional[str] = None
    driverName: Optional[str] = None
    currentLocation: Optional[str] = None
    milesLeft: Optional[float] = None
    speed: Optional[float] = None
    eta: Optional[str] = None
    deliveryTime: Optional[str] = None
    destination: Optional[str] = None
    loadingLocation: Optional[str] = None
    onTimeStatus: Optional[str] = None
    delayReason: Optional[str] = None
    loadGroup: Optional[str] = None
    tripStatus: Optional[str] = None
    subStatus: Optional[str] = None
    driverFeeling: Optional[str] = None
    pickupTime: Optional[str] = None
    lateAfterTime: Optional[str] = None
    additionalNotes: Optional[str] = None


class DriverCallInsightsUpdate(BaseModel):
    driverId: str
    tripId: str
    currentLocation: Optional[str] = None
    milesRemaining: Optional[float] = None
    eta: Optional[str] = None
    onTimeStatus: Optional[str] = None
    delayReason: Optional[str] = None
    driverMood: Optional[str] = None
    preferredCallbackTime: Optional[str] = None
    wantsTextInstead: Optional[bool] = None
    recordingUrl: Optional[str] = None
    callSummary: Optional[str] = None


# --- Prompt Generation Request Schema ---
class GeneratePromptRequest(BaseModel):
    driverId: str
    driverName: str
    phoneNumber: str
    triggers: List[ViolationDetail]
    customRules: Optional[str] = None
