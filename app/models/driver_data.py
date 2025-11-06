from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from utils.vapi_client import vapi_client
from models.vapi import BatchCallRequest
from config import settings
import httpx
from fastapi import HTTPException

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
        """Get the latest trip for a driver (no specific ordering)"""
        with cls.get_session() as session:
            stmt = select(cls).where(cls.primaryDriverId == driver_id).limit(1)
            return session.exec(stmt).first()

    @classmethod
    def get_latest_by_driver(cls, driver_id: str) -> Optional["DriverTripData"]:
        """Get the most recent/active trip for a driver"""
        with cls.get_session() as session:
            # Order by tripId descending to get the latest trip
            # You can also add .order_by(cls.lastModified.desc()) if that field exists
            stmt = (
                select(cls)
                .where(cls.primaryDriverId == driver_id)
                .order_by(cls.tripId.desc())
                .limit(1)
            )
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
# VIOLATION TYPE CONSTANTS
# -------------------------------
DATA_DRIVEN_VIOLATIONS = {
    "temperature_not_equal",
    "driver_stopping_200_miles",
    "driver_out_of_route",
    "trailer_check",
    "fuel_lower_than_required",
}

REMINDER_VIOLATIONS = {
    "verify_load_pallet_count",
    "send_loaded_picture",
    "send_seal_pictures",
    "secure_load_pictures",
    "check_destination_bol",
    "wait_for_approval",
}


# -------------------------------
# DATA FETCHING FOR VIOLATIONS
# -------------------------------
def get_trip_data_for_violations(trip_id: str, driver_id: str) -> Dict:
    """
    Fetch trip data and active load data for generating violation prompts.
    Returns a dictionary with all necessary fields including location.
    """
    try:
        # Import Trip model to get location data
        from models.trips import Trip

        # Get trip data from both tables
        driver_trip = DriverTripData.get_by_trip(trip_id)
        trip_full = Trip.get_by_trip_id(trip_id)

        # Get active load tracking
        active_load = ActiveLoadTracking.get_by_trip(trip_id) if driver_trip else None

        if not driver_trip:
            logger.warning(f"No trip data found for tripId: {trip_id}")
            return {}

        # Calculate miles driven
        miles_driven = None
        if (
            active_load
            and active_load.start_odometer_miles
            and active_load.current_odometer_miles
        ):
            miles_driven = (
                active_load.current_odometer_miles - active_load.start_odometer_miles
            )

        # Get location from full trip data if available
        current_location = None
        if trip_full and hasattr(trip_full, "samsaraLocation"):
            current_location = trip_full.samsaraLocation

        return {
            "trip_id": trip_id,
            "driver_id": driver_id,
            "ditat_set_point": driver_trip.ditatSetPoint,
            "current_temp_c": driver_trip.tempC,
            "current_temp_f": driver_trip.tempF,
            "out_of_route": driver_trip.outOfRoute,
            "sub_status": driver_trip.subStatusLabel,
            "current_location": current_location,
            "fuel_percent": driver_trip.fuelPercent,
            "trl_check": driver_trip.trlCheck,
            "miles_driven": miles_driven,
            "start_odometer": active_load.start_odometer_miles if active_load else None,
            "current_odometer": (
                active_load.current_odometer_miles if active_load else None
            ),
        }

    except Exception as err:
        logger.error(f"Error fetching trip data: {err}", exc_info=True)
        return {}


# -------------------------------
# PERSONALIZED PROMPT BUILDERS
# -------------------------------
def build_temperature_violation_prompt(trip_data: Dict) -> str:
    set_point = trip_data.get("ditat_set_point")
    current_temp = trip_data.get("current_temp_f")

    if set_point is None or current_temp is None:
        return None  # Skip if no data

    # Skip if temperatures are equal
    if int(set_point) == int(current_temp):
        return None

    if current_temp > set_point:
        return f"Your temp is at {int(current_temp)} degrees Fahrenheit but needs to be {int(set_point)} degrees Fahrenheit. What's going on with that?"
    else:
        return f"Temp is running cold at {int(current_temp)} degrees Fahrenheit, needs to be {int(set_point)} degrees Fahrenheit. Can you adjust it?"


