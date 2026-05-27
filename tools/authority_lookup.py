from firebase_config import db

def lookup_authority(road_type: str, location: str) -> dict:
    try:
        # Database se authority dhundo
        auth_ref = db.collection("authorities")
        
        # Pehle exact match try karo
        docs = auth_ref.where("road_type_covered", "array_contains", road_type).stream()
        
        for doc in docs:
            auth = doc.to_dict()
            # Area match check
            if location.lower() in auth.get("area_covered", "").lower():
                return {
                    "success": True,
                    "authority": {
                        "org_name": auth.get("org_name", ""),
                        "contact": auth.get("contact", ""),
                        "executive_engineer": auth.get("executive_engineer", ""),
                        "area_covered": auth.get("area_covered", "")
                    }
                }
        
        # General match (location ignore)
        docs2 = auth_ref.where("road_type_covered", "array_contains", road_type).limit(1).stream()
        for doc in docs2:
            auth = doc.to_dict()
            return {
                "success": True,
                "authority": {
                    "org_name": auth.get("org_name", ""),
                    "contact": auth.get("contact", ""),
                    "executive_engineer": auth.get("executive_engineer", ""),
                    "area_covered": auth.get("area_covered", "")
                }
            }
        
        return {
            "success": True,
            "authority": {
                "org_name": "Local Municipality",
                "contact": "1800-XXX-XXXX",
                "executive_engineer": "Not Assigned",
                "area_covered": location
            }
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}