# list_snapshots.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🔍 دریافت لیست استپشات‌ها...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/snapshots/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        snapshots_list = data.get("data", {}).get("snapshots", [])
        
        if not snapshots_list:
            print("✅ هیچ استپشاتی یافت نشد.")
        else:
            print(f"\n✅ {len(snapshots_list)} استپشات یافت شد:")
            for i, snap_code in enumerate(snapshots_list, 1):
                print(f"   {i}. {snap_code}")
    else:
        print("❌ خطا در دریافت لیست استپشات‌ها.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))