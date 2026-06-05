import os, requests
from dotenv import load_dotenv
load_dotenv()

headers = {
    "Authorization": f"Bearer {os.getenv('BILLZ_BEARER_TOKEN')}",
    "Cookie": os.getenv("BILLZ_COOKIE") or "",
    "platform-id": os.getenv("BILLZ_PLATFORM_ID"),
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0"
}

URL = "https://kinder-kids-integro.billz.ai/api/v2/import"

dates = [
    "2026-05-29", "2026-05-30", "2026-05-31",
    "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"
]

grand_total_docs = 0
grand_total_qty  = 0

for date in dates:
    r = requests.get(URL, headers=headers, params={
        "limit": 20, "start_date": date, "end_date": date
    }, timeout=30)
    docs = r.json().get("imports", [])
    qty  = sum(d.get("total_arrived_measurement_value", 0) for d in docs)
    warn = "⚠️ LIMIT!" if len(docs) >= 20 else "✅"
    print(f"{date} → {len(docs):2d} ta hujjat | {qty:5.0f} dona {warn}")
    grand_total_docs += len(docs)
    grand_total_qty  += qty

print(f"\nJAMI: {grand_total_docs} ta hujjat | {grand_total_qty:.0f} dona")