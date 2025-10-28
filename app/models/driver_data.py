from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from utils.vapi_client import vapi_client
from models.vapi import BatchCallRequest
from config import settings
import httpx
from fastapi import HTTPException
import random
import asyncio

logger = logging.getLogger(__name__)


# -------------------------------
# DriverTripData MODEL
# -------------------------------
class DriverTripData(SQLModel, table=True):
    __tablename__ = "trips"
    __table_args__ = {"extend_existing": True}

    tripId: str = Field(primary_key=True, max_length=50)
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    fuelPercent: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)
    ditatSetPoint: Optional[float] = None
    tempC: Optional[float] = None
    tempF: Optional[float] = None
    etaTimeDifference: Optional[str] = Field(max_length=100, default=None)
    trlCheck: Optional[str] = Field(max_length=10, default=None)
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)
    subStatusLabel: Optional[str] = Field(max_length=100, default=None)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000) -> List["DriverTripData"]:
        """Fetch all trips"""
        with cls.get_session() as session:
            return session.exec(select(cls).limit(limit)).all()

    @classmethod
    def get_by_driver(cls, driver_id: str) -> Optional["DriverTripData"]:
        with cls.get_session() as session:
            stmt = select(cls).where(cls.primaryDriverId == driver_id).limit(1)
            return session.exec(stmt).first()

    @classmethod
    def get_by_trip(cls, trip_id: str) -> Optional["DriverTripData"]:
        with cls.get_session() as session:
            stmt = select(cls).where(cls.tripId == trip_id).limit(1)
            return session.exec(stmt).first()


# -------------------------------
# ActiveLoadTracking MODEL
# -------------------------------
class ActiveLoadTracking(SQLModel, table=True):
    __tablename__ = "active_load_tracking"
    __table_args__ = {"extend_existing": True}

    load_id: str = Field(primary_key=True, max_length=50)
    trip_id: Optional[str] = Field(default=None, max_length=50)
    miles_threshold: Optional[int] = Field(default=250)
    driver_name: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default="EnRouteToDelivery", max_length=50)
    driver_phone_number: Optional[str] = Field(default=None, max_length=50)
    start_time: Optional[str] = Field(default=None, max_length=50)
    start_odometer_miles: Optional[float] = Field(default=None)
    current_odometer_miles: Optional[float] = Field(default=None)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000) -> List["ActiveLoadTracking"]:
        """Fetch all active load tracking rows"""
        with cls.get_session() as session:
            return session.exec(select(cls).limit(limit)).all()

    @classmethod
    def get_by_trip(cls, trip_id: str) -> Optional["ActiveLoadTracking"]:
        """Fetch active load by tripId"""
        with cls.get_session() as session:
            return session.exec(select(cls).where(cls.trip_id == trip_id)).first()


# -------------------------------
# VIOLATION ALERTS MODEL
# -------------------------------
class ViolationAlertDriver(SQLModel, table=True):
    __tablename__ = "violation_alerts"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True, max_length=50)
    load_id: Optional[str] = Field(default=None, max_length=50)
    violation_time: Optional[str] = Field(default=250)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000) -> List["ViolationAlertDriver"]:
        """Fetch all vilation alerts"""
        with cls.get_session() as session:
            return session.exec(select(cls).limit(limit)).all()

    @classmethod
    def get_by_trip_id(cls, trip_id: str) -> Optional["ViolationAlertDriver"]:
        """Fetch violation by id"""
        with cls.get_session() as session:
            return session.exec(select(cls).where(cls.load_id == trip_id)).first()


# -----------------------------
# Combined logic
# -----------------------------
REQUIRED_FUEL = 50  # %


