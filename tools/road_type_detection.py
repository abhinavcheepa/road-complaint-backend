import requests
import os
from firebase_config import db

def detect_road_type(location: str) -> dict:
    try:
        # Step 1: Google Maps se coordinates lo
        maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={maps_key}"
        geo_response = requests.get(geo_url).json()
        
        coordinates = None
        if geo_response["status"] == "OK":
            loc = geo_response["results"][0]["geometry"]["location"]
            coordinates = {"lat": loc["lat"], "lng": loc["lng"]}
        
        # Step 2: Database se check karo
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
        
        # Step 3: OpenStreetMap fallback
        if coordinates:
            osm_url = f"https://nominatim.openstreetmap.org/reverse?lat={coordinates['lat']}&lon={coordinates['lng']}&format=json"
            osm_response = requests.get(osm_url, headers={"User-Agent": "road-complaint-app"}).json()
            
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
            "coordinates": coordinates,
            "source": "not_found"
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}