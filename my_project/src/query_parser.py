# src/query_parser.py
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import Dict, Any

# Common airport code mappings
CITY_TO_IATA = {
    'delhi': 'DEL', 'mumbai': 'BOM', 'bangalore': 'BLR', 'chennai': 'MAA',
    'kolkata': 'CCU', 'hyderabad': 'HYD', 'pune': 'PNQ', 'goa': 'GOI',
    'ajman': 'AJM', 'dubai': 'DXB', 'abu dhabi': 'AUH', 'sharjah': 'SHJ',
    'new york': 'JFK', 'london': 'LHR', 'paris': 'CDG', 'singapore': 'SIN'
}

def normalize_city(city: str) -> str:
    """Normalize city name and convert to IATA code"""
    city = city.lower().strip()
    
    # Handle common misspellings
    misspellings = {
        'delhee': 'delhi',
        'deli': 'delhi',
        'mumbi': 'mumbai',
        'bangalor': 'bangalore',
        'bangaluru': 'bangalore'
    }
    city = misspellings.get(city, city)
    
    return CITY_TO_IATA.get(city, city.upper()[:3])

def parse_date(date_text: str, current_date_str: str) -> str:
    """Parse relative or absolute dates"""
    current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
    date_text_lower = date_text.lower()
    
    # Relative dates
    if 'today' in date_text_lower:
        return current_date.strftime("%Y-%m-%d")
    elif 'tomorrow' in date_text_lower:
        return (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
    elif 'next' in date_text_lower:
        if 'monday' in date_text_lower:
            days_ahead = (0 - current_date.weekday() + 7) % 7 or 7
        elif 'tuesday' in date_text_lower:
            days_ahead = (1 - current_date.weekday() + 7) % 7 or 7
        elif 'wednesday' in date_text_lower:
            days_ahead = (2 - current_date.weekday() + 7) % 7 or 7
        elif 'thursday' in date_text_lower:
            days_ahead = (3 - current_date.weekday() + 7) % 7 or 7
        elif 'friday' in date_text_lower:
            days_ahead = (4 - current_date.weekday() + 7) % 7 or 7
        elif 'saturday' in date_text_lower:
            days_ahead = (5 - current_date.weekday() + 7) % 7 or 7
        elif 'sunday' in date_text_lower:
            days_ahead = (6 - current_date.weekday() + 7) % 7 or 7
        else:
            days_ahead = 7
        return (current_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Try parsing absolute date
    try:
        parsed = date_parser.parse(date_text, fuzzy=True)
        return parsed.strftime("%Y-%m-%d")
    except:
        return date_text

def parse_flight_query(query: str, current_date: str = None) -> Dict[str, Any]:
    """
    Parse natural language flight booking query
    """
    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")
    
    query_lower = query.lower()
    result = {
        "travel_intent": "one_way",
        "passengers": {"total": 0}
    }
    
    # Extract origin and destination
    route_patterns = [
        r'(?:from|leaving)s+([a-z]+)s+(?:to|for)s+([a-z]+)',
        r'([a-z]+)s+(?:to|for)s+([a-z]+)',
    ]
    
    for pattern in route_patterns:
        match = re.search(pattern, query_lower)
        if match:
            result['origin'] = normalize_city(match.group(1))
            result['destination'] = normalize_city(match.group(2))
            break
    
    # Detect round trip
    if any(word in query_lower for word in ['round trip', 'return', 'round-trip']):
        result['travel_intent'] = 'round_trip'
    
    # Extract date
    date_patterns = [
        r'ons+(nexts+w+|w+day|tomorrow|today|d{1,2}[/-]d{1,2}[/-]d{2,4})',
        r'(nexts+w+|w+day)',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, query_lower)
        if match:
            result['travel_date'] = parse_date(match.group(1), current_date)
            break
    
    # Extract time preference
    if 'morning' in query_lower:
        result['time_preference'] = 'morning'
    elif 'afternoon' in query_lower:
        result['time_preference'] = 'afternoon'
    elif 'evening' in query_lower:
        result['time_preference'] = 'evening'
    elif 'night' in query_lower:
        result['time_preference'] = 'night'
    
    # Extract passenger counts
    passengers = {}
    
    # Adult males
    male_patterns = [r'(d+)s*(?:adults*)?(?:male|man|men)', r'(d+)s*men']
    for pattern in male_patterns:
        match = re.search(pattern, query_lower)
        if match:
            passengers['adult_male'] = int(match.group(1))
            break
    
    # Adult females
    female_patterns = [r'(d+)s*(?:adults*)?(?:female|woman|women)', r'(d+)s*women']
    for pattern in female_patterns:
        match = re.search(pattern, query_lower)
        if match:
            passengers['adult_female'] = int(match.group(1))
            break
    
    # Minors
    minor_patterns = [
        r'(d+)s*(?:females*)?minor',
        r'(d+)s*(?:males*)?minor',
        r'(d+)s*(?:child|children|kid)',
    ]
    for pattern in minor_patterns:
        match = re.search(pattern, query_lower)
        if match:
            count = int(match.group(1))
            if 'female' in query_lower and 'minor' in query_lower:
                passengers['minor_female'] = count
            elif 'male' in query_lower and 'minor' in query_lower:
                passengers['minor_male'] = count
            else:
                passengers['minor'] = passengers.get('minor', 0) + count
            break
    
    # Calculate total
    passengers['total'] = sum(v for k, v in passengers.items() if k != 'total')
    
    if passengers['total'] == 0:
        passengers['adult_male'] = 1
        passengers['total'] = 1
    
    result['passengers'] = passengers
    
    return result