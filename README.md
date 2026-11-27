# Tenant Data Quality for NetBox 4.4.6

Adds a **Data Quality** tab to each tenant. This plugin does not change data.

## Installation

On the NetBox server, copy this directory to an accessible location, then install
it in NetBox's virtual environment:

```shell
/opt/netbox/venv/bin/pip install /path/to/tenant_data_quality_check
```

Add `"tenant_data_quality_check"` to `PLUGINS` in NetBox's `configuration.py` and
restart the NetBox web and worker services. Make the package installation
persistent across upgrades or container rebuilds according to your deployment.
No migrations or plugin-specific configuration are required.

## Checks and score

The report includes only devices directly assigned to the tenant, regardless of
device status. It checks that the tenant has exactly one directly assigned VRF,
then checks each device for:

1. A value in the device custom field `PID` or `LAN_PID`.
2. A value in `solarwinds_id`.
3. A primary IPv4.
4. A primary IPv4 that is not used by another device in this tenant.
5. At least one IPv4 or IPv6 address assigned to a device interface.
6. At least one tag.
7. A value in the device custom field `speed_mbps`.
8. The `active` status.

Create these custom fields for the Device object type using exactly these
**Name** values; labels can differ. Null, empty strings, whitespace-only
strings, and empty lists or objects count as missing; numeric zero is a value.
Duplicate IPs are compared by host address, ignoring prefix length and VRF.
A device without a primary IPv4 fails check 3, but does not fail check 4 solely
because it is missing. Both devices in a duplicate pair fail check 4.

Every failed tenant or device check is one issue. The score is
`(1 + 8 * devices - issues) / (1 + 8 * devices) * 100`. Thus a tenant with
no devices has one check, the VRF check. The report lists each issue and links
to affected devices.

The viewer needs `view` permissions for tenants, devices, interfaces, IP
addresses and VRFs. Object-level constraints are respected: if any relevant
device, interface, assigned or primary IP address, or tenant VRF is hidden,
the report returns HTTP 403 rather than displaying incomplete or misleading
results. Tenant access is also checked by NetBox.

## Tests

Pure report logic can be tested without NetBox:

```shell
python -m unittest discover -s tests -v
```

Integration, permissions, and rendering should additionally be tested on a
NetBox 4.4.6 instance with PostgreSQL and the plugin enabled.
