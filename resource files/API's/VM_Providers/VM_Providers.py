# providers.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def get_providers():
    """دریافت لیست ارائه‌دهندگان (مثل Hetzner، DigitalOcean و ...)."""
    response = requests.get(f"{BASE_URL}/api/v1/vlocations/", headers=headers)
    if response.status_code != 200:
        print("❌ خطا در دریافت ارائه‌دهندگان.")
        return []

    data = response.json().get("data", {})
    provider_mapping = data.get("providerCategoriesMapping", {})
    return list(provider_mapping.keys())

def get_locations():
    """دریافت لیست تمام لوکیشن‌های فعال."""
    response = requests.get(f"{BASE_URL}/api/v1/vlocations/", headers=headers)
    if response.status_code != 200:
        print("❌ خطا در دریافت لوکیشن‌ها.")
        return []

    data = response.json().get("data", {})
    locations = data.get("locationsList", [])
    return [
        {
            "name": loc["name"],
            "location_code": loc["locationCode"],
            "provider": loc.get("provider", "Unknown"),
            "country": loc["country"],
            "city": loc["city"]
        }
        for loc in locations if loc.get("active", False)
    ]

def get_plans_by_location(location_code):
    """دریافت لیست پلن‌های یک لوکیشن خاص بر اساس location_code."""
    response = requests.get(f"{BASE_URL}/api/v1/vlocations/", headers=headers)
    if response.status_code != 200:
        print("❌ خطا در دریافت پلن‌ها.")
        return []

    data = response.json().get("data", {})
    location_mapping = data.get("locationMachineTypeMapping", {})
    plans = location_mapping.get(location_code, {})
    
    # برخی لوکیشن‌ها فقط یک دسته (مثل "Standard") دارند
    if isinstance(plans, dict):
        plans = next(iter(plans.values()), [])
    elif isinstance(plans, list):
        pass
    else:
        plans = []

    return [
        {
            "name": p["name"],
            "machine_code": p["machineCode"],
            "cpu": p["cpu"],
            "ram_gb": p["ramGb"],
            "ssd_gb": p["ssdGb"],
            "hourly_price_usd": p["hourlyPriceUsd"],
            "monthly_price_usd": p["monthlyPriceUsd"],
            "traffic_gb": p.get("monthlyTrafficGb", 0)
        }
        for p in plans
    ]

def get_all_os():
    """دریافت لیست تمام سیستم‌عامل‌ها از همه ارائه‌دهندگان."""
    response = requests.get(f"{BASE_URL}/api/v1/os/", headers=headers)
    if response.status_code != 200:
        print("❌ خطا در دریافت سیستم‌عامل‌ها.")
        return []

    data = response.json()
    os_map = data.get("os_map", data.get("data", {}))
    all_os = []
    for provider, os_list in os_map.items():
        for os in os_list:
            if os.get("name") and os.get("slug"):
                all_os.append({
                    "name": os["name"],
                    "slug": os["slug"],
                    "provider": provider,
                    "logo": os.get("logo")
                })
    return all_os

# --- مثال استفاده ---
if __name__ == "__main__":
    print("✅ لیست ارائه‌دهندگان:")
    providers = get_providers()
    for p in providers:
        print(f"   - {p}")

    print("\n✅ نمونه لوکیشن‌ها:")
    locations = get_locations()[:3]  # فقط ۳ تا
    for loc in locations:
        print(f"   - {loc['name']} ({loc['country']}) - کد: {loc['location_code']}")

    print("\n✅ پلن‌های لوکیشن نمونه (Germany, Falkenstein):")
    sample_loc_code = "f7345771-cda3-4843-9c80-cd07a0f31d4f"
    plans = get_plans_by_location(sample_loc_code)
    for plan in plans[:2]:  # فقط ۲ تا
        print(f"   - {plan['name']}: {plan['cpu']} CPU, {plan['ram_gb']} GB RAM → ${plan['hourly_price_usd']}/ساعت")

    print("\n✅ نمونه سیستم‌عامل‌ها:")
    os_list = get_all_os()[:5]
    for os in os_list:
        print(f"   - {os['name']} ({os['slug']}) → {os['provider']}")