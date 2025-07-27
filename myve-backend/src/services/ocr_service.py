

from dotenv import load_dotenv
import os
import io
from google.cloud import vision
from PIL import Image

class OCRService:
    def __init__(self):
        load_dotenv()
        # Ensure GOOGLE_APPLICATION_CREDENTIALS is set
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        self.client = vision.ImageAnnotatorClient()

    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract descriptive information from a PIL Image using Google Cloud Vision.
        Performs both label detection and text detection to provide a combined description
        of the image content and any detected text.
        """
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        content = img_byte_arr.getvalue()

        image = vision.Image(content=content)

        # Perform both label and text detection
        label_response = self.client.label_detection(image=image)
        labels = label_response.label_annotations
        label_desc = ", ".join([label.description for label in labels]) if labels else "No labels"

        text_response = self.client.text_detection(image=image)
        texts = text_response.text_annotations
        text_desc = texts[0].description.strip() if texts else "No text"

        full_description = f"Image likely contains: {label_desc}. Text detected: {text_desc}"
        return full_description

    def extract_text_from_path(self, image_path: str) -> str:
        """Extract text from an image file path using Google Cloud Vision"""
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations

        return texts[0].description if texts else ""
    def extract_text_from_bytes(self, image_bytes: bytes) -> str:
        if not image_bytes or len(image_bytes) < 100:
            print(f"[DEBUG] Received image bytes size: {len(image_bytes)}")
            with open("debug_invalid_image.bin", "wb") as f:
                f.write(image_bytes)
            raise ValueError("Image bytes are too small or empty")

        try:
            # Save the image bytes to file for debugging
            with open("debug_vision_image.png", "wb") as f:
                f.write(image_bytes)

            image = vision.Image(content=image_bytes)

            # Perform both label and text detection
            label_response = self.client.label_detection(image=image)
            labels = label_response.label_annotations
            label_desc = ", ".join([label.description for label in labels]) if labels else "No labels"

            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations
            text_desc = texts[0].description.strip() if texts else "No text"

            full_description = f"Image likely contains: {label_desc}. Text detected: {text_desc}"
            return full_description
        except Exception as e:
            raise RuntimeError(f"Failed to process image bytes: {e}")