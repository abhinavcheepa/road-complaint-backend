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
    tool_call_id, args = extract_vapi_args(body)
    result = save_complaint(args)
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

# ─── Driver Helper Functions ──────────────────────────────

def calculate_safe_speed_logic(
    vehicle_type: str,
    severity: int,
    road_type: str,
    vehicle_weight: float = 1000,
    weather: str = "clear"
) -> int:
    if vehicle_type == "bike":
        if severity >= 7: safe_speed = 15
        elif severity >= 4: safe_speed = 25
        else: safe_speed = 30
    elif vehicle_type == "car":
        if severity >= 7: safe_speed = 20
        elif severity >= 4: safe_speed = 30
        else: safe_speed = 40
    else:  # truck/auto
        if severity >= 7: safe_speed = 10
        elif severity >= 4: safe_speed = 20
        else: safe_speed = 25

    # Weight adjustment
    if vehicle_weight > 2000: safe_speed -= 10
    elif vehicle_weight > 1000: safe_speed -= 5

    # Road type
    if road_type in ["NH", "SH"]: safe_speed += 10
    elif road_type == "Unknown": safe_speed -= 5

    # Weather
    if weather == "rain": safe_speed -= 10
    elif weather == "fog": safe_speed -= 15

    return max(5, safe_speed)


def get_detailed_warning(
    data: dict,
    distance_meters: float,
    safe_speed: int,
    current_speed: float,
    vehicle_type: str
) -> str:
    severity = data.get("severity_score", 0)
    size = data.get("pothole_size", "")
    depth = data.get("pothole_depth", "")
    complaint_type = data.get("complaint_type", "pothole")

    size_info = f"{size}" if size else ""
    depth_info = f", {depth} gehra" if depth else ""

    if current_speed > safe_speed:
        return (
            f"DANGER! {distance_meters:.0f} meter aage {complaint_type} hai "
            f"({size_info}{depth_info}). "
            f"Aapki speed {current_speed:.0f} km/h hai — "
            f"TURANT {safe_speed} km/h kar lo!"
        )
    elif severity >= 7:
        return (
            f"Savdhaan! {distance_meters:.0f} meter aage bada {complaint_type} hai "
            f"({size_info}{depth_info}). "
            f"Speed {safe_speed} km/h rakho."
        )
    else:
        return (
            f"Dhyan rakhein — {distance_meters:.0f} meter aage {complaint_type} hai. "
            f"{safe_speed} km/h safe speed hai."
        )


# ─── Driver Warning Endpoints ─────────────────────────────

