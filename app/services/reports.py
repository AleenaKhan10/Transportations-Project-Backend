from typing import List
from fastapi import APIRouter, HTTPException, Depends
from helpers import logger
from logic.auth.security import get_current_user
from models.driver_reports import DriverReport, DriverMorningReport
from models.drivers import Driver


router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@router.get("/driver-reports")
async def get_all_driver_reports():
    """
    Get all driver reports ordered by report date descending
    """
    try:
        reports = DriverReport.get_all(limit=5000)
        
        return {
            "status": 200,
            "message": "Driver reports fetched successfully",
            "data": [report.model_dump() for report in reports],
        }
        
    except Exception as error:
        logger.error(f"Error fetching reports: {str(error)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": 500,
                "message": "Failed to fetch driver reports",
                "data": None,
                "error": str(error),
            }
        )


@router.get("/morning-reports")
async def get_driver_morning_reports():
    """
    Get all driver morning reports with associated driver information
    """
    try:
        morning_reports = DriverMorningReport.get_all(limit=5000)
        
        # Get associated driver information for each report
        reports_with_drivers = []
        for report in morning_reports:
            report_dict = report.model_dump()
            
            # Get associated driver
            if report.driverIdPrimary:
                driver = Driver.get_by_id(report.driverIdPrimary)
                if driver:
                    report_dict["driver"] = driver.model_dump()
                else:
                    report_dict["driver"] = None
            else:
                report_dict["driver"] = None
                
            reports_with_drivers.append(report_dict)
        
        return {
            "status": 200,
            "count": len(reports_with_drivers),
            "message": "Morning Reports fetched successfully",
            "data": reports_with_drivers,
        }
        
    except Exception as error:
        logger.error(f"Error fetching morning reports: {str(error)}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "status": 500,
                "message": "Failed to fetch driver morning reports",
                "data": None,
                "error": str(error),
            }
        )