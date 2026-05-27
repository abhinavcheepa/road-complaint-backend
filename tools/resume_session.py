from firebase_config import db

def resume_session(phone_number: str) -> dict:
    try:
        # Incomplete sessions dhundo
        sessions = db.collection("sessions")\
            .where("phone_number", "==", phone_number)\
            .where("partial_save", "==", True)\
            .order_by("timestamp", direction="DESCENDING")\
            .limit(1).stream()
        
        for doc in sessions:
            session_data = doc.to_dict()
            return {
                "success": True,
                "has_incomplete_session": True,
                "session_id": session_data.get("session_id"),
                "last_step": session_data.get("last_step"),
                "partial_data": session_data
            }
        
        return {
            "success": True,
            "has_incomplete_session": False
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_partial_session(data: dict, last_step: str):
    try:
        session_id = data.get("session_id")
        if not session_id:
            return {"success": False}
        
        data["partial_save"] = True
        data["last_step"] = last_step
        
        db.collection("sessions").document(session_id).set(data, merge=True)
        
        return {"success": True}
    
    except Exception as e:
        return {"success": False, "error": str(e)}