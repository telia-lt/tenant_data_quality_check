import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace


spec = importlib.util.spec_from_file_location(
    "quality_report", Path(__file__).parents[1] / "tenant_data_quality_check" / "report.py"
)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def device(pk, ip="192.0.2.1/24", fields=None, tags=("tag",), status="active"):
    primary = SimpleNamespace(address=SimpleNamespace(ip=ip.split("/")[0])) if ip else None
    return SimpleNamespace(
        pk=pk,
        primary_ip4_id=pk if primary else None,
        primary_ip4=primary,
        custom_field_data=fields if fields is not None else {
            "PID": "123", "solarwinds_id": "456", "speed_mbps": 100
        },
        tags=SimpleNamespace(all=lambda: tags),
        status=status,
    )


class ReportTests(unittest.TestCase):
    def test_compliant_device(self):
        result = report.build_report([device(1)], 1, {1})
        self.assertEqual((result["passed_checks"], result["total_checks"]), (9, 9))
        self.assertEqual(result["compliance_score"], 100)
        self.assertEqual(result["issues"], [])

    def test_empty_tenant_and_missing_vrf(self):
        result = report.build_report([], 0, set())
        self.assertEqual((result["total_devices"], result["total_issues"]), (0, 1))
        self.assertEqual(result["compliance_score"], 0)
        self.assertEqual(report.build_report([], 1, set())["compliance_score"], 100)
        self.assertEqual(report.build_report([], 2, set())["total_issues"], 1)

    def test_duplicate_hosts_ignore_mask_and_each_device_fails(self):
        result = report.build_report(
            [device(1, "192.0.2.1/24"), device(2, "192.0.2.1/32")], 1, {1, 2}
        )
        self.assertEqual(result["total_issues"], 2)
        self.assertTrue(all(i["check"] == report.DEVICE_CHECKS[3] for i in result["issues"]))
        self.assertEqual(result["passed_checks"], 15)
        self.assertAlmostEqual(result["compliance_score"], 15 / 17 * 100)

    def test_missing_values_and_inactive_status(self):
        result = report.build_report(
            [device(1, None, {"PID": " ", "LAN_PID": "", "solarwinds_id": None}, (), "offline")],
            1,
            set(),
        )
        self.assertEqual(result["total_issues"], 7)
        self.assertEqual(result["passed_checks"], 2)
        self.assertNotIn(report.DEVICE_CHECKS[3], [i["check"] for i in result["issues"]])

    def test_lan_pid_and_numeric_zero_are_values(self):
        fields = {"PID": "", "LAN_PID": "abc", "solarwinds_id": 0, "speed_mbps": 0}
        result = report.build_report([device(1, fields=fields)], 1, {1})
        self.assertEqual(result["total_issues"], 0)


if __name__ == "__main__":
    unittest.main()
