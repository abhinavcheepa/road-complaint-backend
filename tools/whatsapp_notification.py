import requests
import os

def send_whatsapp(phone_number: str, complaint_id: str, data: dict) -> dict:
    try:
        token = os.getenv("WHATSAPP_API_TOKEN")
        api_url = os.getenv("WHATSAPP_API_URL")
        
        message = f"""✅ *Complaint Registered Successfully!*

🆔 Complaint ID: {complaint_id}
📍 Location: {data.get('location', 'N/A')}
🔧 Issue: {data.get('complaint_type', 'N/A')}
⚠️ Severity: {data.get('severity_score', 'N/A')}/10
🏛️ Authority: {data.get('authority_assigned', {}).get('org_name', 'N/A')}

Aapki complaint register ho gayi hai. Jald hi action liya jaayega.
_Road Complaint System_"""

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message}
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(api_url, json=payload, headers=headers)
        
        return {
            "success": True,
            "message_sent": True,
            "response": response.json()
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}