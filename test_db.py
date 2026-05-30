from firebase_config import db

docs = db.collection('driver_warnings').stream()
for doc in docs:
    d = doc.to_dict()
    print(doc.id, d)