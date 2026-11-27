from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from dcim.models import Device, Interface
from ipam.models import IPAddress, VRF
from netbox.views.generic import ObjectView
from tenancy.models import Tenant
from utilities.views import ViewTab, register_model_view

from .report import build_report


def require_complete_visibility(queryset, user):
    visible = queryset.restrict(user, "view").order_by().values("pk")
    if queryset.exclude(pk__in=visible).exists():
        raise PermissionDenied(
            "The quality report requires view access to all related devices, interfaces, IP addresses, and VRFs."
        )


@register_model_view(Tenant, "data_quality", path="data-quality")
class TenantDataQualityView(ObjectView):
    queryset = Tenant.objects.all()
    template_name = "tenant_data_quality_check/report.html"
    tab = ViewTab(label="Data Quality", permission="tenancy.view_tenant")
    additional_permissions = (
        "dcim.view_device",
        "dcim.view_interface",
        "ipam.view_ipaddress",
        "ipam.view_vrf",
    )
    actions = ()

    def get_extra_context(self, request, instance):
        devices = Device.objects.filter(tenant=instance)
        vrfs = VRF.objects.filter(tenant=instance)
        interfaces = Interface.objects.filter(device__in=devices)
        interface_type = ContentType.objects.get_for_model(Interface)
        ip_addresses = IPAddress.objects.filter(
            Q(assigned_object_type=interface_type, assigned_object_id__in=interfaces.values("pk"))
            | Q(pk__in=devices.exclude(primary_ip4_id__isnull=True).values("primary_ip4_id"))
        )

        for queryset in (devices, vrfs, interfaces, ip_addresses):
            require_complete_visibility(queryset, request.user)

        devices = devices.restrict(request.user, "view")
        vrfs = vrfs.restrict(request.user, "view")
        interfaces = interfaces.restrict(request.user, "view")
        ip_addresses = ip_addresses.restrict(request.user, "view")
        interface_ip_ids = ip_addresses.filter(
            assigned_object_type=interface_type,
            assigned_object_id__in=interfaces.values("pk"),
        ).values("assigned_object_id")
        devices_with_interface_ip = set(
            interfaces.filter(pk__in=interface_ip_ids).values_list("device_id", flat=True)
        )
        devices = devices.select_related("primary_ip4").prefetch_related("tags").order_by("name", "pk")
        return {
            "report": build_report(devices, vrfs.count(), devices_with_interface_ip),
        }
