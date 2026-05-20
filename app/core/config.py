from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Job Scraper API")
DEBUG = os.getenv("DEBUG", "False") == "True"