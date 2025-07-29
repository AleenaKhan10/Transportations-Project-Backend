import re
from typing import Optional, Dict, Any


def extract_insights(transcript: str) -> Dict[str, Any]:
    """
    Extract insights from call transcript
    
    Args:
        transcript: The call transcript text
        
    Returns:
        Dictionary containing extracted insights
    """
    lower_transcript = transcript.lower()
    
    def get_match(pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
        """Helper function to extract regex matches"""
        match = re.search(pattern, transcript, flags)
        return match.group(1).strip() if match else None
    
    # Extract current location
    current_location = get_match(r'(?:near|around|close to)\s([A-Z][a-zA-Z\s]+)')
    
    # Extract miles remaining
    miles_remaining = get_match(r'about\s(\d+)\s*miles')
    
    # Extract ETA
    eta = get_match(r'(?:eta.*?|arrive.*?at|pickup.*?at)\s*([0-9]{1,2}[:\s]?[0-9]{2}\s*(?:am|pm)?)')
    
    # Determine on-time status
    if re.search(r'delay|late|behind schedule', lower_transcript):
        on_time_status = "Delayed"
    elif re.search(r'on time|right on schedule', lower_transcript):
        on_time_status = "On Time"
    else:
        on_time_status = "Unknown"
    
    # Extract delay reason
    delay_reason = (
        get_match(r'delay(?:ed)? (?:due to|because of)\s+(.*?)(?:\.|,|$)') or
        get_match(r'\b(heavy traffic|road block|weather|accident|construction|police activity|detour|mechanical issue|closed road|jammed traffic)\b')
    )
    
    # Extract driver mood
    driver_mood = get_match(r'(?:i\'?m|i am|feeling)\s+(good|okay|fine|tired|bad|sick)')
    
    # Extract preferred callback time
    preferred_callback_time = get_match(r'call (?:me)? back (?:at|around)?\s*(\d{1,2}[:\s]?\d{2}\s*(am|pm)?)')
    
    # Check if driver wants text instead
    wants_text_instead = bool(re.search(r'text you instead|can you text', lower_transcript))
    
    # Extract reported issues
    issue_reported = get_match(r'issue with (.*?)\.?')
    
    # Extract weather condition
    weather_condition = get_match(r'weather is (.*?)\.?')
    
    # Extract road condition
    road_condition = get_match(r'road(?:s)? are (.*?)\.?')
    
    return {
        "currentLocation": current_location,
        "milesRemaining": int(miles_remaining) if miles_remaining and miles_remaining.isdigit() else None,
        "eta": eta,
        "onTimeStatus": on_time_status,
        "delayReason": delay_reason,
        "driverMood": driver_mood,
        "preferredCallbackTime": preferred_callback_time,
        "wantsTextInstead": wants_text_instead,
        "issueReported": issue_reported,
        "weatherCondition": weather_condition,
        "roadCondition": road_condition,
    }