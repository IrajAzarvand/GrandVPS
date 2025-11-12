# vm_snapshots.py
import requests
from typing import List, Dict, Optional

# --- تنظیمات ---
API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def list_snapshots() -> List[str]:
    """
    لیست کدهای استپ‌شات‌های موجود را برمی‌گرداند.
    """
    try:
        response = requests.get(f"{BASE_URL}/api/v1/snapshots/", headers=headers, timeout=30)
        if response.status_code != 200:
            print("❌ خطا در دریافت لیست استپ‌شات‌ها.")
            return []

        data = response.json()
        snapshots = data.get("data", {}).get("snapshots", [])
        if isinstance(snapshots, list):
            return snapshots
        else:
            print("⚠️ هیچ استپ‌شاتی یافت نشد.")
            return []
    except Exception as e:
        print(f"❗ خطا در لیست کردن استپ‌شات‌ها: {str(e)}")
        return []

def create_snapshot(vm_code: str, description: str = "Auto snapshot") -> Optional[str]:
    """
    یک استپ‌شات جدید برای یک سرور ایجاد می‌کند.
    برمی‌گرداند: کد استپ‌شات (اگر موفق باشد) یا None (اگر خطا دهد)
    """
    payload = {
        "vm_code": vm_code,
        "description": description
    }
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/snapshots/",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code == 201:
            data = response.json()
            # فرض: پیام شامل کد استپ‌شات است
            msg_text = data.get("msg", {}).get("msg_text", "")
            print(f"✅ استپ‌شات با موفقیت ایجاد شد: {msg_text}")
            return msg_text
        else:
            print(f"❌ خطا در ایجاد استپ‌شات: {response.text}")
            return None
    except Exception as e:
        print(f"❗ خطا در ایجاد استپ‌شات: {str(e)}")
        return None

def get_snapshot_details(snapshot_code: str) -> Dict:
    """
    جزئیات یک استپ‌شات را برمی‌گرداند (فقط اگر API این endpoint را پشتیبانی کند).
    """
    # ⚠️ این endpoint در مستندات دوپرکس نیست و ممکن است کار نکند.
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/snapshots/{snapshot_code}/",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            print(f"❌ خطا در دریافت جزئیات استپ‌شات: {response.text}")
            return {}
    except Exception as e:
        print(f"❗ خطا در دریافت جزئیات استپ‌شات: {str(e)}")
        return {}

def delete_snapshot(snapshot_code: str) -> bool:
    """
    یک استپ‌شات را حذف می‌کند.
    """
    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/snapshots/{snapshot_code}/",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            print("✅ استپ‌شات با موفقیت حذف شد.")
            return True
        else:
            print(f"❌ خطا در حذف استپ‌شات: {response.text}")
            return False
    except Exception as e:
        print(f"❗ خطا در حذف استپ‌شات: {str(e)}")
        return False

# --- مثال استفاده ---
if __name__ == "__main__":
    print("1. لیست استپ‌شات‌ها:")
    snaps = list_snapshots()
    if snaps:
        for i, code in enumerate(snaps, 1):
            print(f"   {i}. {code}")
    else:
        print("   هیچ استپ‌شاتی یافت نشد.")

    # اگر بخواهیم ایجاد کنیم:
    # VM_CODE = "7b0628bf-201f-40f1-b42f-f7f1df51f30e"
    # snap_code = create_snapshot(VM_CODE, "Test snapshot from script")
    #
    # اگر بخواهیم حذف کنیم:
    # if snap_code:
    #     delete_snapshot(snap_code)