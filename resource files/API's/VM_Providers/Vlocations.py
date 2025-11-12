# vlocations.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🌍 دریافت لیست لوکیشن‌ها و پلن‌ها...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/vlocations/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", {})
        
        # نمایش لوکیشن‌ها
        locations = data.get("locationsList", [])
        print(f"\n✅ {len(locations)} لوکیشن یافت شد:")
        for loc in locations:
            print(f"   - {loc.get('name')} ({loc.get('country')})")
            print(f"     کد لوکیشن: {loc.get('locationCode')}")
            print(f"     ارائه‌دهنده: {loc.get('idFromProvider')}")
            print("-" * 50)
        
        # نمایش ارائه‌دهندگان
        providers = data.get("providerCategoriesMapping", {})
        print(f"\n✅ {len(providers)} ارائه‌دهنده یافت شد:")
        for provider_name in providers.keys():
            print(f"   - {provider_name}")
        
        # نمایش پلن‌ها (بر اساس لوکیشن)
        location_mapping = data.get("locationMachineTypeMapping", {})
        print(f"\n✅ مپینگ لوکیشن به پلن‌ها:")
        for location_code, mapping in location_mapping.items():
            print(f"   📍 {location_code}:")
            for category, plans in mapping.items():
                print(f"      - {category}:")
                for plan in plans:
                    print(f"          • {plan.get('name')} | {plan.get('cpu')} CPU | {plan.get('ramGb')} GB RAM | ${plan.get('monthlyPriceUsd')}/month")
            print("-" * 50)
            
    else:
        print("❌ خطا در دریافت داده‌ها.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))