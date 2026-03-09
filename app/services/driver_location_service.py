import os
import httpx
import urllib.parse
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["driver_location_service"])

# API key ko environment variables se uthana best practice hay
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

@router.get("/routes/navigation-guide")
async def get_navigation_and_places(
    lat: float = Query(..., description="Driver's current latitude"),
    lng: float = Query(..., description="Driver's current longitude"),
    query: str = Query(..., description="What the driver is looking for (e.g., 'Lockport', 'repair shop', 'food')")
):
    """
    Dynamic routing and POI search using TomTom Fuzzy Search.
    """
    # 1. Query ko URL-safe format mein convert karna (e.g., "repair shop" -> "repair%20shop")
    encoded_query = urllib.parse.quote(query)
    
    # 2. Ab URL mein encoded_query use karein taake string break na ho
    url = f"https://api.tomtom.com/search/2/search/{encoded_query}.json"
    
    params = {
        "key": TOMTOM_API_KEY,
        "lat": lat,
        "lon": lng,
        "radius": 50000,  # 50km ka radius taake doosri city bhi cover ho jaye
        "limit": 1        # Sirf sab se best match uthayenge
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        
    if response.status_code != 200:
        # Ab agar error ayega tou exact TomTom ka reason terminal aur Swagger dono mein nazar ayega
        raise HTTPException(
            status_code=response.status_code, 
            detail=f"Map API error. TomTom responded with: {response.text}"
        )
        
    data = response.json()
    
    # Agar radius mein koi match na mile
    if not data.get("results"):
        return {
            "success": False,
            "agent_message": f"I'm sorry, I couldn't find any results for '{query}' near your location."
        }
        
    # Sab se pehla/qareeb tareen result extract karna
    result = data["results"][0]
    
    # Agar POI (Point of Interest) hay tou uska naam, warna City/Municipality ka naam
    name = result.get("poi", {}).get("name") or result.get("address", {}).get("municipality", query)
    
    # Proper formatted address (freeformAddress TomTom ka best feature hay)
    address = result.get("address", {}).get("freeformAddress", "Unknown Address")
    
    # Distance calculate karna
    distance_meters = result.get("dist", 0)
    distance_miles = round(distance_meters / 1609.34, 1)
    
    # Final response jo ElevenLabs agent natural way mein parhega
    return {
        "success": True,
        "agent_message": f"I found {name} for you. It is located at {address}, which is about {distance_miles} miles away from your current location."
    }
