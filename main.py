from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from tools.save_complaint import save_complaint, calculate_severity
from tools.road_type_detection import detect_road_type
from tools.authority_lookup import lookup_authority
from tools.resume_session import resume_session, save_partial_session
from tools.whatsapp_notification import send_whatsapp
import uvicorn
import json

app = FastAPI(title="Road Complaint Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ─── Helper Function ───────────────────────────────────────
def extract_vapi_args(body: dict):
    try:
        tool_calls = body.get("message", {}).get("toolCalls", [])
        if not tool_calls:
            tool_calls = body.get("toolCalls", [])
        
        if tool_calls:
            tool_call_id = tool_calls[0].get("id", "")
            args = tool_calls[0].get("function", {}).get("arguments", {})
            
            if isinstance(args, str):
                args = json.loads(args)
            
            return tool_call_id, args
        
        return "", {}
    except Exception as e:
        print("Extract error:", e)
        return "", {}

# ─── VAPI Tool Webhooks ───────────────────────────────────

@app.post("/api/tools/save-to-firebase")
async def save_to_firebase(request: Request):
    body = await request.json()
    print("SAVE FIREBASE REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    print("PARSED ARGS:", args)
    result = save_complaint(args)
    print("SAVE RESULT:", result)
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        }]
    }

@app.post("/api/tools/road-type-detection")
async def road_type_detection(request: Request):
    body = await request.json()
    print("ROAD TYPE REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    location = args.get("location", "")
    result = detect_road_type(location)
    print("ROAD TYPE RESULT:", result)
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        }]
    }

@app.post("/api/tools/authority-lookup")
async def authority_lookup(request: Request):
    body = await request.json()
    print("AUTHORITY REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    result = lookup_authority(
        args.get("road_type", ""),
        args.get("location", "")
    )
    print("AUTHORITY RESULT:", result)
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        }]
    }

@app.post("/api/tools/resume-session")
async def resume_session_handler(request: Request):
    body = await request.json()
    print("RESUME SESSION REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    result = resume_session(args.get("phone_number", ""))
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        }]
    }

@app.post("/api/tools/whatsapp-notification")
async def whatsapp_notification(request: Request):
    body = await request.json()
    print("WHATSAPP REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    result = send_whatsapp(
        args.get("phone_number", ""),
        args.get("complaint_id", ""),
        args
    )
    print("WHATSAPP RESULT:", result)
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        }]
    }

@app.post("/api/tools/severity-calculator")
async def severity_calculator(request: Request):
    body = await request.json()
    print("SEVERITY REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    score = calculate_severity(args)
    print("SEVERITY SCORE:", score)
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps({"severity_score": score})
        }]
    }

@app.post("/api/tools/image-analysis")
async def image_analysis(request: Request):
    body = await request.json()
    print("IMAGE ANALYSIS REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    image_url = args.get("image_url", "")
    
    # Basic response — AI model integration baad mein
    result = {
        "success": True,
        "road_type": "Unknown",
        "pothole_size": "Unknown",
        "pothole_depth": "Unknown",
        "severity_hints": 5,
        "message": "Image received, manual review required"
    }
    return {
        "results": [{
            "toolCallId": tool_call_id,
            "result": json.dumps(result)
        }]
    }
@app.get("/api/driver/nearby-potholes")
async def nearby_potholes(lat: float, lng: float, radius: float = 0.0005):
    try:
        print(f"Nearby potholes request: lat={lat}, lng={lng}, radius={radius}")
        
        # Firebase se saare active warnings lo
        docs = db.collection("driver_warnings")\
            .where("status", "==", "active")\
            .stream()
        
        nearby = []
        for doc in docs:
            d = doc.to_dict()
            coords = d.get("coordinates", {})
            
            try:
                d_lat = float(coords.get("lat", 0))
                d_lng = float(coords.get("lng", 0))
            except:
                continue
            
            if d_lat == 0 or d_lng == 0:
                continue
            
            # Distance calculate karo
            lat_diff = abs(float(lat) - d_lat)
            lng_diff = abs(float(lng) - d_lng)
            distance = ((lat_diff**2) + (lng_diff**2)) ** 0.5
            
            # ~50 meters = 0.0005 degrees approx
            if distance <= radius:
                nearby.append({
                    "complaint_id": d.get("complaint_id"),
                    "complaint_type": d.get("complaint_type"),
                    "location": d.get("location"),
                    "coordinates": coords,
                    "pothole_size": d.get("pothole_size"),
                    "pothole_depth": d.get("pothole_depth"),
                    "severity_score": d.get("severity_score"),
                    "road_type": d.get("road_type"),
                    "distance_approx": round(distance * 111000, 1),
                    "warning": get_warning_message(d)
                })
        
        # Severity se sort karo
        nearby.sort(key=lambda x: x.get("severity_score", 0), reverse=True)
        
        return {
            "success": True,
            "count": len(nearby),
            "potholes": nearby
        }
    
    except Exception as e:
        print("Nearby potholes error:", e)
        return {"success": False, "error": str(e), "potholes": []}


def get_warning_message(data: dict) -> str:
    severity = data.get("severity_score", 0)
    complaint_type = data.get("complaint_type", "")
    size = data.get("pothole_size", "")
    
    if severity >= 8:
        return f"DANGER! Bada {complaint_type} aage hai — rukein ya dheerey chalein!"
    elif severity >= 5:
        return f"Savdhaan! {complaint_type} detected {size} — speed kam karein"
    else:
        return f"Chetavni: {complaint_type} nearby — dhyan rakhein"

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Road Complaint Backend Running!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)