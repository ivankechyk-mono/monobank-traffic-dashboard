import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("META_TOKEN")
if not token:
    print("ERROR: META_TOKEN not found in .env")
    exit(1)

# Перевіряємо токен через Meta Graph API /me
resp = requests.get(
    "https://graph.facebook.com/v20.0/me",
    params={"access_token": token, "fields": "id,name"},
)
data = resp.json()

if "error" in data:
    print(f"FAIL: {data['error']['message']} (code: {data['error']['code']})")
    exit(1)

print(f"OK: токен валідний — id={data.get('id')}, name={data.get('name')}")

# Перевіряємо доступ до рекламних акаунтів
resp2 = requests.get(
    "https://graph.facebook.com/v20.0/me/adaccounts",
    params={"access_token": token, "fields": "id,name,account_status"},
)
data2 = resp2.json()

if "error" in data2:
    print(f"WARN: немає доступу до Ad Accounts — {data2['error']['message']}")
else:
    accounts = data2.get("data", [])
    if not accounts:
        print("WARN: токен валідний але рекламних акаунтів не знайдено")
    else:
        print(f"Ad Accounts ({len(accounts)}):")
        for acc in accounts:
            status = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED"}.get(acc.get("account_status"), "UNKNOWN")
            print(f"  {acc['id']} — {acc['name']} [{status}]")
