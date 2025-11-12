import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("📦 دریافت لیست سیستم‌عامل‌ها...")

try:
    response = requests.get(f"{BASE_URL}/api/v1/os/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        os_map = data.get("os_map", {})  # یا data.get("data", {})
        
        # جمع‌آوری تمام سیستم‌عامل‌ها از همه ارائه‌دهندگان
        all_os = []
        for provider, os_list in os_map.items():
            for os in os_list:
                os["provider"] = provider  # اضافه کردن نام ارائه‌دهنده برای شفافیت
                all_os.append(os)
        
        print(f"\n✅ {len(all_os)} سیستم‌عامل یافت شد:")
        for os in all_os:
            print(f"   - {os['name']} ({os['slug']}) → {os['provider']}")
            
    else:
        print("❌ خطا در دریافت لیست سیستم‌عامل‌ها.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))