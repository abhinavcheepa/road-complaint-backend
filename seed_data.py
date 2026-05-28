from firebase_config import db
from datetime import datetime

def seed_authorities():
    authorities = [
        # National Highway Authority
        {
            "org_name": "National Highways Authority of India (NHAI)",
            "road_type_covered": ["NH"],
            "area_covered": "All India",
            "contact": "1800-111-581",
            "executive_engineer": "Regional Officer NHAI",
            "email": "ro.bhopal@nhai.org",
            "state": "Madhya Pradesh",
            "city": "Bhopal"
        },
        # State Highway Authority MP
        {
            "org_name": "MP Road Development Corporation (MPRDC)",
            "road_type_covered": ["SH"],
            "area_covered": "Madhya Pradesh",
            "contact": "0755-2573737",
            "executive_engineer": "Executive Engineer MPRDC",
            "email": "ee.bhopal@mprdc.org",
            "state": "Madhya Pradesh",
            "city": "Bhopal"
        },
        # MDR Authority
        {
            "org_name": "Public Works Department (PWD) MP",
            "road_type_covered": ["MDR", "SH"],
            "area_covered": "Madhya Pradesh",
            "contact": "0755-2441600",
            "executive_engineer": "Executive Engineer PWD",
            "email": "ee.pwd.bhopal@mp.gov.in",
            "state": "Madhya Pradesh",
            "city": "Bhopal"
        },
        # Local/City Roads
        {
            "org_name": "Bhopal Municipal Corporation (BMC)",
            "road_type_covered": ["City Road", "Local Road", "Unknown"],
            "area_covered": "Bhopal",
            "contact": "0755-2700000",
            "executive_engineer": "City Engineer BMC",
            "email": "cityengineer@bmcbhopal.com",
            "state": "Madhya Pradesh",
            "city": "Bhopal"
        },
        {
            "org_name": "Indore Municipal Corporation (IMC)",
            "road_type_covered": ["City Road", "Local Road"],
            "area_covered": "Indore",
            "contact": "0731-2530900",
            "executive_engineer": "City Engineer IMC",
            "email": "engineer@imcindore.org",
            "state": "Madhya Pradesh",
            "city": "Indore"
        },
        {
            "org_name": "Jabalpur Municipal Corporation",
            "road_type_covered": ["City Road", "Local Road"],
            "area_covered": "Jabalpur",
            "contact": "0761-2622300",
            "executive_engineer": "City Engineer JMC",
            "email": "engineer@jmc.gov.in",
            "state": "Madhya Pradesh",
            "city": "Jabalpur"
        },
        # General fallback
        {
            "org_name": "Local Municipal Corporation",
            "road_type_covered": ["City Road", "Local Road", "Unknown"],
            "area_covered": "General",
            "contact": "1800-180-1234",
            "executive_engineer": "District Engineer",
            "email": "complaints@municipality.gov.in",
            "state": "General",
            "city": "General"
        }
    ]

    for auth in authorities:
        auth["created_at"] = datetime.utcnow().isoformat()
        db.collection("authorities").add(auth)
        print(f"✅ Added: {auth['org_name']}")

def seed_roads():
    roads = [
        {
            "road_name": "NH-46 Bhopal-Jabalpur Highway",
            "road_type": "NH",
            "road_number": "NH-46",
            "area": "Bhopal",
            "state": "Madhya Pradesh",
            "start_point": "Bhopal",
            "end_point": "Jabalpur",
            "last_relaying_date": "2023-03-15",
            "contractor_name": "L&T Construction",
            "amount_sanctioned": 5000000,
            "amount_spent": 4500000
        },
        {
            "road_name": "NH-12 Bhopal-Nagpur Highway",
            "road_type": "NH",
            "road_number": "NH-12",
            "area": "Bhopal",
            "state": "Madhya Pradesh",
            "start_point": "Bhopal",
            "end_point": "Nagpur",
            "last_relaying_date": "2022-11-20",
            "contractor_name": "Shapoorji Pallonji",
            "amount_sanctioned": 8000000,
            "amount_spent": 7800000
        },
        {
            "road_name": "SH-18 Bhopal-Sehore Road",
            "road_type": "SH",
            "road_number": "SH-18",
            "area": "Bhopal",
            "state": "Madhya Pradesh",
            "start_point": "Bhopal",
            "end_point": "Sehore",
            "last_relaying_date": "2023-06-10",
            "contractor_name": "MP Roads Pvt Ltd",
            "amount_sanctioned": 2000000,
            "amount_spent": 1800000
        },
        {
            "road_name": "SH-22 Bhopal-Vidisha Road",
            "road_type": "SH",
            "road_number": "SH-22",
            "area": "Bhopal",
            "state": "Madhya Pradesh",
            "start_point": "Bhopal",
            "end_point": "Vidisha",
            "last_relaying_date": "2022-08-05",
            "contractor_name": "MPRDC Contractor",
            "amount_sanctioned": 1500000,
            "amount_spent": 1400000
        },
        {
            "road_name": "MP Nagar Main Road",
            "road_type": "City Road",
            "road_number": "BMC-001",
            "area": "MP Nagar",
            "state": "Madhya Pradesh",
            "start_point": "MP Nagar Zone 1",
            "end_point": "MP Nagar Zone 2",
            "last_relaying_date": "2023-01-12",
            "contractor_name": "BMC Contractor",
            "amount_sanctioned": 500000,
            "amount_spent": 480000
        },
        {
            "road_name": "Bina-Khurai Road",
            "road_type": "NH",
            "road_number": "NH-50",
            "area": "Bina",
            "state": "Madhya Pradesh",
            "start_point": "Bina",
            "end_point": "Khurai",
            "last_relaying_date": "2022-05-20",
            "contractor_name": "NHAI Contractor",
            "amount_sanctioned": 3000000,
            "amount_spent": 2900000
        }
    ]

    for road in roads:
        road["created_at"] = datetime.utcnow().isoformat()
        db.collection("roads").add(road)
        print(f"✅ Added road: {road['road_name']}")

def seed_all():
    print("🌱 Seeding Firebase Database...")
    print("\n📍 Adding Authorities...")
    seed_authorities()
    print("\n🛣️ Adding Roads...")
    seed_roads()
    print("\n✅ Database seeding complete!")

if __name__ == "__main__":
    seed_all()