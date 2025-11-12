# get_vm_details.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "72a0ad10-80c8-4f96-b753-7f082eb29a98"  # ← اینو با کد واقعی سرورت عوض کن

print(f"🔍 دریافت جزئیات سرور با کد: {VM_CODE} ...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vms/{VM_CODE}/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", {})
        print("✅ جزئیات سرور:")
        print(f"   نام: {data.get('name')}")
        print(f"   کد: {data.get('vmCode')}")
        print(f"   ارائه‌دهنده: {data.get('provider')}")
        print(f"   لوکیشن: {data.get('locationName')} ({data.get('country')})")
        print(f"   وضعیت: {data.get('status')}")
        print(f"   IP عمومی: {data.get('ipv4', 'N/A')}")
        print(f"   IP خصوصی: {data.get('ipv4Private', 'N/A')}")
        print(f"   سیستم‌عامل: {data.get('os', 'N/A')}")
        print(f"   CPU: {data.get('cpu', 'N/A')} | RAM: {data.get('ramGb', 'N/A')}GB | SSD: {data.get('ssdGb', 'N/A')}GB")
        print(f"   تاریخ ایجاد: {data.get('created', 'N/A')}")
    else:
        print("❌ خطا در دریافت جزئیات سرور.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))