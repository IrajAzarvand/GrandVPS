# get_vm_status.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "72a0ad10-80c8-4f96-b753-7f082eb29a98"  # ← اینو با کد واقعی سرورت عوض کن

print(f"🔄 دریافت وضعیت سرور با کد: {VM_CODE} ...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vms/{VM_CODE}/status/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", {})
        status = data.get("status", "N/A")
        is_active = data.get("isActive", False)
        
        print(f"✅ وضعیت فعلی: {status}")
        print(f"   فعال است؟: {'✅ بله' if is_active else '❌ خیر'}")
    else:
        print("❌ خطا در دریافت وضعیت سرور.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))