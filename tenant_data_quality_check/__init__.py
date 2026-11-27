from netbox.plugins import PluginConfig


class TenantDataQualityConfig(PluginConfig):
    name = "tenant_data_quality_check"
    verbose_name = "Tenant Data Quality"
    description = "Data quality checks for tenant devices"
    version = "0.1.0"
    min_version = "4.4.6"
    max_version = "4.4.6"

    def ready(self):
        super().ready()
        from . import views  # noqa: F401


config = TenantDataQualityConfig