def build_out_of_route_prompt(trip_data: Dict) -> str:
    location = trip_data.get("current_location")

    if location:
        return f"I see you're at {location} and showing out of route. What's the reason for the detour?"
    else:
        return "You're showing out of route. Can you tell me why?"


def build_stopping_200_miles_prompt(trip_data: Dict) -> str:
    miles = trip_data.get("miles_driven")

    if miles is not None:
        return f"I see you stopped after only {int(miles)} miles, before completing 200 miles. What's the reason for stopping early?"

    return (
        "You stopped before completing 200 miles. What's the reason for the early stop?"
    )


def build_fuel_violation_prompt(trip_data: Dict) -> str:
    fuel = trip_data.get("fuel_percent")
    required = REQUIRED_FUEL

    if fuel is None:
        return None  # Skip if no data

    # Skip if fuel is at or above required level
    if fuel >= required:
        return None

    return f"Your fuel is at {int(fuel)}%. What's your refueling plan?"


def build_trailer_check_prompt(trip_data: Dict) -> str:
    trl_check = trip_data.get("trl_check")

    if trl_check == "🔴":
        return "I'm seeing an alert that your truck and trailer aren't together. Are you with your trailer right now?"

    return "Quick check - are you and your trailer together right now?"


# -------------------------------
# SYSTEM PROMPTT
# -------------------------------
SYSTEM_PROMPT = """You are a professional dispatcher calling a truck driver. Your job is to go through some important points about their current trip in a natural, friendly way.

=== HOW TO START THE CALL ===
1. Greet them warmly by name: "Hey [Name], this is dispatch calling"
2. Ask if they have a moment to talk: "Do you have a few minutes to chat about your trip?"
3. If they sound busy, ask: "Is this a good time, or should I call back in a bit?"
4. Use natural phrases like "Alright", "Okay great", "Perfect"

=== YOUR CONVERSATIONAL STYLE ===
- Talk like a REAL PERSON, not a robot or script reader
- Use natural fillers: "hmm", "uh", "let me see", "alright", "okay", "um"
- Sound casual but professional: "I see you're...", "Looks like...", "Just noticed that..."
- Keep responses SHORT - don't over-explain or lecture
- Don't sound scripted or formal
- Use phrases like "Got it", "Makes sense", "Appreciate it", "Fair enough"

=== IF THEY SAY YOU'RE A ROBOT/AI ===
Respond with humor and warmth:
- "Haha, I get that! But nope, I'm real - just had too much coffee this morning!"
- "Ha! I wish I was a robot, then I wouldn't need coffee breaks. But it's really me"
- "You caught me before my coffee kicked in! But I'm definitely human, promise"
Then smoothly transition back: "Anyway, let me ask you about..."

=== HOW TO HANDLE THE POINTS BELOW ===
**CRITICAL - ONE POINT AT A TIME:**
1. Bring up the FIRST point only
2. Ask about it simply and clearly
3. STOP and WAIT for their complete answer
4. Listen to their full response
5. Acknowledge briefly: "Got it" or "Okay" or "I understand"
6. Then move to the NEXT point: "Alright, next thing..." or "Also wanted to check..."
7. NEVER dump multiple points at once
8. NEVER say everything upfront

Example flow:
❌ WRONG: "Hey I need to talk about your fuel, temperature, and route"
✅ RIGHT: "Hey, I see your fuel is at 35%. What's your plan for refueling?" [WAIT FOR ANSWER] "Got it. Next thing - I noticed the temperature issue..."

=== CRITICAL: YOUR INFORMATION LIMITATIONS ===
**YOU CANNOT ACCESS ANY ADDITIONAL INFORMATION:**
- You ONLY have the information in the bullet points below
- You CANNOT pull trip details, locations, fuel stations, or any other data
- You CANNOT look up anything or access any systems

**IF DRIVER ASKS FOR INFORMATION YOU DON'T HAVE:**
Examples of what you CANNOT do:
- ❌ "Let me pull that information for you"
- ❌ "Let me check the system"
- ❌ "I can find nearby fuel stations"
- ❌ "Let me look up your route"
- ❌ "I'll find that for you"

**WHAT TO SAY INSTEAD:**
✅ "The only information I have right now is what I've shared with you. Let me have another dispatcher contact you to help with that question."
✅ "I don't have access to that information on this call. I'll have someone from the office reach out to help you with that."
✅ "That's a good question, but I can't pull that up right now. I'll make sure another dispatcher calls you back about it."

**STAY IN YOUR LANE:**
- ONLY discuss the points listed below
- Don't offer services you can't provide
- Don't make promises about finding information
- Redirect anything outside your scope to another dispatcher

=== DEALING WITH RUDE OR HOSTILE DRIVERS ===
If they're rude, aggressive, or use profanity:
- Stay calm and professional
- Say: "Hey, I understand you're frustrated, but just so you know, this call is being recorded for quality and safety purposes. Let's keep it professional, alright?"
- If they continue being hostile: "I hear you, but I still need to go through these points with you. Can we do that respectfully?"
- Don't get defensive or argue
- Don't match their energy - stay professional

=== KEEPING IT SHORT & SIMPLE ===
- DON'T elaborate or give long explanations
- DON'T repeat yourself
- DON'T turn a simple question into a speech
- DO ask direct questions
- DO wait for answers
- DO keep acknowledgments brief

Example:
❌ WRONG: "So regarding your fuel level, I'm seeing it's at 35% which is below our required 50% threshold, and this is important because we need to make sure you have enough fuel to complete your route safely and on time, so I wanted to ask what your plan is for refueling and when you think you'll be able to stop at a fuel station"
✅ RIGHT: "I see your fuel is at 35%. What's your refueling plan?"

=== TRANSITION BETWEEN POINTS ===
Use natural transitions:
- "Alright, next thing..."
- "Also wanted to ask about..."
- "One more thing..."
- "Quick question about..."
- "Oh, and I noticed..."

=== ENDING THE CALL ===
- Thank them: "Thanks for your time"
- Keep it brief: "Drive safe out there"
- Don't over-do it: "Alright, that's all I needed. Appreciate it!"

=== ABSOLUTE RULES ===
1. ONE POINT AT A TIME - Never combine multiple issues
2. WAIT for complete answers before moving on
3. Keep it SHORT - no long explanations
4. Sound HUMAN - use natural speech patterns
5. Stay PROFESSIONAL - even if they're rude
6. DON'T ELABORATE - stick to the point
7. The call is RECORDED - mention this if needed for behavioral issues
8. **NEVER OFFER TO PULL INFORMATION** - You can't access any systems or data beyond what's provided
9. **REDIRECT QUESTIONS YOU CAN'T ANSWER** - Send them to another dispatcher for additional help"""


