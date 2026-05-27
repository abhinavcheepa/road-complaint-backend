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

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Road Complaint Backend Running!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)