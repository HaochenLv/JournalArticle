from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aiccc_math import (
    ResidualBudgetExhausted,
    aggregate_link_commitments,
    path_commitments,
    residual_network_budget,
)


class AICCCMathTests(unittest.TestCase):
    def test_residual_budget_is_sla_minus_accounting_only_terms(self):
        b = residual_network_budget(
            2.0,
            1.1,
            intrinsic_s=0.12,
            blocking_s=0.03,
            fixed_s=0.005,
            queue_s=0.0,
        )
        self.assertAlmostEqual(b.accounted_s, 1.255)
        self.assertAlmostEqual(b.network_s, 0.745)

    def test_path_budget_sums_to_residual_and_equalizes_relative_capacity(self):
        c = path_commitments(
            {"a": 50.0, "b": 100.0},
            {"a": 100.0, "b": 200.0},
            2.0,
        )
        self.assertAlmostEqual(sum(x.allocated_time_s for x in c.values()), 2.0)
        self.assertAlmostEqual(c["a"].weight, 0.5)
        self.assertAlmostEqual(c["b"].weight, 0.5)
        self.assertAlmostEqual(c["a"].required_bandwidth_bytes_per_s, 50.0)
        self.assertAlmostEqual(c["b"].required_bandwidth_bytes_per_s, 100.0)
        self.assertAlmostEqual(c["a"].relative_capacity, c["b"].relative_capacity)

    def test_commitment_matches_aiccc_algebraic_form(self):
        demand = {"a": 30.0, "b": 80.0}
        caps = {"a": 60.0, "b": 160.0}
        residual = 0.8
        c = path_commitments(demand, caps, residual)
        serial = sum(demand[k] / caps[k] for k in demand)
        for k in demand:
            expected = caps[k] * serial / residual
            self.assertAlmostEqual(c[k].required_bandwidth_bytes_per_s, expected)

    def test_shared_link_commitments_add(self):
        a = path_commitments({"e": 20.0}, {"e": 100.0}, 1.0)
        b = path_commitments({"e": 30.0}, {"e": 100.0}, 1.0)
        total = aggregate_link_commitments({"r1": a, "r2": b})
        self.assertAlmostEqual(total["e"], 50.0)

    def test_nonpositive_residual_is_not_a_network_allocation(self):
        with self.assertRaises(ResidualBudgetExhausted):
            path_commitments({"e": 1.0}, {"e": 10.0}, 0.0)


if __name__ == "__main__":
    unittest.main()