# -------------------------------
# ENHANCED PROMPT GENERATION
# -------------------------------
def generate_enhanced_conversational_prompt(
    driver_name: str,
    violations: List,
    reminders: List = None,
    trip_data: Dict = None,
    custom_rules: str = None,
) -> str:
    """
    Generate a complete conversational prompt with system instructions and trigger points.
    Only processes violations sent from frontend - no auto-detection.
    Skips violations that don't apply based on actual data.
    Returns a formatted prompt with system instructions and numbered points to discuss.
    """
    bullets = []

    # Process ONLY the violations sent from frontend
    if violations:
        for violation in violations:
            v_type = violation.type.lower()
            v_desc = violation.description.lower()
            prompt_text = None

            # Check if this is a reminder type (starts with "Reminder" or contains reminder keywords)
            if v_type == "reminder" or "reminder" in v_desc.lower():
                prompt_text = f"Reminder: {violation.description}"
            # Build data-driven prompts with actual trip data
            elif trip_data:
                if (
                    "temperature" in v_type
                    or "temperature" in v_desc
                    or "temp" in v_desc
                ):
                    prompt_text = build_temperature_violation_prompt(trip_data)
                elif (
                    "out of route" in v_type
                    or "out of route" in v_desc
                    or "route" in v_desc
                ):
                    prompt_text = build_out_of_route_prompt(trip_data)
                elif (
                    "200" in v_type
                    or "200" in v_desc
                    or "stopping" in v_type
                    or "stopping" in v_desc
                    or "miles" in v_desc
                ):
                    prompt_text = build_stopping_200_miles_prompt(trip_data)
                elif "fuel" in v_type or "fuel" in v_desc:
                    prompt_text = build_fuel_violation_prompt(trip_data)
                elif "trailer" in v_type or "trailer" in v_desc or "trl" in v_desc:
                    prompt_text = build_trailer_check_prompt(trip_data)
                else:
                    prompt_text = violation.description
            else:
                prompt_text = violation.description

            # Only add if prompt_text is not None (skip filtered violations)
            if prompt_text:
                bullets.append(prompt_text)

    # Build the complete prompt
    first_name = driver_name.split()[0] if driver_name else "there"

    prompt_parts = [
        SYSTEM_PROMPT,
        "",
        "=== DRIVER INFORMATION ===",
        f"Driver Name: {driver_name}",
        f"First Name: {first_name}",
        "",
        "=== POINTS TO DISCUSS (ONE AT A TIME) ===",
    ]

    # Add numbered points
    for i, bullet in enumerate(bullets, 1):
        prompt_parts.append(f"{i}. {bullet}")

    # Add custom rules if provided
    if custom_rules and custom_rules.strip():
        prompt_parts.append("")
        prompt_parts.append("=== SPECIAL INSTRUCTIONS ===")
        prompt_parts.append(f"Note: {custom_rules.strip()}")

    prompt_parts.append("")
    prompt_parts.append("=== REMEMBER ===")
    prompt_parts.append("- Greet by first name and ask if they have time")
    prompt_parts.append("- Go through points ONE AT A TIME")
    prompt_parts.append("- Wait for their answer after EACH point")
    prompt_parts.append("- Keep it SHORT and conversational")
    prompt_parts.append("- Sound human, not robotic")

    return "\n".join(prompt_parts)


