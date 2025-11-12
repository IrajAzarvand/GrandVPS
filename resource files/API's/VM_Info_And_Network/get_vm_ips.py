# get_vm_ips.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "7b0628bf-201f-40f1-b42f-f7f1df51f30e"  # ← اینو با کد واقعی سرورت عوض کن

print(f"🌐 دریافت لیست IPهای سرور با کد: {VM_CODE} ...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vms/{VM_CODE}/ips/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", [])
        print(f"\n✅ {len(data)} IP یافت شد:")
        for ip_info in data:
            print(f"   - آدرس IP: {ip_info.get('address')}")
            print(f"     نوع: {ip_info.get('version')} ({'IPv4' if ip_info.get('version') == '4' else 'IPv6'})")
            print(f"     وضعیت: {'فعال' if ip_info.get('status') == 'active' else 'غیرفعال'}")
            print(f"     تخصیص داده شده: {ip_info.get('assignedAt', 'N/A')}")
            print("-" * 50)
    else:
        print("❌ خطا در دریافت لیست IPها.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))