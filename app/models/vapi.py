from typing import List, Optional
from pydantic import BaseModel


class VAPICallRequest(BaseModel):
    driverIds: List[str]


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