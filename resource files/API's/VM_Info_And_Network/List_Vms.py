# list_vms.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🔍 دریافت لیست تمام سرورهای من...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vms/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        vms = data.get("data", [])
        
        print(f"\n✅ {len(vms)} سرور یافت شد:")
        for vm in vms:
            print(f"   - نام: {vm.get('name')} (کد: {vm.get('vmCode')})")
            print(f"     ارائه‌دهنده: {vm.get('provider')}")
            print(f"     لوکیشن: {vm.get('locationName')} ({vm.get('country')})")
            print(f"     وضعیت: {vm.get('status')}")
            print(f"     IP: {vm.get('ipv4', 'N/A')}")
            print("-" * 50)
    else:
        print("❌ خطا در دریافت لیست سرورها.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))