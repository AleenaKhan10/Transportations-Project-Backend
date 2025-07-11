import datetime
from config import settings
from helpers.utils import dump_json
from providers.ditat import DitatAPI

ditat_api = DitatAPI(settings.DITAT_TOKEN)

def ingest_ditat_data():
    df = ditat_api.get_dispatch_board()
    df["fromAddress"] = df["fromAddress"].apply(dump_json)
    df["toAddress"] = df["toAddress"].apply(dump_json)
    df["legToAddress"] = df["legToAddress"].apply(dump_json)
    df["ingestedAt"] = datetime.datetime.now(tz=datetime.timezone.utc)
    df = df[
        [
            "tripSummaryKey", "updateCounter", "tripKey", "tripId", "status", "subStatus", "carrierKey", "carrierId", "primaryDriverKey", 
            "primaryDriverId", "secondaryDriverKey", "secondaryDriverId", "truckKey", "truckId", "primaryTrailerKey", "primaryTrailerId", 
            "dispatchedBy", "dispatchedByUserName", "customerKey", "customerId", "customerName", "primaryShipmentKey", "primaryShipmentId", 
            "equipmentTypeKey", "equipmentTypeId", "totalWeight", "totalUnitsCount", "totalPalletsCount", "totalVolume", "emptyDrivingDistance", 
            "loadedDrivingDistance", "extraStopCount", "fromZoneKey", "fromStopNumber", "fromIsAppointmentRequired", "fromIsAppointmentSet", 
            "fromArriveOnLocal", "fromLateWhenAfterLocal", "fromIsDropAndHook", "fromArrivedOnLocal", "fromDepartedOnLocal", "fromAddress", "toZoneKey", 
            "toStopNumber", "toIsAppointmentRequired", "toIsAppointmentSet", "toArriveOnLocal", "toLateWhenAfterLocal", "toIsDropAndHook", "toArrivedOnLocal", 
            "toDepartedOnLocal", "toAddress", "legToZoneKey", "legToTripStopNumber", "legToCurrentlyAtAccordingToCheckCall", "legToIsAppointmentRequired", 
            "legToIsAppointmentSet", "legToArriveOnLocal", "legToLateWhenAfterLocal", "legToIsDropAndHook", "legToArrivedOnLocal", "legToDepartedOnLocal", 
            "legToAddress", "legDrivingDistance", "gpsDeviceAssignedTo", "gpsPingOn", "gpsPositionDescription", "etaType", "etaConfidence", "etaLocalTime", 
            "etaRemainingLegDrivingDistanceFromGPS", "etaRemainingLegAirDistanceFromGPS", "etaRemainingLegDrivingDistance", "etaNotes", "wrnMissingAppointment", 
            "gpsSpeed", "pendingCheckCallExists", "referenceId1", "referenceId2", "referenceId3", "referenceId4", 
            "referenceId5", "reeferTemperature", "reeferMode", "actualReeferSetTemperature", "actualReeferReturnTemperature", "actualReeferMode", 
            "actualReeferUpdatedOn", "fromLocationId", "toLocationId", "legToLocationId",  "truckIssues", "primaryDriverIssues", "secondaryDriverIssues", 
            "primaryTrailerIssues", "assignmentsStatus", "assignmentsStatusInfo", "isHazmat", "hazmatDocumentationSavedOn", "bookedBy", "bookedByUserName", 
            "hasAgentAssignment", "isDeleted", "trackRequestStatus", "trackRequestStatusInfo", "totalPayAmount", "totalAdjustedRevenueAmount", "priority", 
            "lastTripNote", "dispatchNote1", "dispatchNote2", "dispatchNote3", "dispatchNote4", "dispatchNote5",
        ]
    ]
    df.to_gbq(
        destination_table="bronze.ditat_full",
        project_id="agy-intelligence-hub",
        if_exists="append" or "replace",
    )
    return {"status": "success"} 