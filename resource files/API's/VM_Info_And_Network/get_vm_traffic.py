# get_vm_traffic.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "7b0628bf-201f-40f1-b42f-f7f1df51f30e"  # ← کد سرور خودت

print(f"📊 دریافت اطلاعات ترافیک سرور با کد: {VM_CODE} ...")

try:
    # دریافت جزئیات سرور — نه از endpoint /traffics/
    response = requests.get(f"{BASE_URL}/api/v1/vms/{VM_CODE}/", headers=headers, timeout=30)
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json().get("data", {})
        
        # استخراج اطلاعات ترافیک
        monthly_bandwidth_mb = data.get("monthlyBandwidth", 0)  # مگابایت
        traffic_used_mb = data.get("trafficUsed", 0)           # مگابایت
        
        if monthly_bandwidth_mb == 0:
            print("⚠️ سرور فاقد سقف ترافیک (ممکنه ترافیک نامحدود باشه).")
            print(f"   ترافیک مصرفی: {traffic_used_mb:.2f} MB")
        else:
            monthly_bandwidth_gb = monthly_bandwidth_mb / 1024
            traffic_used_gb = traffic_used_mb / 1024
            usage_percentage = (traffic_used_gb / monthly_bandwidth_gb * 100) if monthly_bandwidth_gb > 0 else 0
            
            print("✅ اطلاعات ترافیک:")
            print(f"   ترافیک ماهانه: {monthly_bandwidth_gb:.2f} GB")
            print(f"   ترافیک مصرفی: {traffic_used_gb:.2f} GB")
            print(f"   درصد استفاده: {usage_percentage:.1f}%")
            
            if usage_percentage > 90:
                print("❗ توجه: بیش از ۹۰٪ ترافیک مصرف شده است!")
                
    else:
        print("❌ خطا در دریافت جزئیات سرور.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))