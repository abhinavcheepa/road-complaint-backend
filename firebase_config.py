import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv

load_dotenv()

# File path ya JSON string dono handle karo
firebase_creds = os.getenv("FIREBASE_CREDENTIALS")

try:
    # Pehle JSON string try karo
    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
except:
    # File path se load karo
    cred = credentials.Certificate(firebase_creds)

firebase_admin.initialize_app(cred)
db = firestore.client()