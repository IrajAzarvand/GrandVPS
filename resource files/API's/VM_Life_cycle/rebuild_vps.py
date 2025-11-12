import requests

# ==============================
# تنظیمات
# ==============================
API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

# --- اطلاعات سرور ---
vm_code = "72a0ad10-80c8-4f96-b753-7f082eb29a98"  # 👈 کد سرور خودت رو اینجا جایگزین کن
os_slug = "fedora_42"  # 👈 سیستم‌عامل جدید (مثلاً fedora_42, ubuntu_22_04, centos_stream_9 و ...)

# ==============================
# اجرای ریبیلد
# ==============================
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "os_slug": os_slug
}

print(f"🔄 در حال ریبیلد سرور با کد: {vm_code}")
print(f"   سیستم‌عامل جدید: {os_slug}")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/vms/{vm_code}/rebuild/",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ ریبیلد با موفقیت آغاز شد!")
        print("پیام:", data.get("msg", {}).get("msg_text", "بدون پیام"))
        print("\n💡 نکته: ریبیلد چند دقیقه طول می‌کشد. وضعیت سرور بعداً به 'running' تغییر می‌کند.")
    else:
        print("❌ خطایی در ریبیلد رخ داده.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))