from firebase_config import db
from datetime import datetime
import uuid

def save_complaint(data: dict):
    try:
        complaint_id = "CMP-" + str(uuid.uuid4())[:8].upper()
        
        # Severity calculate karo
        severity = calculate_severity(data)
        
        complaint = {
            "complaint_id": complaint_id,
            "session_id": data.get("session_id", str(uuid.uuid4())),
            "timestamp": datetime.utcnow().isoformat(),
            "complaint_type": data.get("complaint_type", ""),
            "location": data.get("location", ""),
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
        
        return {
            "success": True,
            "complaint_id": complaint_id,
            "severity_score": severity,
            "message": "Complaint saved successfully"
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate_severity(data: dict) -> int:
    score = 0
    
    complaint_type = data.get("complaint_type", "")
    size = data.get("pothole_size", "")
    depth = data.get("pothole_depth", "")
    road_type = data.get("road_type", "")
    image = data.get("image_available", "no")
    
    # Complaint type scoring
    if complaint_type == "pothole":
        score += 3
    elif complaint_type == "waterlogging":
        score += 2
    else:
        score += 1
    
    # Size scoring
    try:
        size_num = float(''.join(filter(str.isdigit, str(size))))
        if size_num > 3:
            score += 3
        elif size_num > 1:
            score += 2
        else:
            score += 1
    except:
        score += 1
    
    # Depth scoring
    try:
        depth_num = float(''.join(filter(str.isdigit, str(depth))))
        if depth_num > 1:
            score += 2
        else:
            score += 1
    except:
        score += 1
    
    # Road type scoring
    if road_type in ["NH", "SH"]:
        score += 2
    elif road_type == "MDR":
        score += 1
    
    # Image scoring
    if image == "no":
        score += 1
    else:
        score -= 1
    
    return max(1, min(10, score))