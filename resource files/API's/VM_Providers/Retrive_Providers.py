import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🔍 دریافت لیست ارائه‌دهندگان از داده‌های vlocations...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vlocations/", headers=headers, timeout=30)
    
    if response.status_code != 200:
        print("❌ خطا در دریافت داده‌ها.")
        print("متن خطا:", response.text)
        exit()

    data = response.json().get("data", {})
    machine_mapping = data.get("locationCategoryMachineTypeMapping", {})

    # استخراج لیست ارائه‌دهندگان از کلیدهای machine_mapping
    providers = list(machine_mapping.keys())

    print(f"\n✅ ارائه‌دهندگان یافت شده ({len(providers)} مورد):")
    for provider in providers:
        print(f"   - {provider}")

except Exception as e:
    print("❗ خطای اجرایی:", str(e))