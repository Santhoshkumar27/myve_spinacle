# vision_route.py

# ✅ This file defines vision_bp correctly and registers a POST route to /api/vision/advice

from flask import Blueprint, request, jsonify
from src.services.ocr_service import OCRService
from src.services.gemini_service import fetch_mcp_context
from src.agents.vision_agent import VisionAgent
import base64
from PIL import Image
import io
import logging

vision_bp = Blueprint("vision", __name__)
logging.info("✅ vision_route.py: vision_bp blueprint initialized")

ocr_service = OCRService()
vision_agent = VisionAgent()

@vision_bp.route("/advice", methods=["POST"])
def get_vision_advice():
    try:
        import logging
        logging.info("✅ Received POST /api/vision/advice")

        data = request.get_json()
        logging.debug(f"📦 Full request data: {data}")
        base64_data = data.get("image_base64", "")
        logging.debug(f"[DEBUG] Incoming base64 string size: {len(base64_data)}")
        logging.debug(f"🔍 image_base64 preview: {base64_data[:100]}")
        user_context = data.get("user_context", "")
        logging.info(f"📥 [DEBUG] Raw base64 length: {len(base64_data)}")
        # Enhanced base64 parsing with error check
        if base64_data.startswith("data:image"):
            try:
                base64_str = base64_data.split(",", 1)[1]
            except IndexError:
                logging.error("❌ Malformed base64_data — no comma found.")
                return jsonify({"error": "Malformed base64 image"}), 400
        else:
            base64_str = base64_data  # Assume raw base64 string

        logging.debug(f"[DEBUG] Clean base64 string starts with: {base64_str[:30]}...")
        logging.debug(f"[DEBUG] Parsed base64 part size: {len(base64_str)}")
        logging.info(f"📥 [DEBUG] Stripped base64 length: {len(base64_str)}")
        import binascii
        try:
            image_data = base64.b64decode(base64_str)
            logging.debug(f"[DEBUG] Decoded image byte preview: {image_data[:50]}")
        except binascii.Error as decode_error:
            logging.error(f"❌ Base64 decoding failed: {decode_error}")
            return jsonify({"error": "Invalid base64 image"}), 400
        logging.info(f"🧪 [DEBUG] Received image data size: {len(image_data)} bytes")
        if not image_data or len(image_data) < 100:
            logging.warning("⚠️ [WARN] Decoded image too small or empty")
            logging.debug(f"[DEBUG] image_data is empty or too small. Bytes: {image_data}")
            return jsonify({"error": "Image bytes are too small or empty"}), 500
        # Debug: Write image to disk for inspection
        with open("debug_vision_image.png", "wb") as f:
            f.write(image_data)

        logging.info("🔧 Calling OCR service with decoded image...")
        try:
            extracted_text = ocr_service.extract_text_from_bytes(image_data)
        except Exception as ocr_error:
            logging.error(f"❌ OCR extraction failed: {ocr_error}")
            return jsonify({"error": str(ocr_error)}), 500
        # Remove all code that extracts net worth or affordability ratio from user_context
        # Only use OCR output for the prompt.
        mobile_number = data.get("mobile_number") or "unknown"
        user_context = ""

        ocr_prompt = f"""Recognize any products, services, or intents from this screen content:
{extracted_text}

Analyze the user's intent or goal and provide practical financial advice based only on this information.
"""

        agent_result = vision_agent.run(prompt=ocr_prompt, user_id=mobile_number)
        if isinstance(agent_result, str):
            return jsonify({"advice": agent_result})
        elif hasattr(agent_result, "response"):
            return jsonify({"advice": agent_result.response})
        else:
            return jsonify({"advice": str(agent_result)})
    except Exception as e:
        import traceback
        logging.exception("❌ Vision advice failed with unhandled error")
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc().splitlines()[-5:]  # Only last few lines
        }), 500

@vision_bp.route("/start", methods=["POST"])
def start_vision_app():
    user = request.json.get("user")
    if not user:
        return jsonify({"error": "Missing user ID"}), 400
    result = vision_agent.start_electron_app(user)
    return jsonify(result)

@vision_bp.route("/stop", methods=["POST"])
def stop_vision_app():
    result = vision_agent.stop_electron_app()
    return jsonify(result)

@vision_bp.route("/control", methods=["POST"])
def control_vision_app():
    data = request.get_json()
    action = data.get("action")
    user = data.get("user")

    if action == "start":
        if not user:
            return jsonify({"error": "Missing user ID"}), 400
        result = vision_agent.start_electron_app(user)
        return jsonify(result)
    elif action == "stop":
        result = vision_agent.stop_electron_app()
        return jsonify(result)
    else:
        return jsonify({"error": "Invalid action"}), 400