from firebase_config import db

def lookup_authority(road_type: str, location: str) -> dict:
    try:
        # Default authority return karo agar database mein nahi mila
        default_authority = {
            "org_name": "Local Municipal Corporation",
            "contact": "1800-180-1234",
            "executive_engineer": "District Engineer",
            "area_covered": location
        }

        if not road_type or road_type == "Unknown":
            return {
                "success": True,
                "authority": default_authority
            }

        try:
            docs = db.collection("authorities").where(
                "road_type_covered", "array_contains", road_type
            ).limit(1).stream()

            for doc in docs:
                auth = doc.to_dict()
                return {
                    "success": True,
                    "authority": {
                        "org_name": auth.get("org_name", ""),
                        "contact": auth.get("contact", ""),
                        "executive_engineer": auth.get("executive_engineer", ""),
                        "area_covered": auth.get("area_covered", location)
                    }
                }
        except:
            pass

        return {
            "success": True,
            "authority": default_authority
        }

    except Exception as e:
        print("Authority lookup error:", e)
        return {
            "success": True,
            "authority": {
                "org_name": "Local Municipal Corporation",
                "contact": "1800-180-1234",
                "executive_engineer": "District Engineer",
                "area_covered": location
            }
        }