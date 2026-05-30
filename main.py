from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from tools.save_complaint import save_complaint, calculate_severity
from tools.road_type_detection import detect_road_type
from tools.authority_lookup import lookup_authority
from tools.resume_session import resume_session, save_partial_session
from tools.whatsapp_notification import send_whatsapp
from firebase_config import db
from datetime import datetime
import uvicorn
import json
import uuid
import os
import requests

app = FastAPI(title="Road Complaint Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

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

# ─── VAPI Complaint Tools ─────────────────────────────────

@app.post("/api/tools/save-to-firebase")
async def save_to_firebase(request: Request):
    body = await request.json()
    print("SAVE FIREBASE REQUEST:", json.dumps(body, indent=2))
    tool_call_id, args = extract_vapi_args(body)
    print("PARSED ARGS:", args)
    result = save_complaint(args)
    print("SAVE RESULT:", result)
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps(result)}]}

@app.post("/api/tools/road-type-detection")
async def road_type_detection(request: Request):
    body = await request.json()
    tool_call_id, args = extract_vapi_args(body)
    result = detect_road_type(args.get("location", ""))
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps(result)}]}

@app.post("/api/tools/authority-lookup")
async def authority_lookup(request: Request):
    body = await request.json()
    tool_call_id, args = extract_vapi_args(body)
    result = lookup_authority(args.get("road_type", ""), args.get("location", ""))
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps(result)}]}

@app.post("/api/tools/resume-session")
async def resume_session_handler(request: Request):
    body = await request.json()
    tool_call_id, args = extract_vapi_args(body)
    result = resume_session(args.get("phone_number", ""))
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps(result)}]}

@app.post("/api/tools/whatsapp-notification")
async def whatsapp_notification(request: Request):
    body = await request.json()
    tool_call_id, args = extract_vapi_args(body)
    result = send_whatsapp(args.get("phone_number", ""), args.get("complaint_id", ""), args)
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps(result)}]}

@app.post("/api/tools/severity-calculator")
async def severity_calculator(request: Request):
    body = await request.json()
    tool_call_id, args = extract_vapi_args(body)
    score = calculate_severity(args)
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({"severity_score": score})}]}

@app.post("/api/tools/image-analysis")
async def image_analysis(request: Request):
    body = await request.json()
    tool_call_id, args = extract_vapi_args(body)
    result = {
        "success": True,
        "road_type": "Unknown",
        "pothole_size": "Unknown",
        "pothole_depth": "Unknown",
        "severity_hints": 5,
        "message": "Image received, manual review required"
    }
    return {"results": [{"toolCallId": tool_call_id, "result": json.dumps(result)}]}

# ─── Driver Warning Endpoints ─────────────────────────────

@app.get("/api/driver/nearby-potholes")
async def nearby_potholes(lat: float, lng: float, radius: float = 0.0005):
    try:
        docs = db.collection("driver_warnings").where("status", "==", "active").stream()
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
            lat_diff = abs(float(lat) - d_lat)
            lng_diff = abs(float(lng) - d_lng)
            distance = ((lat_diff**2) + (lng_diff**2)) ** 0.5
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
        nearby.sort(key=lambda x: x.get("severity_score", 0), reverse=True)
        return {"success": True, "count": len(nearby), "potholes": nearby}
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


@app.post("/api/driver/update-location")
async def update_driver_location(request: Request):
    try:
        body = await request.json()
        tool_call_id, args = extract_vapi_args(body)
        session_id = args.get("session_id", str(uuid.uuid4()))
        location_data = {
            "session_id": session_id,
            "lat": args.get("lat"),
            "lng": args.get("lng"),
            "speed": args.get("speed", 0),
            "vehicle_type": args.get("vehicle_type", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "is_active": True
        }
        db.collection("driver_sessions").document(session_id).set(location_data, merge=True)
        return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({"success": True, "session_id": session_id})}]}
    except Exception as e:
        print("Update location error:", e)
        return {"results": [{"toolCallId": "", "result": str(e)}]}


