# src/nlp_extractor.py
import re
from typing import Dict, Any


def extract_passenger_info(text: str) -> dict:
    passengers = {}

    # Adult males
    match = re.search(r'(\d+)\s*(?:adult\s*)?(?:men|man|male)', text, re.IGNORECASE)
    if match:
        passengers["adult_male"] = int(match.group(1))

    # Adult females
    match = re.search(r'(\d+)\s*(?:adult\s*)?(?:women|woman|female)', text, re.IGNORECASE)
    if match:
        passengers["adult_female"] = int(match.group(1))

    # Minor females
    match = re.search(r'(\d+)\s*female\s*minor', text, re.IGNORECASE)
    if match:
        passengers["minor_female"] = int(match.group(1))

    # Minor males
    match = re.search(r'(\d+)\s*male\s*minor', text, re.IGNORECASE)
    if match:
        passengers["minor_male"] = int(match.group(1))

    # Generic minors
    match = re.search(r'(\d+)\s*(kids|children|child|minor)', text, re.IGNORECASE)
    if match:
        passengers["minor"] = int(match.group(1))

    # Total
    if passengers:
        passengers["total"] = sum(v for v in passengers.values())

    return passengers


def extract_entities(text: str) -> Dict[str, Any]:
    entities = {}

    # ---------------------
    # NAME
    # ---------------------
    name_patterns = [
        r'(?:Name|Passenger|Customer)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?:Mr|Mrs|Ms|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities['name'] = match.group(1).strip()
            break

    # ---------------------
    # DATE
    # ---------------------
    date_patterns = [
        r'\b(\d{4}-\d{2}-\d{2})\b',              # YYYY-MM-DD
        r'\b(\d{2}/\d{2}/\d{4})\b',              # DD/MM/YYYY
        r'\b(\d{2}-\d{2}-\d{4})\b',              # DD-MM-YYYY
        r'(?:Date|Travel|Departure)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            entities['date'] = match.group(1)
            break

    # ---------------------
    # AMOUNT
    # ---------------------
    amount_patterns = [
        r'[₹$]\s*([\d,]+(?:\.\d{2})?)',
        r'(?:Amount|Total|Price|Fare)[:\s]+[₹$]?\s*([\d,]+(?:\.\d{2})?)',
        r'(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)'
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities['amount'] = match.group(1).strip()
            break

    # ---------------------
    # BOOKING ID / PNR
    # ---------------------
    pnr_patterns = [
        r'PNR[:\s]+([A-Z0-9]{6,10})',
        r'Booking[:\s]+([A-Z0-9]{6,12})',
        r'ID[:\s]+([A-Z0-9]{6,12})',
        r'\b([A-Z0-9]{6})\b',
    ]
    for pattern in pnr_patterns:
        match = re.search(pattern, text)
        if match:
            entities['booking_id'] = match.group(1)
            break

    # ---------------------
    # ROUTE (natural language)
    # Example: "Delhee to Ajman"
    # ---------------------
    route_pattern = r'([A-Za-z]+)\s+to\s+([A-Za-z]+)'
    route_match = re.search(route_pattern, text, re.IGNORECASE)
    if route_match:
        entities['origin'] = route_match.group(1).strip()
        entities['destination'] = route_match.group(2).strip()
        entities['route'] = f"{entities['origin']}-{entities['destination']}"

    # ---------------------
    # PASSENGERS
    # ---------------------
    passenger_data = extract_passenger_info(text)
    if passenger_data:
        entities['passengers'] = passenger_data

    return entities
