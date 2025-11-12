# create_snapshot.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "7b0628bf-201f-40f1-b42f-f7f1df51f30e"  # ← کد سرورت
SNAPSHOT_NAME = "Backup_2025_11_07"                 # ← نام استپشات
DESCRIPTION = "Backup before major update"         # ← توضیحات

print(f"📸 در حال ایجاد استپشات '{SNAPSHOT_NAME}' برای سرور با کد: {VM_CODE} ...")

payload = {
    "vm_code": VM_CODE,
    "description": DESCRIPTION
}

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/snapshots/",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 201:
        data = response.json()
        msg = data.get("msg", {})
        print("✅ استپشات با موفقیت ایجاد شد!")
        print(f"   کد استپشات: {msg.get('msg_text', 'N/A')}")
    else:
        print("❌ خطا در ایجاد استپشات.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))