import requests
import os
from requests.auth import HTTPBasicAuth

def send_whatsapp(phone_number: str, complaint_id: str, data: dict) -> dict:
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = "whatsapp:+14155238886"

        # Number format fix
        phone_number = str(phone_number).strip()
        phone_number = phone_number.replace(" ", "").replace("-", "")
        
        if not phone_number.startswith("+"):
            if phone_number.startswith("91"):
                phone_number = "+" + phone_number
            else:
                phone_number = "+91" + phone_number
        
        to_number = f"whatsapp:{phone_number}"

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

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        response = requests.post(
            url,
            data={
                "From": from_number,
                "To": to_number,
                "Body": message
            },
            auth=HTTPBasicAuth(account_sid, auth_token)
        )

        response_json = response.json()
        print("TWILIO RESPONSE:", response_json)

        if response.status_code == 201:
            return {
                "success": True,
                "message_sent": True,
                "complaint_id": complaint_id,
                "message_sid": response_json.get("sid", "")
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