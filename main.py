from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from tools.save_complaint import save_complaint
from tools.road_type_detection import detect_road_type
from tools.authority_lookup import lookup_authority
from tools.resume_session import resume_session, save_partial_session
from tools.whatsapp_notification import send_whatsapp
import uvicorn

app = FastAPI(title="Road Complaint Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ─── VAPI Tool Webhooks ───────────────────────────────

@app.post("/api/tools/save-to-firebase")
async def save_to_firebase(request: Request):
    body = await request.json()
    data = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    result = save_complaint(data)
    return {"results": [{"toolCallId": body.get("message", {}).get("toolCalls", [{}])[0].get("id", ""), "result": str(result)}]}

@app.post("/api/tools/road-type-detection")
async def road_type_detection(request: Request):
    body = await request.json()
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    location = args.get("location", "")
    result = detect_road_type(location)
    return {"results": [{"toolCallId": body.get("message", {}).get("toolCalls", [{}])[0].get("id", ""), "result": str(result)}]}

@app.post("/api/tools/authority-lookup")
async def authority_lookup(request: Request):
    body = await request.json()
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    result = lookup_authority(args.get("road_type", ""), args.get("location", ""))
    return {"results": [{"toolCallId": body.get("message", {}).get("toolCalls", [{}])[0].get("id", ""), "result": str(result)}]}

@app.post("/api/tools/resume-session")
async def resume_session_handler(request: Request):
    body = await request.json()
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    result = resume_session(args.get("phone_number", ""))
    return {"results": [{"toolCallId": body.get("message", {}).get("toolCalls", [{}])[0].get("id", ""), "result": str(result)}]}

@app.post("/api/tools/whatsapp-notification")
async def whatsapp_notification(request: Request):
    body = await request.json()
    args = body.get("message", {}).get("toolCalls", [{}])[0].get("function", {}).get("arguments", {})
    result = send_whatsapp(
        args.get("phone_number", ""),
        args.get("complaint_id", ""),
        args
    )
    return {"results": [{"toolCallId": body.get("message", {}).get("toolCalls", [{}])[0].get("id", ""), "result": str(result)}]}

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Road Complaint Backend Running!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)