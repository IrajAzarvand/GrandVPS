# vm_lifecycle.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# --- تابع: ساخت سرور ---
def create_vm(location_code, machine_type_code, os_slug, provider_name, vm_name):
    payload = {
        "location_code": location_code,
        "machine_type_code": machine_type_code,
        "name": vm_name,
        "os_slug": os_slug,
        "provider_name": provider_name
    }

    print(f"🚀 در حال ایجاد سرور با نام: {vm_name} ...")
    print(f"   ارائه‌دهنده: {provider_name}")
    print(f"   لوکیشن: {location_code}")
    print(f"   پلن: {machine_type_code}")
    print(f"   سیستم‌عامل: {os_slug}")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/vms/",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print("\n--- پاسخ سرور ---")
        print("وضعیت:", response.status_code)
        
        if response.status_code == 201:
            data = response.json()
            vm_info = data.get("data", {})
            print("✅ سرور با موفقیت ساخته شد!")
            print(f"   نام سرور: {vm_info.get('name')}")
            print(f"   کد سرور: {vm_info.get('vmCode')}")
            print(f"   وضعیت: {vm_info.get('status')}")
            print(f"   IP: {vm_info.get('ipv4')}")
            print(f"   هزینه ساعتی: {vm_info.get('hourlyPriceUsd', 'N/A')} دلار")
            return vm_info.get('vmCode')
        else:
            print("❌ خطا در ساخت سرور.")
            print("متن خطا:", response.text)
            return None

    except Exception as e:
        print("❗ خطای اجرایی:", str(e))
        return None

# --- تابع: حذف سرور ---
def delete_vm(vm_code):
    print(f"🗑️ در حال حذف سرور با کد: {vm_code} ...")

    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/vms/{vm_code}/",
            headers=headers,
            timeout=30
        )
        
        print("\n--- پاسخ سرور ---")
        print("وضعیت:", response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ سرور با موفقیت حذف شد!")
            print("پیام:", data.get("msg", {}).get("msg_text"))
        else:
            print("❌ خطایی در حذف سرور رخ داده.")
            print("متن خطا:", response.text)

    except Exception as e:
        print("❗ خطای اجرایی:", str(e))

# --- تابع: ریبیلد سرور ---
def rebuild_vm(vm_code, os_slug):
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
            print("پیام:", data.get("msg", {}).get("msg_text"))
        else:
            print("❌ خطایی در ریبیلد رخ داده.")
            print("متن خطا:", response.text)

    except Exception as e:
        print("❗ خطای اجرایی:", str(e))

# --- تابع: اجرای دستورات (turnon, shutdown, reboot) ---
def execute_command(vm_code, command):
    # command: "turnon", "shutdown", "reboot"
    payload = {
        "command": command
    }
    print(f"🛑 در حال اجرای دستور '{command}' روی سرور با کد: {vm_code} ...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/vms/{vm_code}/commands/",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print("\n--- پاسخ سرور ---")
        print("وضعیت:", response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ دستور با موفقیت اجرا شد!")
            print("پیام:", data.get("msg", {}).get("msg_text"))
        else:
            print("❌ خطایی در اجرای دستور رخ داده.")
            print("متن خطا:", response.text)

    except Exception as e:
        print("❗ خطای اجرایی:", str(e))

# --- مثال استفاده ---
if __name__ == "__main__":
    # ۱. ساخت سرور
    vm_code = create_vm(
        location_code="f7345771-cda3-4843-9c80-cd07a0f31d4f",  # Germany, Falkenstein
        machine_type_code="e95e1de4-5798-458b-a518-7ca7a4ab8763",  # H1
        os_slug="ubuntu_24_04",
        provider_name="Hetzner",
        vm_name="test-vm-lifecycle"
    )

    if vm_code:
        # ۲. ریبیلد سرور با Fedora
        rebuild_vm(vm_code, "fedora_42")

        # ۳. خاموش کردن سرور
        execute_command(vm_code, "shutdown")

        # ۴. حذف سرور
        delete_vm(vm_code)