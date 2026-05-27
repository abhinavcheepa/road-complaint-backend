import requests
import os

def send_whatsapp(phone_number: str, complaint_id: str, data: dict) -> dict:
    try:
        token = os.getenv("WHATSAPP_API_TOKEN")
        api_url = os.getenv("WHATSAPP_API_URL")

        # Number format fix
        if not phone_number.startswith("+"):
            phone_number = "+91" + phone_number
        phone_number = phone_number.replace("+", "").replace("-", "").replace(" ", "")

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"}
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(api_url, json=payload, headers=headers)
        print("WHATSAPP RESPONSE:", response.json())

        return {
            "success": True,
            "message_sent": True,
            "complaint_id": complaint_id,
            "response": response.json()
        }

    except Exception as e:
        print("WHATSAPP ERROR:", e)
        return {"success": False, "error": str(e)}