import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from audit_report_test_support import (
    clear_current_audit_report,
    current_audit_report,
)


class AuditReportTestSupportTests(unittest.TestCase):
    def tearDown(self):
        clear_current_audit_report()

    def test_report_is_reused_until_explicitly_cleared(self):
        first = {"snapshot": "first"}
        second = {"snapshot": "second"}
        clear_current_audit_report()

        with patch.object(audit, "audit", side_effect=(first, second)) as run_audit:
            self.assertIs(current_audit_report(), first)
            self.assertIs(current_audit_report(), first)
            self.assertEqual(run_audit.call_count, 1)

            clear_current_audit_report()
            self.assertIs(current_audit_report(), second)
            self.assertEqual(run_audit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
