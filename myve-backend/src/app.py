import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, session
from flask_cors import CORS

from src.routes.mcp_route import mcp_bp
from src.routes.ai_route import ai_bp
from src.routes.vision_route import vision_bp
from src.routes.routes import routes

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# 🔒 Required for session management
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# Enable CORS for all routes
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)

app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
app.register_blueprint(ai_bp, url_prefix='/api/ai')
app.register_blueprint(vision_bp, url_prefix='/api/vision')
app.register_blueprint(routes, url_prefix='/api')

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


from flask import jsonify, request

@app.route("/api/launch/vision", methods=["POST"])
def launch_vision():
    import subprocess
    import logging
    try:
        logging.info("Launching vision tool via subprocess...")

        # Use the absolute path to the vision launcher
        python_executable = sys.executable
        backend_root = os.path.dirname(os.path.abspath(__file__))
        vision_path = os.path.join(backend_root, "utils", "vision_launcher.py")

        if not os.path.exists(vision_path):
            raise FileNotFoundError(f"vision_launcher.py not found at: {vision_path}")

        subprocess.Popen(
            [python_executable, vision_path],
            cwd=os.path.dirname(vision_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        logging.info(f"Vision launcher started from {vision_path}")
        return jsonify({"status": "launched"}), 200

    except Exception as e:
        logging.exception("Failed to launch vision tool")
        return jsonify({"error": str(e)}), 500


# Print all registered routes before running the app
print("✅ Registered routes:")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint:30s} -> {rule.methods} {rule.rule}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
