import requests
import json

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"
ENDPOINT = "/api/v1/vlocations/"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.get(BASE_URL + ENDPOINT, headers=headers)
data = response.json()["data"]

locations = {loc["locationCode"]: loc for loc in data["locationsList"]}
machine_mapping = data["locationMachineTypeMapping"]

all_plans = []

for location_code, machines in machine_mapping.items():
    if not machines:  # اگر پلنی نداشت، رد کن
        continue
        
    loc_info = locations.get(location_code, {})
    location_name = loc_info.get("name", "Unknown")
    provider = loc_info.get("provider", "Unknown")
    
    for machine in machines:
        plan = {
            "location": location_name,
            "provider": provider,
            "plan_name": machine["name"],
            "description": machine.get("description", ""),
            "cpu": machine["cpu"],
            "ram_gb": machine["ramGb"],
            "ssd_gb": machine["ssdGb"],
            "monthly_price_usd": float(machine["monthlyPriceUsd"]),
            "hourly_price_usd": machine["hourlyPriceUsd"],
            "machine_code": machine["machineCode"],
            "location_code": location_code,
            "traffic_gb": machine.get("monthlyTrafficGb", 0),
            "extra_traffic_cost_per_tb": float(machine.get("extraTrafficCostUsdTb", "0"))
        }
        all_plans.append(plan)

# مرتب‌سازی بر اساس قیمت ساعتی (برای کاربرانی که مدل ساعتی دارن)
all_plans.sort(key=lambda x: x["hourly_price_usd"])

# ذخیره در فایل برای استفاده در سایت
with open("vps_plans.json", "w", encoding="utf-8") as f:
    json.dump(all_plans, f, indent=2, ensure_ascii=False)

print(f"✅ تعداد کل پلن‌های قابل فروش: {len(all_plans)}")
print("📁 داده‌ها در فایل vps_plans.json ذخیره شدند.")