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
            stmt = select(cls).where(cls.primaryDriverId == driver_id).order_by(cls.tripId.desc()).limit(1)
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
    "fuel_lower_than_required"
}

REMINDER_VIOLATIONS = {
    "verify_load_pallet_count",
    "send_loaded_picture",
    "send_seal_pictures",
    "secure_load_pictures",
    "check_destination_bol",
    "wait_for_approval"
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
        if active_load and active_load.start_odometer_miles and active_load.current_odometer_miles:
            miles_driven = active_load.current_odometer_miles - active_load.start_odometer_miles

        # Get location from full trip data if available
        current_location = None
        if trip_full and hasattr(trip_full, 'samsaraLocation'):
            current_location = trip_full.samsaraLocation

        return {
            "trip_id": trip_id,
            "driver_id": driver_id,
            # Temperature data
            "ditat_set_point": driver_trip.ditatSetPoint,
            "current_temp_c": driver_trip.tempC,
            "current_temp_f": driver_trip.tempF,
            # Route data
            "out_of_route": driver_trip.outOfRoute,
            "sub_status": driver_trip.subStatusLabel,
            "current_location": current_location,
            # Fuel data
            "fuel_percent": driver_trip.fuelPercent,
            # Trailer check
            "trl_check": driver_trip.trlCheck,
            # Miles tracking
            "miles_driven": miles_driven,
            "start_odometer": active_load.start_odometer_miles if active_load else None,
            "current_odometer": active_load.current_odometer_miles if active_load else None,
        }
    except Exception as err:
        logger.error(f"Error fetching trip data: {err}", exc_info=True)
        return {}


# -------------------------------
# PERSONALIZED PROMPT BUILDERS
# -------------------------------
def build_temperature_violation_prompt(trip_data: Dict, is_first: bool = False) -> str:
    """Build prompt for temperature not equal to set point."""
    set_point = trip_data.get("ditat_set_point")
    current_temp = trip_data.get("current_temp_f")

    intro = "First thing" if is_first else "Next"

    if set_point is None or current_temp is None:
        return f"{intro}, I noticed the temperature isn't at the set point. Can you tell me what's going on?"

    return (
        f"{intro}, your temperature is not equal to the ditat set point. "
        f"Your ditat set point is {set_point}°F and your current vehicle temperature is {current_temp}°F. "
        f"Can you tell me the reason for this please so I can note it down?"
    )


def build_out_of_route_prompt(trip_data: Dict, is_first: bool = False) -> str:
    """Build prompt for driver out of route with actual location."""
    out_of_route = trip_data.get("out_of_route")
    current_location = trip_data.get("current_location")

    intro = "First thing" if is_first else "Next"

    if out_of_route == "🟢":
        # Driver is actually on route, this might be a false alert
        return f"{intro}, I wanted to check on your route status. Everything looks good on our end now."

    # Build prompt with location if available
    if current_location:
        return (
            f"{intro}, I have your current location which is {current_location} and you seem to be out of route. "
            f"Can you tell me the reason on why you chose a different path?"
        )
    else:
        return (
            f"{intro}, according to our system you seem to be out of route. "
            f"Can you tell me the reason on why you chose a different path?"
        )


def build_stopping_200_miles_prompt(trip_data: Dict, is_first: bool = False) -> str:
    """Build prompt for driver stopping within first 200 miles."""
    miles_driven = trip_data.get("miles_driven")

    intro = "First thing" if is_first else "Next"

    if miles_driven is not None:
        return (
            f"{intro}, I noticed you made a stop within the first 200 miles of your trip. "
            f"You've driven approximately {miles_driven:.1f} miles so far. "
            f"Can you tell me the reason for this stop?"
        )

    return (
        f"{intro}, I noticed you made a stop within the first 200 miles of your trip. "
        f"Can you tell me the reason for this stop?"
    )


def build_fuel_violation_prompt(trip_data: Dict, is_first: bool = False) -> str:
    """Build prompt for fuel lower than required percentage."""
    fuel_percent = trip_data.get("fuel_percent")
    required_fuel = REQUIRED_FUEL

    intro = "First thing" if is_first else "Next"

    if fuel_percent is None:
        return f"{intro}, I wanted to check on your fuel level. Can you let me know your current fuel percentage?"

    return (
        f"{intro}, I see your fuel level is at {fuel_percent}%, which is below the required {required_fuel}%. "
        f"Can you tell me your plan for refueling?"
    )


def build_trailer_check_prompt(trip_data: Dict, is_first: bool = False) -> str:
    """Build prompt for trailer check."""
    trl_check = trip_data.get("trl_check")

    intro = "First thing" if is_first else "Next"

    if trl_check == "🔴":
        return (
            f"{intro}, I noticed there's a trailer check alert. "
            f"Can you verify that everything is secure and in good condition with your trailer?"
        )

    return f"{intro}, please perform a trailer check and confirm everything is secure."


# -------------------------------
# SYSTEM PROMPT FOR AI BEHAVIOR (Configure this in VAPI)
# -------------------------------
SYSTEM_PROMPT = """You are a professional dispatcher calling a truck driver about their trip.

Start the call by:
1. Greeting them by name
2. Identifying yourself as their dispatcher
3. Briefly stating you have some information about their trip to discuss
4. Asking if they have a minute to talk and are in a safe place
5. WAIT for their response before proceeding with the topics below

Behavior rules:
- Be BRIEF and DIRECT - no long explanations
- After asking about EACH topic, WAIT COMPLETELY for the driver's full response
- DO NOT repeat yourself or summarize what was already said
- DO NOT say "let me recap" or "to summarize"
- Handle ONE topic at a time, waiting for driver's answer before moving to next
- If driver asks a question, answer it briefly then continue with your topics
- Keep tone natural, conversational, and professional
- Do not rush or interrupt the driver

The topics to discuss will be provided in the prompt. Go through them one by one."""


# -------------------------------
# ENHANCED PROMPT GENERATION
# -------------------------------
def generate_enhanced_conversational_prompt(
    driver_name: str,
    violations: List,
    reminders: List = None,
    trip_data: Dict = None
) -> str:
    """
    Generate an enhanced conversational prompt with actual data.
    Separates data-driven violations (with discussion) from reminders.
    Note: Greeting is handled by VAPI system prompt, this only contains the discussion topics.
    """
    first_name = driver_name.split()[0] if driver_name else "Driver"

    prompt_parts = []

    # No greeting here - it's in the system prompt configured in VAPI

    # Process violations with actual data
    if violations:
        violation_messages = []

        for idx, violation in enumerate(violations):
            is_first = (idx == 0)  # Track if this is the first violation
            v_type = violation.type.lower()
            v_desc = violation.description.lower()

            # Check both type and description for better matching
            if trip_data:
                # Use data-driven prompts when trip data is available
                if "temperature" in v_type or "temperature" in v_desc or "temp" in v_desc:
                    violation_messages.append(build_temperature_violation_prompt(trip_data, is_first))
                elif "out of route" in v_type or "out of route" in v_desc or "route" in v_desc:
                    violation_messages.append(build_out_of_route_prompt(trip_data, is_first))
                elif "200" in v_type or "200" in v_desc or "stopping" in v_type or "stopping" in v_desc or "miles" in v_desc:
                    violation_messages.append(build_stopping_200_miles_prompt(trip_data, is_first))
                elif "fuel" in v_type or "fuel" in v_desc:
                    violation_messages.append(build_fuel_violation_prompt(trip_data, is_first))
                elif "trailer" in v_type or "trailer" in v_desc or "trl" in v_desc:
                    violation_messages.append(build_trailer_check_prompt(trip_data, is_first))
                else:
                    # Generic violation message for any other type
                    intro = "First thing" if is_first else "Next"
                    violation_messages.append(f"{intro}, {violation.description}")
            else:
                # No trip data available, use generic descriptions
                intro = "First thing" if is_first else "Next"
                violation_messages.append(f"{intro}, {violation.description}")

        if violation_messages:
            prompt_parts.extend(violation_messages)

    # Add reminders section at the end - keep it brief
    if reminders and len(reminders) > 0:
        reminder_texts = ", ".join([r.description.lower().rstrip('.') for r in reminders])
        prompt_parts.append(f"Also, few reminders: {reminder_texts}.")

    # Join all parts
    user_prompt = " ".join(prompt_parts)

    # Return just the conversational prompt (system prompt will be sent separately)
    return user_prompt.strip()


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
        "temperature", "temp", "set point", "setpoint",
        "out of route", "route", "off route",
        "200 miles", "stopping", "stop",
        "fuel", "gas",
        "trailer", "trl", "trailer check"
    ]

    # Keywords that indicate reminders
    reminder_keywords = [
        "reminder", "remind", "make sure", "verify", "check",
        "picture", "photo", "image", "send",
        "load", "pallet", "piece count",
        "seal", "secured", "secure",
        "destination", "bol", "bill of lading",
        "approval", "wait", "permission"
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
def generate_conversational_prompt(driver_name: str, violations: List, custom_rules: str = "") -> str:
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
    transitions = ["Umm, I noticed", "So, checking the data", "Hmm, I see", "Alright, so"]

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


async def make_drivers_violation_batch_call(request: BatchCallRequest):
    """
    Process driver violation call with enhanced data-driven prompts.
    Fetches actual trip data and generates personalized prompts with real-time information.
    Note: Even though the request has a 'drivers' array, only ONE driver is sent per call.
    """
    try:
        # Get the first (and only) driver from the array
        if not request.drivers or len(request.drivers) == 0:
            raise HTTPException(status_code=400, detail="No driver data provided")

        driver = request.drivers[0]  # Only one driver per call

        logger.info(f"📞 Processing call for driver: {driver.driverName} ({driver.driverId})")

        # Normalize phone number to E.164 format
        phone_digits = "".join(filter(str.isdigit, driver.phoneNumber))
        normalized_phone = f"+1{phone_digits}" if not phone_digits.startswith("1") else f"+{phone_digits}"

        # Always fetch the latest trip by driverId (don't rely on frontend sending tripId)
        logger.info(f"🔍 Fetching latest trip for driver: {driver.driverId}")
        driver_trip = DriverTripData.get_latest_by_driver(driver.driverId)

        if driver_trip:
            trip_id = driver_trip.tripId
            logger.info(f"✅ Found latest tripId: {trip_id}")
        else:
            logger.error(f"❌ Could not find any trip for driver: {driver.driverId}")
            trip_id = None

        # Fetch trip data for generating personalized prompts
        trip_data = get_trip_data_for_violations(
            trip_id=trip_id or "",
            driver_id=driver.driverId
        )

        # Log the fetched trip data for debugging
        if trip_data:
            logger.info("✅ Trip data fetched successfully:")
            logger.info(f"   - Trip ID: {trip_data.get('trip_id')}")
            logger.info(f"   - Temperature Set Point: {trip_data.get('ditat_set_point')}°F")
            logger.info(f"   - Current Temperature: {trip_data.get('current_temp_f')}°F")
            logger.info(f"   - Fuel Percent: {trip_data.get('fuel_percent')}%")
            logger.info(f"   - Current Location: {trip_data.get('current_location')}")
            logger.info(f"   - Out of Route: {trip_data.get('out_of_route')}")
            logger.info(f"   - Miles Driven: {trip_data.get('miles_driven')}")
        else:
            logger.warning("⚠️ No trip data available - using generic prompts")

        # Categorize violations into data-driven vs reminders
        data_driven_violations, reminder_violations = categorize_violations(
            driver.violations.violationDetails
        )

        logger.info(f"📊 Found {len(data_driven_violations)} data-driven violations and {len(reminder_violations)} reminders")

        # Log details of each violation for debugging
        if data_driven_violations:
            logger.info("Data-driven violations:")
            for v in data_driven_violations:
                logger.info(f"  - Type: '{v.type}', Description: '{v.description}'")

        if reminder_violations:
            logger.info("Reminders:")
            for r in reminder_violations:
                logger.info(f"  - Type: '{r.type}', Description: '{r.description}'")

        # Generate enhanced conversational prompt with actual data
        prompt = generate_enhanced_conversational_prompt(
            driver_name=driver.driverName,
            violations=data_driven_violations,
            reminders=reminder_violations,
            trip_data=trip_data
        )

        # Add custom rules if provided
        if driver.customRules and driver.customRules.strip():
            prompt += f" Additionally: {driver.customRules.strip()}"

        logger.info(f"📞 Calling {driver.driverName} at {normalized_phone}")
        logger.info(f"📝 Generated Prompt ({len(prompt)} chars):")
        logger.info(f"{'='*80}")
        logger.info(prompt)
        logger.info(f"{'='*80}")

        # Call webhook
        webhook_payload = {
            "driverPhoneNumber": normalized_phone,
            "prompt": prompt
        }

        # Print the final payload being sent - FULL DETAILS
        print("\n" + "=" * 100)
        print("                    FINAL PAYLOAD TO BE SENT TO DRIVER                    ")
        print("=" * 100)
        print(f"\n📋 DRIVER INFORMATION:")
        print(f"   Name: {driver.driverName}")
        print(f"   Driver ID: {driver.driverId}")
        print(f"   Phone: {normalized_phone}")
        print(f"   Trip ID: {trip_id or 'NOT FOUND'}")

        print(f"\n📊 VIOLATIONS BREAKDOWN:")
        print(f"   Total Violations: {len(driver.violations.violationDetails)}")
        print(f"   Data-Driven (with actual data): {len(data_driven_violations)}")
        print(f"   Reminders (brief): {len(reminder_violations)}")

        if data_driven_violations:
            print(f"\n   Data-Driven Violations:")
            for idx, v in enumerate(data_driven_violations, 1):
                print(f"      {idx}. Type: '{v.type}' | Description: '{v.description}'")

        if reminder_violations:
            print(f"\n   Reminders:")
            for idx, r in enumerate(reminder_violations, 1):
                print(f"      {idx}. Type: '{r.type}' | Description: '{r.description}'")

        print(f"\n🗂️ TRIP DATA FETCHED:")
        print(f"   Trip Data Available: {'✅ Yes' if trip_data else '❌ No'}")
        if trip_data:
            print(f"   Current Location: {trip_data.get('current_location', 'N/A')}")
            print(f"   Temperature Set Point: {trip_data.get('ditat_set_point', 'N/A')}°F")
            print(f"   Current Temperature: {trip_data.get('current_temp_f', 'N/A')}°F")
            print(f"   Fuel Percent: {trip_data.get('fuel_percent', 'N/A')}%")
            print(f"   Out of Route: {trip_data.get('out_of_route', 'N/A')}")
            print(f"   Miles Driven: {trip_data.get('miles_driven', 'N/A')}")
            print(f"   Trailer Check: {trip_data.get('trl_check', 'N/A')}")

        if driver.customRules:
            print(f"\n📝 CUSTOM RULES: {driver.customRules}")

        print(f"\n🤖 SYSTEM PROMPT (Configure this in VAPI once):")
        print("-" * 100)
        print(SYSTEM_PROMPT)
        print("-" * 100)

        print(f"\n💬 CONVERSATIONAL PROMPT (Length: {len(prompt)} chars):")
        print("=" * 100)
        print(prompt)
        print("=" * 100)

        print(f"\n📦 WEBHOOK PAYLOAD:")
        print(f"   - driverPhoneNumber: {normalized_phone}")
        print(f"   - prompt: {len(prompt)} chars")
        print("=" * 100)
        print("✅ Payload ready to be sent!\n")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://vapi-ringcentral-bridge-181509438418.us-central1.run.app/api/webhook/call-driver",
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
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
                "tripId": trip_id,
            },
            "prompt": prompt,
            "promptLength": len(prompt),
            "violations_summary": {
                "total": len(driver.violations.violationDetails),
                "data_driven": len(data_driven_violations),
                "reminders": len(reminder_violations),
            },
            "trip_data_fetched": bool(trip_data),
            "trip_data": trip_data if trip_data else {},
            "webhook_response": webhook_response
        }

    except HTTPException:
        raise
    except Exception as err:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error making driver call: {err}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Call error: {str(err)}"
        )