def get_driver_summary(driver_id: str) -> Dict:
    """
    Fetch trip + active load + violation alert data for a driver.
    Adds checks for fuel %, temperature, route status, miles_threshold, and violation_time.
    """
    try:
        driver_trip = DriverTripData.get_by_driver(driver_id)
        active_load = None
        violation_alert = None

        if driver_trip and driver_trip.tripId:
            active_load = ActiveLoadTracking.get_by_trip(driver_trip.tripId)
            violation_alert = ViolationAlertDriver.get_by_trip_id(driver_trip.tripId)

        # --- Fuel percent logic ---
        fuel_percent = (
            getattr(driver_trip, "fuelPercent", None) if driver_trip else None
        )
        if fuel_percent is not None:
            if fuel_percent < REQUIRED_FUEL:
                fuel_percent = f"{fuel_percent}% (Below required {REQUIRED_FUEL}%)"
            elif fuel_percent > REQUIRED_FUEL:
                fuel_percent = f"{fuel_percent}% (Above required {REQUIRED_FUEL}%)"
            else:
                fuel_percent = f"{fuel_percent}% (At required {REQUIRED_FUEL}%)"

        # --- Temperature logic ---
        driver_temp_message = None
        set_point = getattr(driver_trip, "ditatSetPoint", None) if driver_trip else None
        current_temp = getattr(driver_trip, "tempC", None) if driver_trip else None

        if set_point is not None and current_temp is not None:
            if current_temp > set_point:
                driver_temp_message = f"{current_temp}°C (Above required {set_point}°C)"
            elif current_temp < set_point:
                driver_temp_message = f"{current_temp}°C (Below required {set_point}°C)"
            else:
                driver_temp_message = f"{current_temp}°C (At required temperature)"
        elif current_temp is not None:
            driver_temp_message = f"{current_temp}°C (No set point available)"
        elif set_point is not None:
            driver_temp_message = f"Required {set_point}°C (No current temp available)"

        # --- Route Status Logic ---
        out_of_route = getattr(driver_trip, "outOfRoute", None) if driver_trip else None
        trl_check = getattr(driver_trip, "trlCheck", None) if driver_trip else None
        sub_status = (
            getattr(driver_trip, "subStatusLabel", None) if driver_trip else None
        )

        route_status = None
        if (
            out_of_route == "🟢"
            and trl_check == "🟢"
            and sub_status == "En Route to Delivery"
        ):
            route_status = "Driver is on route"
        else:
            route_status = "Driver is out of route"

        # --- Build response ---
        response_data = {
            "driverId": driver_id,
            "fuelPercent": fuel_percent,
            "driver_temp": driver_temp_message,
            "routeStatus": route_status,
            "tripId": getattr(driver_trip, "tripId", None) if driver_trip else None,
            "onTimeStatus": (
                getattr(driver_trip, "onTimeStatus", None) if driver_trip else None
            ),
            "trlCheck": getattr(driver_trip, "trlCheck", None) if driver_trip else None,
            "timeDifference": (
                getattr(driver_trip, "etaTimeDifference", None) if driver_trip else None
            ),
            "miles_threshold": (
                getattr(active_load, "miles_threshold", None) if active_load else None
            ),
            "driver_name": (
                getattr(active_load, "driver_name", None) if active_load else None
            ),
            "phoneNumber": (
                getattr(active_load, "driver_phone_number", None)
                if active_load
                else None
            ),
            "startTime": (
                getattr(active_load, "start_time", None) if active_load else None
            ),
            "startOdometer": (
                getattr(active_load, "start_odometer_miles", None)
                if active_load
                else None
            ),
            "currentOdometer": (
                getattr(active_load, "current_odometer_miles", None)
                if active_load
                else None
            ),
            "violation_time": (
                getattr(violation_alert, "violation_time", None)
                if violation_alert
                else None
            ),
        }

        return {
            "message": "Driver trip and active load data fetched successfully",
            "data": response_data,
        }

    except Exception as err:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error fetching driver summary: {err}", exc_info=True)
        return {
            "message": "Error fetching driver summary",
            "error": str(err),
            "trace": error_details,  # ⚠️ remove this in production
        }


