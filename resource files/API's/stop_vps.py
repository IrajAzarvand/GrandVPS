import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# کد سروری که قبلاً ساختی
vm_code = "ad6ef1dd-7ba3-40d9-8cdc-19ba1de56dd4"

print(f"🛑 در حال خاموش کردن سرور با کد: {vm_code} ...")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/vms/{vm_code}/stop/",
        headers=headers,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        vm_info = data.get("data", {})
        print("✅ سرور با موفقیت خاموش شد!")
        print(f"   نام سرور: {vm_info.get('name')}")
        print(f"   وضعیت جدید: {vm_info.get('status')}")
    else:
        print("❌ خطایی در خاموش کردن سرور رخ داده.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))