@app.post("/api/driver/calculate-safe-speed")
async def calculate_safe_speed(request: Request):
    try:
        body = await request.json()
        tool_call_id, args = extract_vapi_args(body)
        vehicle_type = args.get("vehicle_type", "car").lower()
        severity = int(args.get("severity_score", 5))
        road_type = args.get("road_type", "City Road")
        weather = args.get("weather", "clear").lower()

        if vehicle_type == "bike":
            if severity >= 7: safe_speed = 15
            elif severity >= 4: safe_speed = 25
            else: safe_speed = 30
        elif vehicle_type == "car":
            if severity >= 7: safe_speed = 20
            elif severity >= 4: safe_speed = 30
            else: safe_speed = 40
        else:
            if severity >= 7: safe_speed = 10
            elif severity >= 4: safe_speed = 20
            else: safe_speed = 25

        if road_type in ["NH", "SH"]: safe_speed += 10
        elif road_type == "Unknown": safe_speed -= 5
        if weather == "rain": safe_speed -= 10
        elif weather == "fog": safe_speed -= 15
        safe_speed = max(5, safe_speed)

        return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({
            "success": True,
            "safe_speed": safe_speed,
            "message": f"{vehicle_type} ke liye {safe_speed} km/h safe speed hai"
        })}]}
    except Exception as e:
        print("Safe speed error:", e)
        return {"results": [{"toolCallId": "", "result": str(e)}]}


@app.post("/api/driver/weather")
async def get_weather(request: Request):
    try:
        body = await request.json()
        tool_call_id, args = extract_vapi_args(body)
        lat = args.get("lat")
        lng = args.get("lng")
        weather_key = os.getenv("OPENWEATHER_API_KEY", "")

        if weather_key:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={weather_key}&units=metric"
            response = requests.get(url, timeout=5)
            data = response.json()
            condition = data.get("weather", [{}])[0].get("main", "Clear").lower()
            temp = data.get("main", {}).get("temp", 25)
            if "rain" in condition: weather_status = "rain"
            elif "fog" in condition or "mist" in condition: weather_status = "fog"
            else: weather_status = "clear"
        else:
            weather_status = "clear"
            temp = 25

        return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({
            "success": True,
            "weather": weather_status,
            "temperature": temp
        })}]}
    except Exception as e:
        print("Weather error:", e)
        return {"results": [{"toolCallId": "", "result": json.dumps({"success": True, "weather": "clear", "temperature": 25})}]}


@app.post("/api/driver/check-drowsiness")
async def check_drowsiness(request: Request):
    try:
        body = await request.json()
        tool_call_id, args = extract_vapi_args(body)
        last_steering = args.get("last_steering_movement", 0)
        last_speed_change = args.get("last_speed_change", 0)
        current_speed = args.get("current_speed", 0)

        alert_level = 0
        message = "Driver theek lag raha hai"

        if current_speed > 20:
            if last_steering > 60 and last_speed_change > 90:
                alert_level = 2
                message = "DANGER! Driver so raha lag raha hai — turant rokein!"
            elif last_steering > 30 and last_speed_change > 60:
                alert_level = 1
                message = "Driver thaka hua lag raha hai — alert karo"

        return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({
            "success": True,
            "alert_level": alert_level,
            "message": message,
            "action_needed": alert_level > 0
        })}]}
    except Exception as e:
        print("Drowsiness error:", e)
        return {"results": [{"toolCallId": "", "result": str(e)}]}


# ─── WhatsApp Bot Webhook ─────────────────────────────────

@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    try:
        body = await request.json()
        print("WHATSAPP WEBHOOK:", json.dumps(body, indent=2))

        event = body.get("event", "")
        if event != "messages.received":
            return {"status": "ok"}

        data = body.get("data", {})
        message = data.get("message", {})
        from_number = data.get("from", "").replace("@s.whatsapp.net", "")
        text = message.get("text", {}).get("body", "").strip()

        print(f"Message from {from_number}: {text}")

        response_text = await process_whatsapp_message(text, from_number)

        if response_text:
            await send_wasender_message(from_number, response_text)

        return {"status": "ok"}

    except Exception as e:
        print("Webhook error:", e)
        return {"status": "error", "message": str(e)}


