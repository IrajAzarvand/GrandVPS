# get_snapshot_details.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

SNAPSHOT_CODE = "snap-abc123-def456-ghi789"  # ← کد استپشات (از خروجی create_snapshot.py)

print(f"🔍 دریافت جزئیات استپشات با کد: {SNAPSHOT_CODE} ...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/snapshots/{SNAPSHOT_CODE}/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", {}).get("snapshot", {})
        print("✅ جزئیات استپشات:")
        print(f"   نام: {data.get('name')}")
        print(f"   کد: {data.get('snapshotCode')}")
        print(f"   ارائه‌دهنده: {data.get('provider')}")
        print(f"   لوکیشن: {data.get('location')} ({data.get('country')})")
        print(f"   حجم: {data.get('sizeGb', 0)} GB")
        print(f"   وضعیت: {data.get('status')}")
        print(f"   تاریخ ایجاد: {data.get('created', 'N/A')}")
        print(f"   توضیحات: {data.get('description', 'N/A')}")
        print(f"   سرور مرتبط: {data.get('vm', {}).get('name', 'N/A')}")
    else:
        print("❌ خطا در دریافت جزئیات استپشات.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))