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
        logger.info("Starting NEX core services...")
        
        # Initialize Firebase Admin
        try:
            # Check if already initialized
            if not firebase_admin._apps:
                # In a real scenario, use a service account JSON file.
                # For now, we assume ADC (Application Default Credentials) 
                # or the environment is set up (e.g., GOOGLE_APPLICATION_CREDENTIALS)
                self.firebase_app = firebase_admin.initialize_app()
                logger.info("Firebase Admin initialized.")
            else:
                self.firebase_app = firebase_admin.get_app()
            
            self.db = firestore.client()
            logger.info("Firestore client initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            # In production, this might be a fatal error
            # For now, we continue but Firestore dependent features will fail

        # Initialize Gemini
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            genai.configure(api_key=google_api_key)
            logger.info("Gemini AI configured.")
        else:
            logger.warning("GOOGLE_API_KEY not found. NEX interaction will fail.")

services = Services()

def get_db():
    return services.db
