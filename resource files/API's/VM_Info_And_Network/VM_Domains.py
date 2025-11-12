# get_vm_domains.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "72a0ad10-80c8-4f96-b753-7f082eb29a98"  # ← اینو با کد واقعی سرورت عوض کن

print(f"🔍 دریافت لیست دامنه‌های سرور با کد: {VM_CODE} ...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vms/{VM_CODE}/domains/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", [])
        print(f"\n✅ {len(data)} دامنه یافت شد:")
        for domain in data:
            print(f"   - نام دامنه: {domain.get('name')}")
            print(f"     کد دامنه: {domain.get('id')}")
            print(f"     وضعیت: {'فعال' if domain.get('active', False) else 'غیرفعال'}")
            print(f"     تاریخ ایجاد: {domain.get('created', 'N/A')}")
            print("-" * 50)
    else:
        print("❌ خطا در دریافت لیست دامنه‌ها.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))