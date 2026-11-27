from collections import Counter


DEVICE_CHECKS = (
    "PID or LAN_PID is set",
    "SolarWinds ID is set",
    "Primary IPv4 is set",
    "Primary IPv4 is unique within tenant",
    "At least one interface has an IP address",
    "At least one tag is set",
    "Speed Mbps is set",
    "Status is active",
)

REQUIREMENT_LABELS = (
    "PID / LAN_PID present",
    "SolarWinds ID present",
    "Primary IPv4 present",
    "Primary IPv4 unique",
    "At least one IP address on one of interfaces",
    "At least one TAG per device",
    "Speed Mbps present",
    "Device status is Active",
)


def has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return value != [] and value != {}


def build_report(devices, vrf_count, devices_with_interface_ip):
    devices = list(devices)
    addresses = Counter(
        str(device.primary_ip4.address.ip)
        for device in devices
        if device.primary_ip4_id
    )
    issues = []
    vrf_passed = vrf_count == 1
    vrf_failures = []
    if not vrf_passed:
        detail = f"Found {vrf_count} VRFs."
        issues.append({
            "device": None,
            "check": "Tenant has exactly one VRF",
            "detail": detail,
        })
        vrf_failures.append({"device": None, "detail": detail})

    failures_by_check = [[] for _ in DEVICE_CHECKS]

    for device in devices:
        fields = device.custom_field_data or {}
        primary_ip = str(device.primary_ip4.address.ip) if device.primary_ip4_id else None
        checks = (
            has_value(fields.get("PID")) or has_value(fields.get("LAN_PID")),
            has_value(fields.get("solarwinds_id")),
            primary_ip is not None,
            primary_ip is None or addresses[primary_ip] == 1,
            device.pk in devices_with_interface_ip,
            bool(device.tags.all()),
            has_value(fields.get("speed_mbps")),
            device.status == "active",
        )
        for idx, (label, passed) in enumerate(zip(DEVICE_CHECKS, checks)):
            if not passed:
                detail = f"Duplicate IP: {primary_ip}" if label == DEVICE_CHECKS[3] else ""
                issues.append({
                    "device": device,
                    "check": label,
                    "detail": detail,
                })
                failures_by_check[idx].append({
                    "device": device,
                    "detail": detail,
                })

    total_devices = len(devices)
    requirements = [
        {
            "name": "Single VRF",
            "passed": vrf_passed,
            "passed_count": 1 if vrf_passed else 0,
            "total_count": 1,
            "result": f"{1 if vrf_passed else 0}/1",
            "failures": vrf_failures,
            "is_tenant_check": True,
        }
    ]
    for req_name, failures in zip(REQUIREMENT_LABELS, failures_by_check):
        passed_count = total_devices - len(failures)
        requirements.append({
            "name": req_name,
            "passed": len(failures) == 0,
            "passed_count": passed_count,
            "total_count": total_devices,
            "result": f"{passed_count}/{total_devices}",
            "failures": failures,
            "is_tenant_check": False,
        })

    total_checks = 1 + total_devices * len(DEVICE_CHECKS)
    passed_checks = total_checks - len(issues)
    return {
        "total_devices": total_devices,
        "total_issues": len(issues),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "compliance_score": passed_checks * 100 / total_checks,
        "issues": issues,
        "requirements": requirements,
        "vrf_count": vrf_count,
    }
