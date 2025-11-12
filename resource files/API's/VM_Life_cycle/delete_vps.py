import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# کد سروری که قبلاً ساختی (مثلاً از خروجی create_vps.py)
vm_code = "db3ce65c-9ad8-43ee-ba37-340e0885980f"

print(f"🗑️ در حال حذف سرور با کد: {vm_code} ...")

try:
    response = requests.delete(
        f"{BASE_URL}/api/v1/vms/{vm_code}/",
        headers=headers,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ سرور با موفقیت حذف شد!")
        print("پیام:", data.get("msg", {}).get("msg_text"))
    else:
        print("❌ خطایی در حذف سرور رخ داده.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))