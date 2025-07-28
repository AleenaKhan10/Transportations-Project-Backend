from typing import List, Optional
from pydantic import BaseModel


class VAPICallRequest(BaseModel):
    driverIds: List[str]


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
    currentLocation: Optional[str] = None
    milesRemaining: Optional[float] = None
    eta: Optional[str] = None
    onTimeStatus: Optional[str] = None
    delayReason: Optional[str] = None
    driverMood: Optional[str] = None
    preferredCallbackTime: Optional[str] = None
    wantsTextInstead: Optional[bool] = None
    issueReported: Optional[str] = None
    recordingUrl: Optional[str] = None