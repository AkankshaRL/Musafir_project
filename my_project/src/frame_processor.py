# src/frame_processor.py
import cv2
import os
import tempfile
from typing import List, Dict
from preprocessing import preprocess_image
from ocr_engine import extract_text_from_image
from nlp_extractor import extract_entities

def extract_frames(video_path: str, fps: float = 1.5) -> List[str]:
    """
    Extract frames from video/GIF at specified FPS
    """
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps) if video_fps > 0 else 15
    
    frames = []
    frame_count = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                cv2.imwrite(tmp.name, frame)
                frames.append(tmp.name)
                saved_count += 1
        
        frame_count += 1
    
    cap.release()
    return frames

def merge_entities(frame_results: List[Dict]) -> Dict:
    """
    Merge entities from multiple frames, keeping highest confidence
    """
    merged = {}
    
    for frame_data in frame_results:
        entities = frame_data.get('entities', {})
        for key, value in entities.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, str) and len(value) > len(str(merged[key])):
                # Keep longer/more complete value
                merged[key] = value
    
    return merged

def process_dynamic_image(video_path: str) -> Dict:
    """
    Process dynamic image (GIF/MP4)
    """
    # Extract frames
    frame_paths = extract_frames(video_path)
    
    frame_results = []
    
    for i, frame_path in enumerate(frame_paths):
        try:
            # Preprocess
            preprocessing_result = preprocess_image(frame_path)
            
            # OCR
            ocr_result = extract_text_from_image(preprocessing_result['processed_path'])
            
            # Extract entities
            entities = extract_entities(ocr_result['text'])
            
            frame_results.append({
                "frame": i,
                "text": ocr_result['text'],
                "entities": entities
            })
            
            # Cleanup
            os.unlink(frame_path)
            if os.path.exists(preprocessing_result['processed_path']):
                os.unlink(preprocessing_result['processed_path'])
                
        except Exception as e:
            frame_results.append({
                "frame": i,
                "error": str(e)
            })
    
    # Merge entities
    merged_entities = merge_entities(frame_results)
    
    return {
        "frames_processed": len(frame_paths),
        "frame_results": frame_results,
        "merged_entities": merged_entities
    }