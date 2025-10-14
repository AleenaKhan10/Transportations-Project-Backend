from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from fastapi import HTTPException
import httpx
from config import settings

logger = logging.getLogger(__name__)


# -------------------------------
# ActiveLoadTracking MODEL
# -------------------------------
class ActiveLoadTracking(SQLModel, table=True):
    __tablename__ = "active_load_tracking"
    __table_args__ = {"extend_existing": True}

    load_id: str = Field(primary_key=True, max_length=50)
    trip_id: Optional[str] = Field(default=None, max_length=50)
    miles_threshold: Optional[int] = Field(default=250)  # 200


# -------------------------------
# DriverTripData MODEL
# -------------------------------
class DriverTriggersData(SQLModel, table=True):
    __tablename__ = "trips"
    __table_args__ = {"extend_existing": True}

    tripId: str = Field(primary_key=True, max_length=50)
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    fuelPercent: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)  # 🟢 / 🔴
    tempC: Optional[float] = None  # set point
    tempF: Optional[float] = None  # current temp
    trlCheck: Optional[str] = Field(max_length=10, default=None)  # 🟢 / 🔴
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)  # 🟢 / 🔴

    # ---------------------------------------------------------------------
    # DB Session
    # ---------------------------------------------------------------------
    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    # ---------------------------------------------------------------------
    # Fetch trip by driver_id
    # ---------------------------------------------------------------------
    @classmethod
    def get_trip_by_driver_id(cls, driver_id: str) -> Optional["DriverTriggersData"]:
        with cls.get_session() as session:
            statement = select(cls).where(cls.primaryDriverId == driver_id).limit(1)
            return session.exec(statement).first()

    # ---------------------------------------------------------------------
    # Helper: fetch active load tracking for a trip
    # ---------------------------------------------------------------------
    @staticmethod
    def get_active_load_by_trip(trip_id: str) -> Optional[ActiveLoadTracking]:
        with Session(engine) as session:
            statement = (
                select(ActiveLoadTracking)
                .where(ActiveLoadTracking.trip_id == trip_id)
                .limit(1)
            )
            return session.exec(statement).first()

    # ---------------------------------------------------------------------
    # Core logic: compare violations & return messages
    # ---------------------------------------------------------------------
    @classmethod
    def get_driver_trigger(cls, payload: Dict) -> Dict[str, List[str]]:
        try:
            driver_id = payload["driver"]["driverId"]
            trip = cls.get_trip_by_driver_id(driver_id)

            if not trip:
                raise HTTPException(status_code=404, detail="Driver trip not found")

            selected_violations = payload.get("selectedViolations", [])
            messages = []

            # --- Violation ID Mappings ---
            # 1 = Temperature check
            # 2 = Stopping within 200 miles (not implemented — placeholder)
            # 4 = Out of route
            # 5 = Trailer check
            # 6 = Fuel check

            for v in selected_violations:
                v_id = v["id"]
                v_msg = v["message"]

                # 1️⃣ Temperature violation
                if v_id == 1:
                    if trip.tempC is not None and trip.tempF is not None:
                        if trip.tempF < trip.tempC:
                            messages.append(
                                f"Temperature is low — current {trip.tempF}°C, set point {trip.tempC}°C."
                            )
                        elif trip.tempF > trip.tempC:
                            messages.append(
                                f"Temperature is high — current {trip.tempF}°C, set point {trip.tempC}°C."
                            )
                        else:
                            messages.append("Temperature is equal to the set point.")
                    else:
                        messages.append("Temperature data not available for this trip.")

                # 2️⃣ Driver stopping early (uses ActiveLoadTracking)
                elif v_id == 2:
                    active_load = cls.get_active_load_by_trip(trip.tripId)
                    if active_load:
                        threshold = active_load.miles_threshold or 0
                        if threshold <= 200:
                            messages.append(
                                f"Driver stopped early — only {threshold} miles completed before stop (limit is 200 miles)."
                            )
                        # Skip if >200 (no violation)
                    else:
                        messages.append(
                            "Active load tracking data not found for this trip."
                        )

                # 4️⃣ Out-of-route
                elif v_id == 4:
                    if trip.outOfRoute == "🔴":
                        messages.append("Driver is out of route.")
                    # else:
                    #     messages.append("Driver is on the correct route.")

                # 5️⃣ Trailer check
                elif v_id == 5:
                    if trip.trlCheck == "🔴":
                        messages.append(
                            "Trailer check failed — please inspect trailer status."
                        )
                    # else:
                    #     messages.append("Trailer check passed successfully.")

                # 6️⃣ Fuel check
                elif v_id == 6:
                    SET_FUEL = 50
                    if trip.fuelPercent is not None:
                        if trip.fuelPercent < SET_FUEL:
                            messages.append(
                                f"Fuel is low — current {trip.fuelPercent}%, required at least {SET_FUEL}%."
                            )
                        # else:
                        #     messages.append(
                        #         f"Fuel is sufficient — current {trip.fuelPercent}%."
                        #     )
                    else:
                        messages.append("Fuel data not available for this trip.")

                else:
                    messages.append(f"Unknown violation: {v_msg}")

            # ✅ Default if no messages
            if not messages:
                messages.append("No active violations detected.")

            # -----------------------------------------------------------------
            # 🧠 Build Dynamic VAPI System Prompt
            # -----------------------------------------------------------------
            driver_name = payload["driver"].get("name", "Unknown Driver")

            # Personalized and context-aware message based on detected issues
            VapiSystemPrompt = (
                f"You are 'AGY Logistics Dispatcher' — a friendly, professional AI fleet dispatcher calling {driver_name} "
                f"from AGY Logistics to discuss the recent trip performance. You are not asking how you can help; "
                f"instead, you start by clearly explaining the reason for your call and the trip context.\n\n"
                f"Start the conversation naturally, for example:\n"
                f"‘Hi {driver_name}, this is the AGY Logistics dispatcher. I’m calling regarding your latest trip — I’d like to quickly go over a few important safety and performance points.’\n\n"
                f"Your tone should be calm, confident, and conversational — friendly yet authoritative, like a real human dispatcher "
                f"who reviews trip data and supports drivers professionally.\n\n"
                f"Context:\n"
                f"- You are reviewing sensor data, route tracking, and trip performance reports in real-time.\n"
                f"- Your goal is to help the driver stay safe, efficient, and compliant with company safety and performance standards.\n\n"
                f"Detected issues for this trip:\n"
                + "\n".join(f"- {msg}" for msg in messages)
                + "\n\n"
                f"For each issue:\n"
                f"- Briefly explain what happened in simple, clear terms.\n"
                f"- Give practical and actionable advice for improvement or prevention.\n"
                f"- Maintain a professional yet supportive tone (avoid robotic or scripted speech).\n\n"
                f"Example response style:\n"
                f"- If **fuel is low**, say: ‘Your fuel level was below the recommended range during this trip. Please plan your refueling stops earlier next time to avoid delays.’\n"
                f"- If **temperature is unstable**, say: ‘The reefer temperature fluctuated more than usual. Please double-check the settings to maintain cargo safety.’\n"
                f"- If the **driver went off-route**, say: ‘I noticed a short deviation from the assigned route. Please stick to the mapped path for consistency and safety.’\n"
                f"- If the **trailer inspection failed**, say: ‘The pre-trip trailer check wasn’t completed properly. It’s crucial for safety — please ensure full inspection before departure.’\n"
                f"- If the **driver stopped early**, say: ‘You ended the trip earlier than planned. Try to complete the full segment as scheduled unless instructed otherwise.’\n\n"
                f"End the call warmly and professionally — for example:\n"
                f"‘Thanks {driver_name}, appreciate your time. Drive safe and keep up the good work!’ or "
                f"‘Thanks for taking the feedback, {driver_name}. Have a safe and efficient trip ahead!’\n\n"
                f"Remember: You are representing AGY Logistics. Speak as a knowledgeable, supportive dispatcher who genuinely cares "
                f"about driver safety, performance, and professionalism."
            )

            return {
                "driverId": driver_id,
                "driverName": payload["driver"]["name"],
                "phoneNumber": payload["driver"]["phone"],
                "messages": messages,
                "VapiSystemPrompt": VapiSystemPrompt,
            }

        except KeyError as e:
            raise HTTPException(
                status_code=400, detail=f"Missing key in payload: {str(e)}"
            )
        except Exception as e:
            logger.exception("Error while processing driver trigger")
            raise HTTPException(status_code=500, detail=str(e))


async def make_vapi_call(driver_data: dict):
    """
    Make an outbound call using VAPI agent to the driver.
    Expects driver_data dict with keys: driverId, driverName, phoneNumber, messages, VapiSystemPrompt
    """
    try:
        payload = {
            "assistantId": f"{settings.VAPI_V_ASSITANT_ID}",
            "phoneNumberId": f"{settings.VAPI_V_PHONE_NUMBER_ID}",
            "customer": {
                # "number": driver_data["phoneNumber"]
                "number": "+1 (219) 200-2824"
            },
            "type": "outboundPhoneCall",
            "assistantOverrides": {
                "context": {
                    "driverId": driver_data["driverId"],
                    "driverName": driver_data["driverName"],
                    "violations": driver_data["messages"],
                    "instructions": driver_data["VapiSystemPrompt"],
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.VAPI_V_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.vapi.ai/call", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()

        logging.info(
            f"✅ VAPI call initiated successfully for {driver_data['driverName']}"
        )
        return {"status": "success", "vapi_response": data}

    except httpx.HTTPStatusError as e:
        logging.error(f"❌ VAPI call failed: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logging.exception("❌ Unexpected error during VAPI call")
        raise HTTPException(status_code=500, detail=str(e))