# -------------------------------
# MAKE VAPI MULTIPLE CALLS - BATCH CALL
# -------------------------------
def generate_conversational_prompt(
    driver_name: str, violations: List, custom_rules: str = ""
) -> str:
    """
    Generate a natural, conversational prompt under 250 characters.
    Includes random greetings, transitions, and natural language elements.
    """
    import random

    first_name = driver_name.split()[0] if driver_name else "Driver"

    # Random greetings
    greetings = [
        f"Hey {first_name}, how are you doing?",
        f"Hi {first_name}, hope the road's treating you well!",
        f"Hello {first_name}, this is your dispatcher.",
    ]

    # Random transitions
    transitions = [
        "Umm, I noticed",
        "So, checking the data",
        "Hmm, I see",
        "Alright, so",
    ]

    # Random closings
    closings = ["Got a sec?", "Can we chat?", "Let's talk.", "Quick call?"]

    # Build prompt
    opening = random.choice(greetings)

    # Combine violation messages
    messages = [v.description for v in violations]

    if messages:
        if len(messages) == 1:
            middle = f"{random.choice(transitions)} {messages[0].lower()}"
        elif len(messages) == 2:
            middle = f"{random.choice(transitions)} {messages[0].lower()} Also, {messages[1].lower()}"
        else:
            # Take first 2 violations to stay under 250 chars
            middle = f"{random.choice(transitions)} {messages[0].lower()} and {messages[1].lower()}"
    else:
        middle = "Just checking in on your trip"

    # Add custom rules as a note
    if custom_rules and custom_rules.strip():
        note = f" Note: {custom_rules.strip()}"
        # Only add if it fits
        if len(opening + middle + note) < 230:
            middle += note

    closing = random.choice(closings)

    prompt = f"{opening} {middle} {closing}"

    # Ensure under 250 characters
    if len(prompt) > 250:
        prompt = prompt[:247] + "..."

    return prompt


def generate_conversational_prompt_ibrar(
    driver_name: str, violations: list, custom_rules: str = ""
) -> str:
    """
    Generate a natural, conversational prompt for the VAPI assistant.
    The assistant will greet the driver, explain the purpose, confirm availability,
    go through each violation one by one, and close the call gracefully.

    Args:
        driver_name (str): The name of the driver (e.g., "John Doe")
        violations (list): A list of violation descriptions or dicts with "description"
        custom_rules (str, optional): Any custom communication rules or tone adjustments.

    Returns:
        str: A formatted conversational prompt for the VAPI agent.
    """
    # Clean violation texts
    formatted_violations = []
    for v in violations:
        if isinstance(v, dict):
            text = v.get("description") or v.get("message") or ""
        else:
            text = str(v)
        if text.strip():
            formatted_violations.append(text.strip())

    if not formatted_violations:
        formatted_violations = ["No specific violations were listed."]

    # --- Build conversation flow ---
    prompt = f"""
You are a professional dispatcher assistant calling {driver_name}.
Your goal is to discuss recent driving violations politely and clearly.

1. Begin by greeting {driver_name} warmly and introducing yourself as the dispatcher.
2. Explain that the purpose of this call is to review their recent vehicle or driving violations.
3. Ask politely if they are available to speak right now.
4. Once they confirm, go through each violation below one by one:
"""

    for i, violation in enumerate(formatted_violations, start=1):
        prompt += f"\n   - Violation {i}: {violation}"

    prompt += """
5. After reading each violation, pause and ask the driver to confirm or explain briefly.
6. Maintain a calm, respectful, and professional tone throughout the conversation.
7. Once all violations have been discussed, thank the driver sincerely for their time.
8. End the call gracefully by saying something like:
   "That’s all for today, drive safe and have a good day."

"""

    if custom_rules:
        prompt += f"\nAdditional communication rules:\n{custom_rules.strip()}\n"

    prompt += "\nKeep the tone natural, empathetic, and conversational. Avoid robotic phrasing."

    return prompt.strip()