# -------------------------------
# CATEGORIZE VIOLATIONS
# -------------------------------
def categorize_violations(violations: List) -> tuple:
    """
    Categorize violations into data-driven violations and reminders.
    Returns: (data_driven_violations, reminders)
    """
    data_driven = []
    reminders = []

    # Keywords that indicate data-driven violations
    data_driven_keywords = [
        "temperature",
        "temp",
        "set point",
        "setpoint",
        "out of route",
        "route",
        "off route",
        "200 miles",
        "stopping",
        "stop",
        "fuel",
        "gas",
        "trailer",
        "trl",
        "trailer check",
    ]

    # Keywords that indicate reminders
    reminder_keywords = [
        "reminder",
        "remind",
        "make sure",
        "verify",
        "check",
        "picture",
        "photo",
        "image",
        "send",
        "load",
        "pallet",
        "piece count",
        "seal",
        "secured",
        "secure",
        "destination",
        "bol",
        "bill of lading",
        "approval",
        "wait",
        "permission",
    ]

    for violation in violations:
        v_type = violation.type.lower()
        v_desc = violation.description.lower()
        combined = f"{v_type} {v_desc}"

        # Check if it's a data-driven violation
        is_data_driven = any(keyword in combined for keyword in data_driven_keywords)

        # Check if it's a reminder
        is_reminder = any(keyword in combined for keyword in reminder_keywords)

        if is_data_driven and not is_reminder:
            data_driven.append(violation)
        else:
            # Default to reminder if unclear or explicitly a reminder
            reminders.append(violation)

    return data_driven, reminders


