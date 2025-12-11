# src/preprocessing.py
import cv2
import numpy as np
import tempfile
import os

def preprocess_image(image_path: str) -> dict:
    """
    Preprocess image for better OCR results
    """
    steps = []
    
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Failed to load image")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    steps.append("grayscale")
    
    # Noise removal
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    steps.append("denoise")
    
    # Adaptive thresholding
    threshold = cv2.adaptiveThreshold(
        denoised, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    steps.append("threshold")
    
    # Resize if too small
    height, width = threshold.shape
    if width < 800:
        scale = 800 / width
        new_width = int(width * scale)
        new_height = int(height * scale)
        threshold = cv2.resize(threshold, (new_width, new_height), 
                              interpolation=cv2.INTER_CUBIC)
        steps.append("resize")
    
    # Save preprocessed image
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        cv2.imwrite(tmp.name, threshold)
        processed_path = tmp.name
    
    return {
        "preprocessing": "successful",
        "steps": steps,
        "processed_path": processed_path,
        "original_size": f"{img.shape[1]}x{img.shape[0]}",
        "processed_size": f"{threshold.shape[1]}x{threshold.shape[0]}"
    }