async def process_whatsapp_message(text: str, phone: str) -> str:
    t = text.lower().strip()

    if any(w in t for w in ["hello", "hi", "helo", "namaskar", "namaste", "hey", "haan", "start"]):
        return """🛣️ *Road Complaint System mein Aapka Swagat Hai!*

Main aapki kaise madad kar sakta hun?

1️⃣ *complaint* — Nayi complaint register karein
2️⃣ *status* — Complaint status check karein
3️⃣ *help* — Help aur jankari

Reply mein number ya keyword bhejein! 😊"""

    elif any(w in t for w in ["1", "complaint", "report", "pothole", "shikayat", "complain", "darj"]):
        return """📝 *Nayi Complaint Register Karein*

Complaint register karne ke 2 tarike hain:

📞 *Voice Call:* Hamare AI agent se baat karein
📱 *App:* Road Complaint System app use karein

Kya aap call se complaint register karna chahte hain?
Reply karein: *call haan* ya *call nahi*"""

    elif any(w in t for w in ["2", "status", "check", "dekho", "dekhna"]):
        return """🔍 *Complaint Status Check Karein*

Apna Complaint ID bhejein.
Format: *CMP-XXXXXXXX*

Example: *CMP-1ACF21AE*"""

    elif t.startswith("cmp-"):
        complaint_id = t.upper()
        return await get_complaint_status(complaint_id)

    elif any(w in t for w in ["call haan", "call han", "call yes", "haan call"]):
        return """📞 *Voice Agent Se Baat Karein*

Abhi hamare AI voice agent ko call karein.
Agent aapki complaint register karega aur confirmation WhatsApp pe bhejega! ✅

_Hamare agent ka number jald available hoga!_"""

    elif any(w in t for w in ["call nahi", "call na", "call no", "nahi call"]):
        return """📱 *App Se Register Karein*

Road Complaint System app use karein:

1️⃣ App kholen
2️⃣ "Complaint Register" click karein
3️⃣ Photo click karein — location auto save hogi
4️⃣ Submit karein

_App download link jald available hoga!_ 🚀"""

    elif any(w in t for w in ["3", "help", "madad", "info", "kya", "kaise"]):
        return """ℹ️ *Road Complaint System — Help*

*Hum kya karte hain:*
🔧 Pothole, waterlogging, drainage complaints
🚗 Driver safety warnings
🏛️ Municipality ko direct notification
📊 Budget transparency

*Commands:*
- *complaint* — Nayi complaint
- *status* — Status check
- *CMP-XXXXXXXX* — Specific complaint status
- *help* — Ye message

*Dashboard:* municipality-dashboard-omega.vercel.app"""

    else:
        return """🛣️ *Road Complaint System*

Samajh nahi aaya. Please in options mein se choose karein:

1️⃣ *complaint* — Nayi complaint register karein
2️⃣ *status* — Complaint status check karein
3️⃣ *help* — Help aur jankari"""


async def get_complaint_status(complaint_id: str) -> str:
    try:
        docs = db.collection("complaints")\
            .where("complaint_id", "==", complaint_id)\
            .limit(1).stream()

        for doc in docs:
            data = doc.to_dict()
            status = data.get("status", "pending")
            location = data.get("location", "N/A")
            complaint_type = data.get("complaint_type", "N/A")
            severity = data.get("severity_score", 0)
            authority = data.get("authority_assigned", {})
            authority_name = authority.get("org_name", "N/A") if isinstance(authority, dict) else "N/A"

            emoji = "⏳" if status == "pending" else "🔄" if status == "assigned" else "✅"
            msg = "Aapki complaint process ho rahi hai. Jald action liya jaayega! 🙏" if status == "pending" \
                else "Authority ne complaint assign kar li hai! 🔄" if status == "assigned" \
                else "Complaint resolve ho gayi hai! ✅"

            return f"""🔍 *Complaint Status*

🆔 *ID:* {complaint_id}
{emoji} *Status:* {status.upper()}
📍 *Location:* {location}
🔧 *Type:* {complaint_type}
⚠️ *Severity:* {severity}/10
🏛️ *Authority:* {authority_name}

{msg}"""

        return f"❌ *{complaint_id}* nahi mili.\n\nKripya sahi ID check karein."

    except Exception as e:
        return "❌ Status check mein error aaya. Baad mein try karein."


async def send_wasender_message(phone: str, message: str):
    try:
        api_token = os.getenv("WASENDER_API_TOKEN")
        session = os.getenv("WASENDER_SESSION", "road-complaint-bot")

        phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not phone.startswith("91"):
            phone = "91" + phone

        url = "https://api.wasenderapi.com/api/send-message"
        payload = {
            "session": session,
            "to": f"{phone}@s.whatsapp.net",
            "text": message
        }
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        print("BOT REPLY SENT:", response.status_code, response.json())

    except Exception as e:
        print("Send message error:", e)


# ─── Health Check ─────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Road Complaint Backend Running!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)