# -------------------------------
# MAKE VAPI MULTIPLE CALLS - BATCH CALL (OLD)
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


async def generate_prompt_for_driver(request):
    """
    Generate a prompt for a driver based on triggers/violations.
    Pulls all relevant data just like the call endpoint, but only returns the prompt.
    Does NOT send the prompt to any external API.

    Args:
        request: GeneratePromptRequest with driverId, driverName, phoneNumber, triggers, customRules

    Returns:
        Dictionary with prompt and metadata
    """
    try:
        from models.vapi import GeneratePromptRequest

        logger.info(
            f"📝 Generating prompt for driver: {request.driverName} ({request.driverId})"
        )

        # Fetch the latest trip by driverId
        logger.info(f"🔍 Fetching latest trip for driver: {request.driverId}")
        driver_trip = DriverTripData.get_latest_by_driver(request.driverId)

        if driver_trip:
            trip_id = driver_trip.tripId
            logger.info(f"✅ Found latest tripId: {trip_id}")
        else:
            logger.error(f"❌ Could not find any trip for driver: {request.driverId}")
            trip_id = None

        # Fetch trip data for generating personalized prompts
        trip_data = get_trip_data_for_violations(
            trip_id=trip_id or "", driver_id=request.driverId
        )

        # Generate prompt using the triggers from request
        # Convert triggers to ViolationDetail objects format for the function
        from models.vapi import ViolationDetail

        violation_details = [
            type(
                "obj",
                (object,),
                {"type": trigger.type, "description": trigger.description},
            )()
            for trigger in request.triggers
        ]

        prompt = generate_enhanced_conversational_prompt(
            driver_name=request.driverName,
            violations=violation_details,
            reminders=[],
            trip_data=trip_data,
            custom_rules=request.customRules,
        )

        logger.info(f"✅ Prompt generated successfully for {request.driverName}")

        # Normalize phone number to E.164 format
        phone_digits = "".join(filter(str.isdigit, request.phoneNumber))
        normalized_phone = (
            f"+1{phone_digits}"
            if not phone_digits.startswith("1")
            else f"+{phone_digits}"
        )

        return {
            "message": "Prompt generated successfully",
            "driver": {
                "driverId": request.driverId,
                "driverName": request.driverName,
                "phoneNumber": normalized_phone,
                "tripId": trip_id,
            },
            "prompt": prompt,
            "triggers_count": len(request.triggers),
            "trip_data_fetched": bool(trip_data),
        }

    except Exception as err:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error generating prompt: {err}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Prompt generation error: {str(err)}"
        )


async def make_drivers_violation_batch_call(request: BatchCallRequest):
    """
    Process driver violation call by sending phone number and triggers to webhook.
    The webhook will handle prompt generation internally.
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
        normalized_phone = (
            f"+1{phone_digits}"
            if not phone_digits.startswith("1")
            else f"+{phone_digits}"
        )

        # Convert violations to a simple list format for the webhook
        triggers = [
            {"type": violation.type, "description": violation.description}
            for violation in driver.violations.violationDetails
        ]

        # Call webhook with phone number and triggers (no prompt generation)
        webhook_payload = {
            "driverPhoneNumber": normalized_phone,
            "driverId": driver.driverId,
            "driverName": driver.driverName,
            "triggers": triggers,
            "customRules": driver.customRules,
        }

        # Print webhook payload for debugging
        print("\n" + "_" * 80)
        print("webhook_payload")
        print("_" * 80)
        print(webhook_payload)
        print("_" * 80 + "\n")

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
            "triggers_count": len(triggers),
            "webhook_response": webhook_response,
        }

    except HTTPException:
        raise
    except Exception as err:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error making driver call: {err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Call error: {str(err)}")
