import requests
import uuid

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# --- ابتدا لیست لوکیشن‌ها و پلن‌ها رو بگیریم ---
print("🔍 دریافت لیست لوکیشن‌ها و پلن‌ها...")
response_locations = requests.get(f"{BASE_URL}/api/v1/vlocations/", headers=headers)
if response_locations.status_code != 200:
    print("❌ خطای دریافت داده‌ها از vlocations.")
    exit()

location_data = response_locations.json().get("data", {})
locations_map = {loc["locationCode"]: loc for loc in location_data.get("locationsList", [])}
machine_mapping = location_data.get("locationMachineTypeMapping", {})

# --- اطلاعات سرور ---
location_code = "f7345771-cda3-4843-9c80-cd07a0f31d4f"  # Germany, Falkenstein
machine_type_code = "e95e1de4-5798-458b-a518-7ca7a4ab8763"  # H1
os_slug = "ubuntu_24_04"
provider_name = "Hetzner"
vm_name = f"test-vm-{uuid.uuid4().hex[:8]}"

# --- پیدا کردن قیمت ساعتی از داده‌های قبلی ---
hourly_price_usd = None
if location_code in machine_mapping:
    for plan in machine_mapping[location_code]:
        if plan.get("machineCode") == machine_type_code:
            hourly_price_usd = plan.get("hourlyPriceUsd")
            break

# --- ارسال درخواست ساخت سرور ---
payload = {
    "location_code": location_code,
    "machine_type_code": machine_type_code,
    "name": vm_name,
    "os_slug": os_slug,
    "provider_name": provider_name
}

print(f"\n🚀 در حال ایجاد سرور با نام: {vm_name} ...")
print(f"   ارائه‌دهنده: {provider_name}")
print(f"   لوکیشن: {locations_map.get(location_code, {}).get('name', 'Unknown')}")
print(f"   پلن: H1 (2 CPU, 4GB RAM, 40GB SSD)")
print(f"   سیستم‌عامل: Ubuntu 24.04")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/vms/",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code >= 200 and response.status_code < 300:
        data = response.json()
        vm_info = data.get("data", {})
        
        print("✅ سرور با موفقیت ساخته شد!")
        print(f"   نام سرور: {vm_info.get('name')}")
        print(f"   کد سرور: {vm_info.get('vmCode')}")
        print(f"   وضعیت: {vm_info.get('status')}")
        print(f"   IP: {vm_info.get('ipv4')}")
        
        # ✅ اینجا قیمت ساعتی رو از داده‌های قبلی نشون می‌دیم
        if hourly_price_usd is not None:
            print(f"   هزینه ساعتی: {hourly_price_usd} دلار")
        else:
            print("   هزینه ساعتی: نامشخص (خطا در یافتن قیمت)")

    else:
        print("❌ خطا در ساخت سرور.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))