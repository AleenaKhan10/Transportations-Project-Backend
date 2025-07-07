from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    DITAT_TOKEN = os.getenv("DITAT_TOKEN")
    SAMSARA_TOKEN = os.getenv("SAMSARA_TOKEN")
    DUMMY_TOKEN = os.getenv("DUMMY_TOKEN")