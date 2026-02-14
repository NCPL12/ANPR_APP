"""
ANPR REST API – Python backend for MongoDB detected_plates.
Serves stats and paginated plate records for the dashboard.
"""
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()
from bson import ObjectId
import base64
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING, ASCENDING

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# MongoDB connection
MONGO_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://anprncpl_db_user:aYWS8VfcQMagPrX0@anpr.w8cukh3.mongodb.net/"
)
DB_NAME = os.environ.get("ANPR_DB_NAME", "anpr_database")
COLLECTION_NAME = "detected_plates"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
coll = db[COLLECTION_NAME]

# Map vehicle_class to plate type (adjust as per your codes)
VEHICLE_CLASS_LABELS = {
    0: "Unknown",
    1: "Private",
    2: "Commercial",
    3: "Government",
    4: "Special",
    5: "Diplomatic",
    6: "Taxi",
    7: "Truck",
}


def json_serial(obj):
    """Convert ObjectId and datetime for JSON."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def doc_to_plate(doc, include_image=False):
    """Convert MongoDB document to API response shape (all fields from DB)."""
    plate = {
        "id": str(doc["_id"]),
        "plate_number": doc.get("plate_number", ""),
        "raw_text": doc.get("raw_text", ""),
        "confidence": doc.get("confidence"),
        "ocr_engine": doc.get("ocr_engine", ""),
        "timestamp": doc.get("timestamp") or doc.get("created_at"),
        "frame_coords": doc.get("frame_coords"),
        "vehicle_coords": doc.get("vehicle_coords"),
        "vehicle_confidence": doc.get("vehicle_confidence"),
        "vehicle_class": doc.get("vehicle_class"),
        "plate_type": VEHICLE_CLASS_LABELS.get(doc.get("vehicle_class"), "Unknown"),
        "image_saved": doc.get("image_saved", False),
        "created_at": doc.get("created_at"),
    }
    if include_image and doc.get("plate_image"):
        plate["plate_image"] = doc["plate_image"]
    return plate


@app.route("/")
def index():
    return send_from_directory(".", "anpr.html")


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Dashboard stats: total, today, this week. Cameras/sites can be env or fixed."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    total = coll.count_documents({})
    today_count = coll.count_documents({"created_at": {"$gte": today_start}})
    week_count = coll.count_documents({"created_at": {"$gte": week_start}})

    return jsonify({
        "total": total,
        "today": today_count,
        "week": week_count,
        "cameras": int(os.environ.get("ANPR_CAMERAS", "23")),
        "sites": int(os.environ.get("ANPR_SITES", "2")),
    })


@app.route("/api/plates", methods=["GET"])
def get_plates():
    """List detected plates with pagination and sort. Use limit=all or high limit to get all records."""
    page = max(1, int(request.args.get("page", 1)))
    limit_arg = request.args.get("limit", "25")
    if limit_arg.lower() == "all":
        limit = 50000
    else:
        limit = min(50000, max(1, int(limit_arg) if limit_arg.isdigit() else 25))
    sort_param = request.args.get("sort", "date-desc")

    sort_map = {
        "date-desc": [("created_at", DESCENDING)],
        "date-asc": [("created_at", ASCENDING)],
        "plate": [("plate_number", ASCENDING)],
        "site": [("ocr_engine", ASCENDING), ("created_at", DESCENDING)],
    }
    sort = sort_map.get(sort_param, sort_map["date-desc"])

    skip = (page - 1) * limit
    cursor = coll.find({}).sort(sort).skip(skip).limit(limit)
    total = coll.count_documents({})

    items = [doc_to_plate(d, include_image=False) for d in cursor]
    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 0,
    })


@app.route("/api/plates/<plate_id>", methods=["GET"])
def get_plate(plate_id):
    """Single plate by id, optionally with base64 image."""
    try:
        doc = coll.find_one({"_id": ObjectId(plate_id)})
    except Exception:
        return jsonify({"error": "Invalid id"}), 400
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(doc_to_plate(doc, include_image=True))


@app.route("/api/plates/<plate_id>/image", methods=["GET"])
def get_plate_image(plate_id):
    """Return plate image as JSON { image: base64 } or 404."""
    try:
        doc = coll.find_one({"_id": ObjectId(plate_id)}, {"plate_image": 1})
    except Exception:
        return jsonify({"error": "Invalid id"}), 400
    if not doc or not doc.get("plate_image"):
        return jsonify({"error": "Image not found"}), 404
    return jsonify({"image": doc["plate_image"]})


@app.route("/api/plates/<plate_id>/image/img", methods=["GET"])
def get_plate_image_binary(plate_id):
    """Return plate image as JPEG for <img> src."""
    try:
        doc = coll.find_one({"_id": ObjectId(plate_id)}, {"plate_image": 1})
    except Exception:
        return Response(status=400)
    if not doc or not doc.get("plate_image"):
        return Response(status=404)
    try:
        raw = base64.b64decode(doc["plate_image"])
    except Exception:
        return Response(status=500)
    return Response(raw, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
