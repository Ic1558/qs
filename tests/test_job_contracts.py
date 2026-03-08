from __future__ import annotations

import unittest

from universal_qs_engine.job_contracts import (
    ALLOWED_STATES,
    UnknownJobContractError,
    get_job_contract,
    list_job_contracts,
)


class JobContractTests(unittest.TestCase):
    def test_all_four_contracts_exist(self) -> None:
        contracts = {contract.job_type: contract for contract in list_job_contracts()}
        self.assertEqual(
            set(contracts),
            {
                "qs.boq_generate",
                "qs.compliance_check",
                "qs.po_generate",
                "qs.report_export",
            },
        )

    def test_po_generate_requires_approval(self) -> None:
        contract = get_job_contract("qs.po_generate")
        self.assertTrue(contract.requires_approval)

    def test_other_jobs_default_to_non_destructive_contracts(self) -> None:
        for job_type in ("qs.boq_generate", "qs.compliance_check", "qs.report_export"):
            with self.subTest(job_type=job_type):
                contract = get_job_contract(job_type)
                self.assertFalse(contract.requires_approval)

    def test_allowed_states_are_deterministic_for_all_contracts(self) -> None:
        expected = ALLOWED_STATES
        for contract in list_job_contracts():
            with self.subTest(job_type=contract.job_type):
                self.assertEqual(contract.allowed_states, expected)

    def test_unknown_lookup_fails_closed(self) -> None:
        with self.assertRaises(UnknownJobContractError):
            get_job_contract("qs.unknown_job")


if __name__ == "__main__":
    unittest.main()
