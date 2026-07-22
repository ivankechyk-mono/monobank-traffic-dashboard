"""Перевірка: які сторінки GSC повертають product=Unknown"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from google.oauth2.credentials import Credentials
from src.connectors.gsc import GSCConnector

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

creds = Credentials.from_authorized_user_file("token.json", SCOPES)
gsc = GSCConnector(site_url="https://monobank.ua/", credentials=creds)
df = gsc.get_keywords(date_range=("2026-07-13", "2026-07-19"))

unknown = df[df["product"] == "Unknown"][["query", "page", "clicks"]].sort_values("clicks", ascending=False)
print(f"Unknown рядків: {len(unknown)}")
print(unknown.head(20).to_string(index=False))
