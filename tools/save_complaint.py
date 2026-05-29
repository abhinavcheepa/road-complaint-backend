from firebase_config import db
from datetime import datetime
import uuid

def save_complaint(data: dict):
    try:
        complaint_id = "CMP-" + str(uuid.uuid4())[:8].upper()
        severity = calculate_severity(data)

        full_address = data.get("full_address", {})
        if isinstance(full_address, str):
            full_address = {"street": full_address}

        location_parts = [
            full_address.get("street", ""),
            full_address.get("ward_colony", ""),
            full_address.get("city", ""),
            full_address.get("district", ""),
            full_address.get("state", ""),
        ]
        location_string = ", ".join([p for p in location_parts if p])
        if not location_string:
            location_string = data.get("location", "")

        # ── 1. MUNICIPALITY DATA (poori info) ──────────────────
        complaint = {
            "complaint_id": complaint_id,
            "session_id": data.get("session_id", str(uuid.uuid4())),
            "timestamp": datetime.utcnow().isoformat(),
            "complaint_type": data.get("complaint_type", ""),
            "location": location_string,
            "full_address": {
                "street": full_address.get("street", ""),
                "ward_colony": full_address.get("ward_colony", ""),
                "city": full_address.get("city", ""),
                "district": full_address.get("district", ""),
                "state": full_address.get("state", ""),
                "pincode": full_address.get("pincode", "")
            },
            "coordinates": data.get("coordinates", {"lat": "", "lng": ""}),
            "road_type": data.get("road_type", "Unknown"),
            "authority_assigned": data.get("authority_assigned", {}),
            "landmark": data.get("landmark", ""),
            "pothole_size": data.get("pothole_size", ""),
            "pothole_depth": data.get("pothole_depth", ""),
            "severity_score": severity,
            "image_available": data.get("image_available", "no"),
            "image_url": data.get("image_url", ""),
            "user_name": data.get("user_name", ""),
            "phone_number": data.get("phone_number", ""),
            "whatsapp_consent": data.get("whatsapp_consent", "no"),
            "language_detected": data.get("language_detected", "hindi"),
            "status": "pending",
            "partial_save": False
        }

        db.collection("complaints").document(complaint_id).set(complaint)

        # ── 2. DRIVER WARNING DATA (selective info only) ────────
        coordinates = data.get("coordinates", {})
        lat = coordinates.get("lat", "") if isinstance(coordinates, dict) else ""
        lng = coordinates.get("lng", "") if isinstance(coordinates, dict) else ""

        driver_data = {
            "complaint_id": complaint_id,
            "timestamp": datetime.utcnow().isoformat(),
            "complaint_type": data.get("complaint_type", ""),
            "location": location_string,
            "coordinates": {"lat": lat, "lng": lng},
            "road_type": data.get("road_type", "Unknown"),
            "pothole_size": data.get("pothole_size", ""),
            "pothole_depth": data.get("pothole_depth", ""),
            "severity_score": severity,
            "status": "active"
        }

        db.collection("driver_warnings").document(complaint_id).set(driver_data)

        return {
            "success": True,
            "complaint_id": complaint_id,
            "severity_score": severity,
            "message": "Complaint saved successfully"
        }

    except Exception as e:
        print("Save complaint error:", e)
        return {"success": False, "error": str(e)}


def calculate_severity(data: dict) -> int:
    score = 0
    complaint_type = data.get("complaint_type", "")
    size = data.get("pothole_size", "")
    depth = data.get("pothole_depth", "")
    road_type = data.get("road_type", "")
    image = data.get("image_available", "no")

    if complaint_type == "pothole":
        score += 3
    elif complaint_type == "waterlogging":
        score += 2
    else:
        score += 1

    try:
        size_num = float(''.join(filter(lambda x: x.isdigit() or x == '.', str(size))))
        if size_num > 3:
            score += 3
        elif size_num > 1:
            score += 2
        else:
            score += 1
    except:
        score += 1

    try:
        depth_num = float(''.join(filter(lambda x: x.isdigit() or x == '.', str(depth))))
        if depth_num > 1:
            score += 2
        else:
            score += 1
    except:
        score += 1

    if road_type in ["NH", "SH"]:
        score += 2
    elif road_type == "MDR":
        score += 1

    if image in ["yes", "already_uploaded"]:
        score -= 1
    else:
        score += 1

    return max(1, min(10, score))