import os
import firebase_admin
from firebase_admin import credentials, firestore
from loguru import logger
import google.generativeai as genai

class Services:
    def __init__(self):
        self.db = None
        self.firebase_app = None

    async def init_services(self):
        """
        Initialize all core services (Firebase, Firestore, Gemini).
        """
        logger.info(f"Starting NEX core services... Instance ID: {id(self)}")
        
        # Initialize Firebase Admin
        # Initialize Firebase Admin
        try:
            # Check if already initialized
            if not firebase_admin._apps:
                cred = None
                service_account_path = "/app/service_account.json"
                
                if os.path.exists(service_account_path):
                    logger.info(f"Found service account at {service_account_path}")
                    cred = credentials.Certificate(service_account_path)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                else:
                    # Fallback to ADC
                    logger.info("No service account found at /app/service_account.json, using ADC.")
                    self.firebase_app = firebase_admin.initialize_app()
                
                logger.info("Firebase Admin initialized.")
            else:
                self.firebase_app = firebase_admin.get_app()
            
            self.db = firestore.client()
            logger.info(f"Firestore client initialized. DB Object: {self.db}")
        except Exception as e:
            logger.critical(f"Failed to initialize Firebase: {e}")
            raise e

        # Initialize Gemini
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            genai.configure(api_key=google_api_key)
            logger.info("Gemini AI configured.")
        else:
            logger.warning("GOOGLE_API_KEY not found. NEX interaction will fail.")

services = Services()

def get_db():
    logger.debug(f"Accessing DB from Services instance {id(services)}. DB state: {services.db}")
    return services.db
