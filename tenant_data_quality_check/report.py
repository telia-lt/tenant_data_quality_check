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
    if vrf_count != 1:
        issues.append({
            "device": None,
            "check": "Tenant has exactly one VRF",
            "detail": f"Found {vrf_count} VRFs.",
        })

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
        for label, passed in zip(DEVICE_CHECKS, checks):
            if not passed:
                issues.append({
                    "device": device,
                    "check": label,
                    "detail": f"Duplicate IP: {primary_ip}" if label == DEVICE_CHECKS[3] else "",
                })

    total_checks = 1 + len(devices) * len(DEVICE_CHECKS)
    passed_checks = total_checks - len(issues)
    return {
        "total_devices": len(devices),
        "total_issues": len(issues),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "compliance_score": passed_checks * 100 / total_checks,
        "issues": issues,
        "vrf_count": vrf_count,
    }
