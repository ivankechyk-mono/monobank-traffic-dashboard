"""Перевіряє доступ до Google Ads API і визначає правильний Customer ID."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_IDS = [
    os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
    os.getenv("GOOGLE_ADS_CUSTOMER_ID_ALT"),
]

config = {
    "developer_token": os.getenv("GOOGLE_ADS_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "use_proto_plus": True,
}

client = GoogleAdsClient.load_from_dict(config)

for customer_id in CUSTOMER_IDS:
    if not customer_id:
        continue
    print(f"\nПеревіряємо Customer ID: {customer_id}")
    try:
        ga_service = client.get_service("GoogleAdsService")
        query = """
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone
            FROM customer
            LIMIT 1
        """
        response = ga_service.search(customer_id=customer_id, query=query)
        for row in response:
            c = row.customer
            print(f"  ✅ OK — Name: {c.descriptive_name}, Currency: {c.currency_code}, TZ: {c.time_zone}")
    except GoogleAdsException as e:
        for error in e.failure.errors:
            print(f"  ❌ {error.error_code} — {error.message}")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
