from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research import RequestSpec, SLA, pipeline, replace
from aiccc_evaluator import evaluate


class ConstantProfiles:
    def prefill_time(self, r, p, np, nd):
        return 0.1

    def decode_time_per_token(self, r, ctx, p, np, nd):
        return 0.1


class AICCCEvaluatorTests(unittest.TestCase):
    def test_accounting_only_overhead_does_not_change_progress(self):
        p = pipeline()
        w = (
            RequestSpec("a", 0.0, 20, 33),
            RequestSpec("b", 0.15, 30, 1),
        )
        a = evaluate(p, w, SLA(100, 100), ConstantProfiles(), drain=True)
        b = evaluate(
            p,
            w,
            SLA(100, 100, fixed_overhead_s=0.2),
            ConstantProfiles(),
            drain=True,
        )
        self.assertEqual(a["trajectory_hash"], b["trajectory_hash"])
        self.assertEqual(a["final_time_s"], b["final_time_s"])

    def test_sla_changes_only_ledger_under_drain(self):
        p = pipeline()
        w = (
            RequestSpec("a", 0.0, 20, 33),
            RequestSpec("b", 0.15, 30, 1),
        )
        loose = evaluate(p, w, SLA(100, 100), ConstantProfiles(), drain=True)
        strict = evaluate(p, w, SLA(0.01, 0.01), ConstantProfiles(), drain=True)
        self.assertNotEqual(loose["safe"], strict["safe"])
        self.assertEqual(loose["trajectory_hash"], strict["trajectory_hash"])

    def test_explicit_network_budget_fields_are_recorded(self):
        r = evaluate(
            pipeline(),
            (RequestSpec("a", 0.0, 100, 1),),
            SLA(100, 100),
            ConstantProfiles(),
            trace=True,
        )
        post = next(
            x
            for x in r["trace"]
            if x["side"] == "post" and x["num_prefill"] == 1
        )
        ledger = post["ledger"]["a"]
        self.assertGreater(ledger["residual_network_s"], 0)
        self.assertTrue(ledger["network"])
        allocated = sum(x["delta_s"] for x in ledger["network"].values())
        self.assertAlmostEqual(allocated, ledger["residual_network_s"])

    def test_network_relative_commitment_is_equal_on_path(self):
        p = pipeline()
        p = replace(
            p,
            links={
                k: replace(
                    v,
                    capacity_bytes_per_s=v.capacity_bytes_per_s
                    * (2 if i % 2 else 1),
                )
                for i, (k, v) in enumerate(p.links.items())
            },
        )
        r = evaluate(
            p,
            (RequestSpec("a", 0.0, 100, 1),),
            SLA(100, 100),
            ConstantProfiles(),
            trace=True,
        )
        post = next(
            x
            for x in r["trace"]
            if x["side"] == "post" and x["num_prefill"] == 1
        )
        ratios = [
            item["relative_capacity"]
            for item in post["ledger"]["a"]["network"].values()
        ]
        self.assertLess(max(ratios) - min(ratios), 1e-12)

    def test_any_first_violation_is_unsafe_no_attainment_threshold(self):
        r = evaluate(
            pipeline(),
            (RequestSpec("a", 0.0, 20, 1),),
            SLA(0.01, 100),
            ConstantProfiles(),
        )
        self.assertFalse(r["safe"])
        self.assertTrue(r["strict_all_request_safety"])
        self.assertEqual(r["first_violation"]["kind"], "sla_time")

    def test_intrinsic_accounting_preserves_trajectory(self):
        w = (RequestSpec("r", 0.0, 2051, 143),)
        p = pipeline()
        sla = SLA(2.0, 0.15, fixed_overhead_s=0.005)
        baseline = evaluate(p, w, sla, intrinsic=False, drain=True)
        corrected = evaluate(p, w, sla, intrinsic=True, drain=True)
        self.assertEqual(baseline["trajectory_hash"], corrected["trajectory_hash"])
        self.assertTrue(baseline["safe"])
        self.assertFalse(corrected["safe"])
        self.assertAlmostEqual(baseline["max_accounted_ttft_s"], 1.8940402816)
        self.assertAlmostEqual(
            corrected["max_accounted_ttft_s"],
            2.0158229367353977,
        )


if __name__ == "__main__":
    unittest.main()
