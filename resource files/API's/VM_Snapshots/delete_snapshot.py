# delete_snapshot.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

SNAPSHOT_CODE = "snap-abc123-def456-ghi789"  # ← کد استپشات

print(f"🗑️ در حال حذف استپشات با کد: {SNAPSHOT_CODE} ...")

try:
    response = requests.delete(
        f"{BASE_URL}/api/v1/snapshots/{SNAPSHOT_CODE}/",
        headers=headers,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        msg = data.get("msg", {})
        print("✅ استپشات با موفقیت حذف شد!")
        print(f"   پیام: {msg.get('msg_text', 'N/A')}")
    else:
        print("❌ خطا در حذف استپشات.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))