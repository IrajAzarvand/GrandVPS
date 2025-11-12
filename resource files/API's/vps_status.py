import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"
VM_CODE = "36a04138-9389-4648-9c76-fb8ea37ebd02"  # کد سرور ساخته‌شده

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

url = f"{BASE_URL}/api/v1/vms/{VM_CODE}/"

print(f"🔍 دریافت اطلاعات سرور با کد: {VM_CODE} ...")

try:
    response = requests.get(url, headers=headers, timeout=15)
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        vm_info = data.get("data", {})
        print("✅ اطلاعات سرور با موفقیت دریافت شد:")
        print(f"   نام سرور: {vm_info.get('name')}")
        print(f"   وضعیت: {vm_info.get('status')}")
        print(f"   IP: {vm_info.get('ipv4')}")
        print(f"   لوکیشن: {vm_info.get('locationName')}")
        print(f"   پلن: {vm_info.get('vmachineTypeId')}")
        print(f"   سیستم‌عامل: {vm_info.get('osName')}")
        print(f"   CPU: {vm_info.get('cpu')}, RAM: {vm_info.get('ramGb')} GB, SSD: {vm_info.get('ssdGb')} GB")
    else:
        print("❌ خطا در دریافت اطلاعات سرور.")
        print("متن پاسخ:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))