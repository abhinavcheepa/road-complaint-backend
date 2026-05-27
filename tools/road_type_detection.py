import requests
from firebase_config import db

def detect_road_type(location: str) -> dict:
    try:
        osm_geo_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
        geo_response = requests.get(
            osm_geo_url,
            headers={"User-Agent": "road-complaint-app"},
            timeout=5  # 👈 5 second timeout
        ).json()

        coordinates = None
        if geo_response:
            coordinates = {
                "lat": geo_response[0]["lat"],
                "lng": geo_response[0]["lon"]
            }

        # Firebase check
        roads_ref = db.collection("roads")
        docs = roads_ref.where("area", "==", location).stream()
        for doc in docs:
            road_data = doc.to_dict()
            return {
                "success": True,
                "road_type": road_data.get("road_type", "Unknown"),
                "road_name": road_data.get("road_name", ""),
                "coordinates": coordinates,
                "source": "database"
            }

        # OpenStreetMap reverse geocoding
        if coordinates:
            reverse_url = f"https://nominatim.openstreetmap.org/reverse?lat={coordinates['lat']}&lon={coordinates['lng']}&format=json"
            osm_response = requests.get(
                reverse_url,
                headers={"User-Agent": "road-complaint-app"},
                timeout=5  # 👈 5 second timeout
            ).json()

            road_ref = osm_response.get("address", {}).get("road", "")

            if "NH" in road_ref or "National" in road_ref:
                road_type = "NH"
            elif "SH" in road_ref or "State" in road_ref:
                road_type = "SH"
            elif "MDR" in road_ref or "Major District" in road_ref:
                road_type = "MDR"
            else:
                road_type = "City Road"

            return {
                "success": True,
                "road_type": road_type,
                "road_name": road_ref,
                "coordinates": coordinates,
                "source": "openstreetmap"
            }

        return {
            "success": True,
            "road_type": "Unknown",
            "coordinates": None,
            "source": "not_found"
        }

    except Exception as e:
        print("Road type error:", e)
        return {
            "success": False,
            "road_type": "Unknown",
            "error": str(e)
        }