# vm_info_and_network.py
import requests

API_KEY = "d13aea94.Vmzuzv7EiXSI16fzm5HSISOdhiM8hb9DYyO-sYPkjnE"
BASE_URL = "https://www.doprax.com"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def list_vms():
    """دریافت لیست تمام سرورهای کاربر."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/", headers=headers)
    if response.status_code != 200:
        return []
    data = response.json().get("data", [])
    return [
        {
            "name": vm["name"],
            "vm_code": vm["vmCode"],
            "provider": vm["provider"],
            "location": f"{vm['locationName']} ({vm['country']})",
            "status": vm["status"],
            "ipv4": vm.get("ipv4", "N/A"),
            "created": vm.get("created", "N/A")
        }
        for vm in data
    ]

def get_vm_details(vm_code):
    """دریافت جزئیات یک سرور خاص."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/{vm_code}/", headers=headers)
    if response.status_code != 200:
        return {}
    data = response.json().get("data", {})
    return {
        "name": data.get("name"),
        "vm_code": data.get("vmCode"),
        "provider": data.get("provider"),
        "location": f"{data['locationName']} ({data['country']})",
        "os": data.get("os"),
        "cpu": data.get("cpu"),
        "ram_gb": data.get("ramGb"),
        "ssd_gb": data.get("ssdGb"),
        "monthly_traffic_gb": data.get("monthlyBandwidth", 0),
        "traffic_used_gb": data.get("trafficUsed", 0),  # این مقدار ممکنه صفر باشه
        "status": data.get("status"),
        "ipv4": data.get("ipv4", "N/A"),
        "ipv4_private": data.get("ipv4Private", "N/A"),
        "created": data.get("created", "N/A")
    }

def get_vm_status(vm_code):
    """دریافت وضعیت فعلی سرور."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/{vm_code}/status/", headers=headers)
    if response.status_code != 200:
        return {}
    data = response.json().get("data", {})
    return {
        "status": data.get("status"),
        "is_active": data.get("isActive", False)
    }

def get_vm_domains(vm_code):
    """دریافت لیست دامنه‌های سرور."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/{vm_code}/domains/", headers=headers)
    if response.status_code != 200:
        return []
    data = response.json().get("data", [])
    return [
        {
            "name": domain.get("name"),
            "id": domain.get("id"),
            "active": domain.get("active", False),
            "created": domain.get("created", "N/A")
        }
        for domain in data
    ]

def verify_domain(vm_code, domain_code):
    """تأیید یک دامنه."""
    payload = {"operation": "verify"}
    response = requests.post(
        f"{BASE_URL}/api/v1/vms/{vm_code}/domains/{domain_code}/",
        headers=headers,
        json=payload
    )
    if response.status_code != 200:
        return False
    return True

def delete_domain(vm_code, domain_code):
    """حذف یک دامنه."""
    response = requests.delete(
        f"{BASE_URL}/api/v1/vms/{vm_code}/domains/{domain_code}/",
        headers=headers
    )
    if response.status_code != 200:
        return False
    return True

def get_vm_traffic(vm_code):
    """دریافت اطلاعات ترافیک سرور (فقط محدودیت ماهانه)."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/{vm_code}/", headers=headers)
    if response.status_code != 200:
        return {}
    data = response.json().get("data", {})
    monthly_bandwidth_gb = data.get("monthlyBandwidth", 0) / 1024  # از مگابایت به گیگابایت
    traffic_used_gb = data.get("trafficUsed", 0) / 1024  # از مگابایت به گیگابایت
    usage_percentage = (traffic_used_gb / monthly_bandwidth_gb * 100) if monthly_bandwidth_gb > 0 else 0
    
    return {
        "monthly_bandwidth_gb": monthly_bandwidth_gb,
        "traffic_used_gb": traffic_used_gb,
        "usage_percentage": usage_percentage
    }

def get_vm_ips(vm_code):
    """دریافت لیست IPهای سرور."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/{vm_code}/ips/", headers=headers)
    if response.status_code != 200:
        return []
    data = response.json().get("data", [])
    return [
        {
            "address": ip_info.get("address"),
            "version": ip_info.get("version"),
            "status": ip_info.get("status"),
            "assigned_at": ip_info.get("assignedAt", "N/A")
        }
        for ip_info in data
    ]

def change_vm_ip(vm_code, ip_code):
    """تغییر IP سرور (فقط برای Hetzner)."""
    payload = {"operation": "change_ip"}
    response = requests.post(
        f"{BASE_URL}/api/v1/vms/{vm_code}/ips/{ip_code}/",
        headers=headers,
        json=payload
    )
    if response.status_code != 200:
        return False
    return True

def get_vm_password(vm_code):
    """دریافت رمز عبور سرور."""
    response = requests.get(f"{BASE_URL}/api/v1/vms/{vm_code}/password/", headers=headers)
    if response.status_code != 200:
        return {}
    data = response.json().get("data", {})
    return {
        "username": data.get("username", "N/A"),
        "password": data.get("password", "N/A"),
        "os": data.get("os", "N/A")
    }

# --- مثال استفاده ---
if __name__ == "__main__":
    print("✅ لیست سرورها:")
    vms = list_vms()
    for vm in vms[:2]:  # فقط ۲ تا نمونه
        print(f"   - {vm['name']} ({vm['provider']}) | {vm['status']}")

    print("\n✅ جزئیات سرور نمونه:")
    sample_vm = vms[0] if vms else None
    if sample_vm:
        details = get_vm_details(sample_vm["vm_code"])
        for key, value in details.items():
            print(f"   {key}: {value}")

    print("\n✅ وضعیت سرور:")
    if sample_vm:
        status = get_vm_status(sample_vm["vm_code"])
        print(f"   وضعیت: {status['status']} | فعال؟ {'✅ بله' if status['is_active'] else '❌ خیر'}")

    print("\n✅ دامنه‌های سرور:")
    if sample_vm:
        domains = get_vm_domains(sample_vm["vm_code"])
        for domain in domains[:1]:
            print(f"   - {domain['name']} | {'فعال' if domain['active'] else 'غیرفعال'}")

    print("\n✅ ترافیک سرور:")
    if sample_vm:
        traffic = get_vm_traffic(sample_vm["vm_code"])
        print(f"   محدودیت ماهانه: {traffic['monthly_bandwidth_gb']:.2f} GB")
        print(f"   مصرفی: {traffic['traffic_used_gb']:.2f} GB")
        print(f"   درصد استفاده: {traffic['usage_percentage']:.1f}%")

    print("\n✅ IPهای سرور:")
    if sample_vm:
        ips = get_vm_ips(sample_vm["vm_code"])
        for ip in ips:
            print(f"   - {ip['address']} ({ip['version']}) | {ip['status']}")

    print("\n✅ رمز عبور سرور:")
    if sample_vm:
        password = get_vm_password(sample_vm["vm_code"])
        print(f"   نام کاربری: {password['username']}")
        print(f"   رمز عبور: {password['password']}")
        print(f"   سیستم‌عامل: {password['os']}")