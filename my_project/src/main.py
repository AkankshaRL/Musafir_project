from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import tempfile
import os
import uuid
from datetime import datetime
 
from preprocessing import preprocess_image
from ocr_engine import extract_text_from_image
from frame_processor import process_dynamic_image
from nlp_extractor import extract_entities
from query_parser import parse_flight_query
 
app = FastAPI(title="OCR & NLP Processing System", version="1.0.0")
 
# In-memory storage for demo
extracted_data = {}
 
class QuestionRequest(BaseModel):
    file_id: str
    question: str
 
class FlightQueryRequest(BaseModel):
    query: str
    current_date: Optional[str] = None
 
@app.get("/")
async def root():
    return {
        "message": "OCR & NLP Processing System",
        "endpoints": ["/extract", "/ask", "/parse-flight-query"]
    }
 
@app.post("/extract")
async def extract_endpoint(file: UploadFile = File(...)):
    """
    Extract text and entities from static or dynamic images
    """
    try:
        file_id = str(uuid.uuid4())
       
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
       
        # Determine file type
        ext = file.filename.lower().split('.')[-1]
        is_dynamic = ext in ['gif', 'mp4', 'avi']
       
        result = {
            "file_id": file_id,
            "filename": file.filename,
            "type": "dynamic" if is_dynamic else "static",
            "timestamp": datetime.now().isoformat()
        }
       
        if is_dynamic:
            # Process dynamic image
            dynamic_result = process_dynamic_image(tmp_path)
            result.update(dynamic_result)
        else:
            # Process static image
            preprocessing_result = preprocess_image(tmp_path)
            ocr_result = extract_text_from_image(preprocessing_result['processed_path'])
            entities = extract_entities(ocr_result['text'])
           
            result.update({
                "preprocessing": preprocessing_result,
                "ocr": ocr_result,
                "entities": entities
            })
       
        # Store for Q&A
        extracted_data[file_id] = result
       
        # Cleanup
        os.unlink(tmp_path)
        if 'processed_path' in result.get('preprocessing', {}):
            if os.path.exists(result['preprocessing']['processed_path']):
                os.unlink(result['preprocessing']['processed_path'])
       
        return JSONResponse(content=result)
       
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
@app.post("/ask")
async def ask_endpoint(request: QuestionRequest):
    """
    Answer questions about extracted content
    """
    if request.file_id not in extracted_data:
        raise HTTPException(status_code=404, detail="File ID not found")

    data = extracted_data[request.file_id]
    question_lower = request.question.lower()

    # Simple rule-based QA
    answer = None
    source = None

    entities = data.get('entities', {}) or data.get('merged_entities', {})

    # ----- Amount / Price / Total money -----
    if 'amount' in question_lower or 'total' in question_lower and any(k in question_lower for k in ['price', 'amount', 'fare']):
        if 'amount' in entities:
            answer = f"The amount is {entities['amount']}."
            source = f"Amount found: {entities['amount']}"

    # ----- Name -----
    elif 'name' in question_lower:
        if 'name' in entities:
            answer = f"The name is {entities['name']}."
            source = f"Name found: {entities['name']}"

    # ----- Date / When -----
    elif 'date' in question_lower or 'when' in question_lower:
        if 'date' in entities:
            answer = f"The date is {entities['date']}."
            source = f"Date found: {entities['date']}"

    # ----- PNR / Booking / ID -----
    elif 'pnr' in question_lower or 'booking' in question_lower or 'id' in question_lower:
        for key in entities.keys():
            if 'pnr' in key.lower() or 'id' in key.lower() or 'booking' in key.lower():
                answer = f"The {key} is {entities[key]}."
                source = f"{key}: {entities[key]}"
                break

    # ----- Passenger-specific logic (adult/male/female/minor/total) -----
    if not answer:
        passengers = entities.get('passengers', {}) if isinstance(entities.get('passengers', {}), dict) else {}

        # asking for adult males specifically
        if 'adult' in question_lower and 'male' in question_lower:
            if 'adult_male' in passengers:
                answer = f"There are {passengers['adult_male']} adult males."
                source = f"adult_male: {passengers['adult_male']}"

        # asking for adult females specifically
        elif 'adult' in question_lower and 'female' in question_lower:
            if 'adult_female' in passengers:
                answer = f"There are {passengers['adult_female']} adult females."
                source = f"adult_female: {passengers['adult_female']}"

        # generic 'how many adults' -> sum adult_male + adult_female if available
        elif 'how many adults' in question_lower or ('how many' in question_lower and 'adult' in question_lower):
            male = passengers.get('adult_male', 0)
            female = passengers.get('adult_female', 0)
            total_adults = male + female
            if total_adults > 0:
                answer = f"There are {total_adults} adults ({male} male, {female} female)."
                source = f"adult_male: {male}, adult_female: {female}"

        # minors specific
        elif 'minor' in question_lower or 'child' in question_lower or 'children' in question_lower or 'kid' in question_lower:
            # ask male/female minors
            if 'male' in question_lower and 'minor' in question_lower and 'minor_male' in passengers:
                answer = f"There are {passengers['minor_male']} male minors."
                source = f"minor_male: {passengers['minor_male']}"
            elif 'female' in question_lower and 'minor' in question_lower and 'minor_female' in passengers:
                answer = f"There are {passengers['minor_female']} female minors."
                source = f"minor_female: {passengers['minor_female']}"
            else:
                # generic minors total
                minors_total = passengers.get('minor', 0) + passengers.get('minor_male', 0) + passengers.get('minor_female', 0)
                if minors_total > 0:
                    answer = f"There are {minors_total} minors."
                    source = f"minors_total: {minors_total}"

        # total passengers
        elif 'total' in question_lower and 'passeng' in question_lower or 'how many passengers' in question_lower or ('total' in question_lower and 'pax' in question_lower):
            if 'total' in passengers:
                answer = f"Total passengers are {passengers['total']}."
                source = f"total: {passengers['total']}"
            else:
                # fallback to sum of known passenger counts
                total_sum = sum(v for k, v in passengers.items() if isinstance(v, int) and k != 'total')
                if total_sum > 0:
                    answer = f"Total passengers (inferred) are {total_sum}."
                    source = f"inferred_total: {total_sum}"

    # ----- Final fallback: return all entities or no data -----
    if not answer:
        if entities:
            answer = f"Found information: {', '.join([f'{k}: {v}' for k, v in entities.items()])}"
            source = "All extracted entities"
        else:
            answer = "No relevant information found for this question."
            source = "No data"

    return {
        "file_id": request.file_id,
        "question": request.question,
        "answer": answer,
        "source": source
    }

 
@app.post("/parse-flight-query")
async def parse_flight_query_endpoint(request: FlightQueryRequest):
    """
    Parse natural language flight booking query
    """
    try:
        current_date = request.current_date or datetime.now().strftime("%Y-%m-%d")
        result = parse_flight_query(request.query, current_date)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)