@app.get("/api/driver/nearby-potholes")
async def nearby_potholes(
    lat: float,
    lng: float,
    radius: float = 0.0005,
    vehicle_type: str = "car",
    current_speed: float = 0,
    vehicle_weight: float = 1000,
    weather: str = "clear"
):
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
            distance_meters = round(distance * 111000, 1)

            if distance <= radius:
                severity = d.get("severity_score", 0)
                road_type = d.get("road_type", "Unknown")

                safe_speed = calculate_safe_speed_logic(
                    vehicle_type, severity, road_type,
                    vehicle_weight, weather
                )
                is_dangerous = current_speed > safe_speed

                nearby.append({
                    "complaint_id": d.get("complaint_id"),
                    "complaint_type": d.get("complaint_type"),
                    "location": d.get("location"),
                    "coordinates": coords,
                    "pothole_size": d.get("pothole_size"),
                    "pothole_depth": d.get("pothole_depth"),
                    "severity_score": severity,
                    "road_type": road_type,
                    "distance_meters": distance_meters,
                    "safe_speed": safe_speed,
                    "current_speed": current_speed,
                    "is_dangerous": is_dangerous,
                    "warning": get_detailed_warning(
                        d, distance_meters, safe_speed,
                        current_speed, vehicle_type
                    )
                })

        nearby.sort(key=lambda x: x.get("severity_score", 0), reverse=True)
        return {"success": True, "count": len(nearby), "potholes": nearby}
    except Exception as e:
        print("Nearby potholes error:", e)
        return {"success": False, "error": str(e), "potholes": []}


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
            "vehicle_weight": args.get("vehicle_weight", 1000),
            "vehicle_model": args.get("vehicle_model", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "is_active": True
        }
        db.collection("driver_sessions").document(session_id).set(location_data, merge=True)
        return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({
            "success": True,
            "session_id": session_id
        })}]}
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
        current_speed = float(args.get("current_speed", 0))
        vehicle_weight = float(args.get("vehicle_weight", 1000))

        safe_speed = calculate_safe_speed_logic(
            vehicle_type, severity, road_type,
            vehicle_weight, weather
        )

        is_dangerous = current_speed > safe_speed

        if is_dangerous:
            warning = (
                f"DANGER! Aapki speed {current_speed:.0f} km/h hai — "
                f"TURANT {safe_speed} km/h kar lo!"
            )
        else:
            warning = f"Speed theek hai — {safe_speed} km/h maintain karein"

        return {"results": [{"toolCallId": tool_call_id, "result": json.dumps({
            "success": True,
            "safe_speed": safe_speed,
            "current_speed": current_speed,
            "is_dangerous": is_dangerous,
            "warning": warning,
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
        return {"results": [{"toolCallId": "", "result": json.dumps({
            "success": True, "weather": "clear", "temperature": 25
        })}]}


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
        messages = data.get("messages", {})
        key = messages.get("key", {})

        if key.get("fromMe", False):
            return {"status": "ok"}

        from_number = key.get("cleanedSenderPn", "") or \
                      key.get("senderPn", "").replace("@s.whatsapp.net", "")

        message = messages.get("message", {})
        text = message.get("conversation", "") or \
               message.get("extendedTextMessage", {}).get("text", "") or \
               messages.get("messageBody", "")
        text = text.strip()

        print(f"Message from {from_number}: {text}")

        if not from_number or not text:
            return {"status": "ok"}

        response_text = await process_whatsapp_message(text, from_number)

        if response_text:
            await send_wasender_message(from_number, response_text)

        return {"status": "ok"}

    except Exception as e:
        print("Webhook error:", e)
        return {"status": "error", "message": str(e)}


# ─── WhatsApp Session Management ──────────────────────────

async def get_whatsapp_session(phone: str) -> dict:
    try:
        doc = db.collection("whatsapp_sessions").document(phone).get()
        if doc.exists:
            return doc.to_dict()
        return {}
    except:
        return {}


async def save_whatsapp_session(phone: str, step: str, data: dict):
    try:
        db.collection("whatsapp_sessions").document(phone).set({
            "step": step,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print("Session save error:", e)


async def clear_whatsapp_session(phone: str):
    try:
        db.collection("whatsapp_sessions").document(phone).delete()
    except Exception as e:
        print("Session clear error:", e)


# ─── WhatsApp Message Processing ──────────────────────────

async def process_whatsapp_message(text: str, phone: str) -> str:
    t = text.lower().strip()

    session = await get_whatsapp_session(phone)
    current_step = session.get("step", "menu") if session else "menu"
    session_data = session.get("data", {}) if session else {}

    # ─── ACTIVE SESSION STEPS ─────────────────────────────

    if current_step == "complaint_type":
        types = {
            "1": "pothole", "pothole": "pothole",
            "2": "waterlogging", "waterlogging": "waterlogging",
            "3": "drainage", "drainage": "drainage",
            "4": "streetlight", "streetlight": "streetlight",
            "5": "garbage", "garbage": "garbage",
            "6": "other", "other": "other"
        }
        complaint_type = types.get(t)
        if complaint_type:
            session_data["complaint_type"] = complaint_type
            await save_whatsapp_session(phone, "location", session_data)
            return f"✅ *{complaint_type.upper()}* noted!\n\n📍 *Exact location batao* — mohalla, ward, city?"
        else:
            return """❓ Sahi option choose karein:

1️⃣ Pothole
2️⃣ Waterlogging
3️⃣ Drainage
4️⃣ Street Light
5️⃣ Garbage
6️⃣ Other"""

    elif current_step == "location":
        session_data["location"] = text
        await save_whatsapp_session(phone, "details", session_data)
        ct = session_data.get("complaint_type", "")
        if ct == "pothole":
            return "📏 *Pothole kitna bada hai?* (feet ya meters mein batao)"
        elif ct == "waterlogging":
            return "💧 *Kitne area mein paani bhara hai?*"
        elif ct == "streetlight":
            return "💡 *Kitni lights band hain aur kab se?*"
        else:
            return "📝 *Thoda detail mein batao — kitne time se ye problem hai?*"

    elif current_step == "details":
        session_data["pothole_size"] = text
        await save_whatsapp_session(phone, "landmark", session_data)
        return "🏛️ *Koi nearby landmark hai?*\n\nAgar nahi pata to *skip* likhein"

    elif current_step == "landmark":
        if t != "skip":
            session_data["landmark"] = text
        await save_whatsapp_session(phone, "user_name", session_data)
        return "👤 *Aapka naam batao*"

    elif current_step == "user_name":
        session_data["user_name"] = text
        await save_whatsapp_session(phone, "confirm", session_data)

        ct = session_data.get("complaint_type", "N/A")
        loc = session_data.get("location", "N/A")
        size = session_data.get("pothole_size", "N/A")
        lm = session_data.get("landmark", "N/A")

        return f"""📋 *Complaint Summary:*

🔧 *Type:* {ct.upper()}
📍 *Location:* {loc}
📏 *Details:* {size}
🏛️ *Landmark:* {lm}
👤 *Name:* {text}
📱 *Phone:* {phone}

Kya ye sahi hai?
Reply: *haan* ya *nahi*"""

    elif current_step == "confirm":
        if any(w in t for w in ["haan", "han", "yes", "sahi", "correct", "ok", "theek"]):
            complaint_data = {
                "complaint_type": session_data.get("complaint_type", ""),
                "location": session_data.get("location", ""),
                "pothole_size": session_data.get("pothole_size", ""),
                "landmark": session_data.get("landmark", ""),
                "user_name": session_data.get("user_name", ""),
                "phone_number": phone,
                "coordinates": {"lat": "", "lng": ""},
                "road_type": "Unknown",
                "language_detected": "hindi",
                "whatsapp_consent": "yes",
                "image_available": "no"
            }
            result = save_complaint(complaint_data)
            complaint_id = result.get("complaint_id", "N/A")
            severity = result.get("severity_score", 0)
            await clear_whatsapp_session(phone)

            return f"""✅ *Complaint Successfully Registered!*

🆔 *Complaint ID:* {complaint_id}
📍 *Location:* {session_data.get('location', 'N/A')}
🔧 *Type:* {session_data.get('complaint_type', 'N/A').upper()}
⚠️ *Severity:* {severity}/10

Jald se jald action liya jaayega! 🙏
_Road Complaint System_"""

        elif any(w in t for w in ["nahi", "na", "no", "galat", "wrong", "cancel"]):
            await clear_whatsapp_session(phone)
            return "❌ Complaint cancel kar di. Dobara shuru karne ke liye *complaint* likhein."
        else:
            return "Reply karein: *haan* (register karein) ya *nahi* (cancel karein)"

    # ─── MENU ─────────────────────────────────────────────

    if any(w in t for w in ["hello", "hi", "helo", "namaskar", "namaste", "hey", "start"]):
        return """🛣️ *Road Complaint System mein Aapka Swagat Hai!*

Main aapki kaise madad kar sakta hun?

1️⃣ *complaint* — Nayi complaint register karein
2️⃣ *status* — Complaint status check karein
3️⃣ *help* — Help aur jankari

Reply mein number ya keyword bhejein! 😊"""

    elif t in ["1"] or any(w in t for w in ["complaint", "report", "pothole",
        "shikayat", "complain", "darj", "register"]):
        await save_whatsapp_session(phone, "complaint_type", {})
        return """📝 *Complaint Register Karein*

Kaunsi problem hai? Number bhejein:

1️⃣ Pothole (Gaddha)
2️⃣ Waterlogging (Paani bharana)
3️⃣ Drainage problem
4️⃣ Street Light band
5️⃣ Garbage/Kachra
6️⃣ Other"""

    elif t in ["2"] or any(w in t for w in ["status", "check"]):
        return """🔍 *Status Check*

Apna Complaint ID bhejein.
Format: *CMP-XXXXXXXX*"""

    elif t.startswith("cmp-"):
        return await get_complaint_status(t.upper())

    elif t in ["3"] or any(w in t for w in ["help", "madad"]):
        return """ℹ️ *Help*

- *complaint* — Nayi complaint
- *status* — Status check
- *CMP-XXXXXXXX* — Specific status
- *help* — Ye message"""

    else:
        return """🛣️ *Road Complaint System*

1️⃣ *complaint* — Nayi complaint
2️⃣ *status* — Status check
3️⃣ *help* — Help"""


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
            msg = "Aapki complaint process ho rahi hai. Jald action liya jaayega! 🙏" \
                if status == "pending" \
                else "Authority ne complaint assign kar li hai! 🔄" \
                if status == "assigned" \
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