async def make_drivers_violation_batch_call(request: BatchCallRequest):
    """
    Process driver violation call.
    Generates conversational prompt and calls the RingCentral webhook.
    Note: Even though the request has a 'drivers' array, only ONE driver is sent per call.
    """
    try:
        # Get the first (and only) driver from the array
        if not request.drivers or len(request.drivers) == 0:
            raise HTTPException(status_code=400, detail="No driver data provided")

        driver = request.drivers[0]  # Only one driver per call

        logger.info(
            f"📞 Processing call for driver: {driver.driverName} ({driver.driverId})"
        )

        # Normalize phone number to E.164 format
        phone_digits = "".join(filter(str.isdigit, driver.phoneNumber))
        # normalized_phone = f"+1{phone_digits}" if not phone_digits.startswith("1") else f"+{phone_digits}"
        normalized_phone = "+12192002824"

        # Generate conversational prompt
        prompt = generate_conversational_prompt(
            driver_name=driver.driverName,
            violations=driver.violations.violationDetails,
            custom_rules=driver.customRules or "",
        )
        # prompt = generate_conversational_prompt_ibrar(
        #     driver_name=driver.driverName,
        #     violations=driver.violations.violationDetails,
        #     custom_rules=driver.customRules or "",
        # )

        logger.info(f"📞 Calling {driver.driverName} at {normalized_phone}")
        logger.info(f"📝 Prompt ({len(prompt)} chars): {prompt}")

        # Call webhook
        webhook_payload = {"driverPhoneNumber": normalized_phone, "prompt": prompt}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://vapi-ringcentral-bridge-181509438418.us-central1.run.app/api/webhook/call-driver",
                json=webhook_payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            webhook_response = response.json()

        logger.info(f"✅ Call initiated successfully for {driver.driverName}")

        return {
            "message": "Call initiated successfully",
            "timestamp": request.timestamp,
            "driver": {
                "driverId": driver.driverId,
                "driverName": driver.driverName,
                "phoneNumber": normalized_phone,
            },
            "prompt": prompt,
            "promptLength": len(prompt),
            "webhook_response": webhook_response,
        }

    except HTTPException:
        raise
    except Exception as err:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error making driver call: {err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Call error: {str(err)}")


# -------------------------------
# MAKE VAPI VIOLATION CALL --- IBRAR
# -------------------------------


# ----------------------------------------------
# Generate Prompt for Each Violation
# ----------------------------------------------
# def generate_violation_prompt(
#     driver_name: str, violation_text: str, index: int, total: int
# ) -> str:
#     """
#     Generates a single prompt for a specific violation.
#     Professional, conversational, and under 250 chars.
#     """
#     first_name = driver_name.split()[0] if driver_name else "Driver"

#     greetings = [
#         f"Hello {first_name}, this is your dispatcher.",
#         f"Hi {first_name}, dispatcher here.",
#         f"Good day {first_name}, I’m calling from dispatch.",
#     ]

#     intro = random.choice(greetings) if index == 0 else ""

#     # Main violation message
#     if total > 1:
#         progress = f"This is alert {index + 1} of {total}. "
#     else:
#         progress = ""

#     body = f"{progress}The issue recorded is: {violation_text}. Do you confirm this?"

#     closing_options = [
#         "Once confirmed, we’ll move to the next one.",
#         "Please confirm so we can continue.",
#         "Let me know if that’s correct before we continue.",
#     ]
#     closing = random.choice(closing_options)

#     prompt = f"{intro} {body} {closing}".strip()

#     if len(prompt) > 250:
#         prompt = prompt[:247] + "..."

#     return prompt


# ----------------------------------------------
# Generate Final Closing Prompt
# ----------------------------------------------
# def generate_closing_prompt(driver_name: str) -> str:
#     """Final closing message when all violations are reviewed."""
#     first_name = driver_name.split()[0] if driver_name else "Driver"

#     closings = [
#         f"Thanks {first_name}, that covers all the alerts for now. Safe driving out there!",
#         f"Appreciate your time, {first_name}. That’s all for today — drive safe!",
#         f"All set, {first_name}. Thanks for confirming. Have a safe trip ahead!",
#     ]

#     return random.choice(closings)


# ----------------------------------------------
# Make Call for Each Violation
# ----------------------------------------------
# async def make_drivers_violation_call(request):
#     """
#     Process driver violation call.
#     Generates and sends a separate conversational prompt for each violation.
#     Waits for driver response between each prompt (simulated here with async sleep).
#     Returns all VAPI webhook responses.
#     """
#     try:
#         if not request.drivers or len(request.drivers) == 0:
#             raise HTTPException(status_code=400, detail="No driver data provided")

#         driver = request.drivers[0]
#         driver_name = driver.driverName
#         violations = driver.violations.violationDetails or []

#         if not violations:
#             raise HTTPException(
#                 status_code=400, detail="No violations found for this driver"
#             )

#         print(f"📞 Starting step-by-step call flow for {driver_name}")

#         # Normalize phone number
#         phone_digits = "".join(filter(str.isdigit, driver.phoneNumber))
#         # normalized_phone = f"+1{phone_digits}" if not phone_digits.startswith("1") else f"+{phone_digits}"
#         normalized_phone = "+1 (219) 200-2824"  # Static for now

#         webhook_responses = []

#         async with httpx.AsyncClient(timeout=30) as client:
#             total = len(violations)

#             for index, v in enumerate(violations):
#                 # Extract violation text (works for dicts or models)
#                 if hasattr(v, "description"):
#                     violation_text = v.description
#                 elif hasattr(v, "message"):
#                     violation_text = v.message
#                 elif isinstance(v, dict):
#                     violation_text = v.get("description") or v.get("message", "")
#                 else:
#                     violation_text = ""

#                 violation_text = violation_text.strip()
#                 if not violation_text:
#                     continue

#                 # Generate conversational prompt
#                 prompt = generate_violation_prompt(
#                     driver_name, violation_text, index, total
#                 )

#                 # Send prompt via webhook
#                 payload = {"driverPhoneNumber": normalized_phone, "prompt": prompt}
#                 print(f"🚀 Sending prompt {index + 1}/{total}: {prompt}")

#                 response = await client.post(
#                     "https://vapi-ringcentral-bridge-181509438418.us-central1.run.app/api/webhook/call-driver",
#                     json=payload,
#                     headers={"Content-Type": "application/json"},
#                 )
#                 response.raise_for_status()

#                 webhook_response = response.json()
#                 webhook_responses.append(
#                     {
#                         "violationIndex": index + 1,
#                         "prompt": prompt,
#                         "webhookResponse": webhook_response,
#                     }
#                 )

#                 print(f"✅ Violation {index + 1}/{total} prompt sent successfully")

#                 # ⏳ Wait for driver response (simulation: 4 seconds)
#                 await asyncio.sleep(4)

#             # Final closing message
#             final_prompt = generate_closing_prompt(driver_name)
#             payload = {"driverPhoneNumber": normalized_phone, "prompt": final_prompt}
#             print(f"📞 Sending closing message: {final_prompt}")

#             final_response = await client.post(
#                 "https://vapi-ringcentral-bridge-181509438418.us-central1.run.app/api/webhook/call-driver",
#                 json=payload,
#                 headers={"Content-Type": "application/json"},
#             )
#             final_response.raise_for_status()

#             webhook_responses.append(
#                 {
#                     "type": "closing",
#                     "prompt": final_prompt,
#                     "webhookResponse": final_response.json(),
#                 }
#             )

#         print(f"🎯 Call flow completed for {driver_name}")

#         return {
#             "message": "All violation prompts sent successfully",
#             "driver": {
#                 "driverId": driver.driverId,
#                 "driverName": driver_name,
#                 "phoneNumber": normalized_phone,
#             },
#             "totalViolations": len(violations),
#             "webhook_responses": webhook_responses,
#         }

#     except Exception as err:
#         print("❌ Error in make_drivers_violation_call:", err)
#         raise HTTPException(status_code=500, detail=f"Call error: {str(err)}")
