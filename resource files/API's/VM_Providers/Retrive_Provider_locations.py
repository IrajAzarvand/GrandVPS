# provider_locations.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🌍 دریافت مپینگ ارائه‌دهندگان به لوکیشن‌ها...")

try:
    response = requests.get(
        f"{BASE_URL}/api/v1/vproviderlocation/",
        headers=headers,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        providers_data = data.get("data", {})
        
        print(f"✅ {len(providers_data)} ارائه‌دهنده یافت شد:")
        for provider_name, locations in providers_data.items():
            print(f"\n   🏢 {provider_name}:")
            for loc in locations:
                print(f"      - {loc.get('name')} ({loc.get('country')})")
                print(f"        کد لوکیشن: {loc.get('locationCode')}")
                print(f"        شهر: {loc.get('city')}")
                print(f"        منطقه: {loc.get('region')}")
                print("-" * 50)
    else:
        print("❌ خطا در دریافت مپینگ.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))