import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# کد سروری که قبلاً ساختی (مثلاً از خروجی create_vps.py)
vm_code = "72a0ad10-80c8-4f96-b753-7f082eb29a98"  # 👈 اینجا کد سرورتو جایگزین کن

payload = {
    "command": "shutdown"  # یا "turnon" یا "reboot"
}

print(f"🛑 در حال خاموش کردن سرور با کد: {vm_code} ...")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/vms/{vm_code}/commands/",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ دستور با موفقیت اجرا شد!")
        print("پیام:", data.get("msg", {}).get("msg_text"))
    else:
        print("❌ خطایی در اجرای دستور رخ داده.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))