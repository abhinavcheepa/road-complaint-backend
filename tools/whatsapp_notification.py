import requests
import os

def send_whatsapp(phone_number: str, complaint_id: str, data: dict) -> dict:
    try:
        api_token = os.getenv("WASENDER_API_TOKEN")
        session = os.getenv("WASENDER_SESSION", "road-complaint-bot")

        # Number format fix
        phone_number = str(phone_number).strip()
        phone_number = phone_number.replace(" ", "").replace("-", "")
        
        if phone_number.startswith("+"):
            phone_number = phone_number[1:]
        elif phone_number.startswith("0"):
            phone_number = "91" + phone_number[1:]
        elif not phone_number.startswith("91"):
            phone_number = "91" + phone_number

        # Authority name nikalo
        authority = data.get("authority_assigned", {})
        if isinstance(authority, dict):
            authority_name = authority.get("org_name", "Local Municipality")
        else:
            authority_name = "Local Municipality"

        message = f"""✅ *Complaint Registered Successfully!*

🆔 *Complaint ID:* {complaint_id}
📍 *Location:* {data.get('location', 'N/A')}
🔧 *Issue:* {data.get('complaint_type', 'N/A')}
⚠️ *Severity:* {data.get('severity_score', 'N/A')}/10
🏛️ *Authority:* {authority_name}

Aapki complaint register ho gayi hai.
Jald hi action liya jaayega. 🙏

_Road Complaint System_"""

        url = f"https://api.wasenderapi.com/api/send-message"

        payload = {
            "session": session,
            "to": f"{phone_number}@s.whatsapp.net",
            "text": message
        }

        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()
        print("WASENDER RESPONSE:", response_json)

        if response.status_code == 200:
            return {
                "success": True,
                "message_sent": True,
                "complaint_id": complaint_id,
                "response": response_json
            }
        else:
            return {
                "success": False,
                "error": response_json.get("message", "Unknown error"),
                "code": response.status_code
            }

    except Exception as e:
        print("WHATSAPP ERROR:", e)
        return {"success": False, "error": str(e)}