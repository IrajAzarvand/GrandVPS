# delete_domain.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

VM_CODE = "abc123-def456-ghi789"      # ← اینو با کد واقعی سرورت عوض کن
DOMAIN_CODE = "dom-123456789"         # ← اینو با کد واقعی دامنه‌ات عوض کن

print(f"🗑️ در حال حذف دامنه با کد: {DOMAIN_CODE} از سرور: {VM_CODE} ...")

try:
    response = requests.delete(
        f"{BASE_URL}/api/v1/vms/{VM_CODE}/domains/{DOMAIN_CODE}/",
        headers=headers,
        timeout=30
    )
    
    print("\n--- پاسخ سرور ---")
    print("وضعیت:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        msg = data.get("msg", {})
        print("✅ دامنه با موفقیت حذف شد!")
        print(f"   پیام: {msg.get('msg_text', 'N/A')}")
    else:
        print("❌ خطا در حذف دامنه.")
        print("متن خطا:", response.text)

except Exception as e:
    print("❗ خطای اجرایی:", str(e))