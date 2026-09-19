from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research import RequestSpec, SLA, pipeline, replace
from aiccc_evaluator import evaluate as evaluate_core
from aiccc_j1_evaluator import evaluate


class ConstantProfiles:
    def prefill_time(self, r, p, np, nd):
        return 0.1

    def decode_time_per_token(self, r, ctx, p, np, nd):
        return 0.1


class ContextProfiles:
    def prefill_time(self, r, p, np, nd):
        return 0.1

    def decode_time_per_token(self, r, ctx, p, np, nd):
        return 0.2 if ctx <= r.input_tokens + 2 else 0.05


class OverlapProfiles:
    def prefill_time(self, r, p, np, nd):
        return 1.0 if r.id == "a" else 0.1

    def decode_time_per_token(self, r, ctx, p, np, nd):
        return 0.1


def huge_bandwidth(p):
    return replace(
        p,
        links={
            k: replace(v, capacity_bytes_per_s=1e18)
            for k, v in p.links.items()
        },
    )


class AICCCJ1EvaluatorTests(unittest.TestCase):
    def test_standard_ttft_reaches_first_output_and_charges_fixed_once(self):
        p = huge_bandwidth(pipeline())
        r = evaluate(
            p,
            (RequestSpec("a", 0.0, 20, 3),),
            SLA(10.0, 10.0, fixed_overhead_s=0.05),
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
            trace=True,
        )
        ledger = r["request_ledgers"]["a"]["ttft"]
        self.assertAlmostEqual(r["first_token_time_s"]["a"], 0.2)
        self.assertAlmostEqual(ledger["profile_elapsed_s"], 0.2)
        self.assertAlmostEqual(ledger["fixed_s"], 0.05)
        self.assertAlmostEqual(ledger["accounted_s"], 0.25)

    def test_average_tpot_excludes_first_output(self):
        p = huge_bandwidth(pipeline())
        r = evaluate(
            p,
            (RequestSpec("a", 0.0, 20, 3),),
            SLA(10.0, 10.0, fixed_overhead_s=0.02),
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
            trace=True,
        )
        ledger = r["request_ledgers"]["a"]["tpot"]
        self.assertEqual(ledger["units"], 2)
        self.assertAlmostEqual(ledger["profile_elapsed_s"], 0.2)
        self.assertAlmostEqual(ledger["fixed_s"], 0.04)
        self.assertAlmostEqual(ledger["accounted_s"] / ledger["units"], 0.12)

    def test_single_output_has_no_average_tpot_horizon(self):
        r = evaluate(
            huge_bandwidth(pipeline()),
            (RequestSpec("a", 0.0, 20, 1),),
            SLA(10.0, 0.01),
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
            trace=True,
        )
        self.assertTrue(r["safe"])
        self.assertNotIn("tpot", r["request_ledgers"]["a"])
        self.assertAlmostEqual(
            r["first_token_time_s"]["a"], r["finish_time_s"]["a"]
        )

    def test_j1_reuses_exact_j0_profile_trajectory(self):
        p = pipeline()
        w = (
            RequestSpec("a", 0.0, 20, 33),
            RequestSpec("b", 0.15, 30, 17),
        )
        sla = SLA(100.0, 100.0)
        core = evaluate_core(
            p,
            w,
            sla,
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
            drain=True,
            trace=True,
        )
        j1 = evaluate(
            p,
            w,
            sla,
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
        )
        self.assertEqual(j1["core_trajectory_hash"], core["trajectory_hash"])
        self.assertEqual(j1["final_time_s"], core["final_time_s"])

    def test_first_token_semantics_do_not_depend_on_decode_block_size(self):
        p = huge_bandwidth(pipeline())
        w = (RequestSpec("a", 0.0, 20, 17),)
        args = dict(
            pipeline=p,
            workload=w,
            sla=SLA(10.0, 10.0),
            prof=ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
            trace=True,
        )
        q1 = evaluate(**args, decode_block_size=1)
        q7 = evaluate(**args, decode_block_size=7)
        q16 = evaluate(**args, decode_block_size=16)
        self.assertAlmostEqual(q1["first_token_time_s"]["a"], 0.2)
        self.assertAlmostEqual(q7["first_token_time_s"]["a"], 0.2)
        self.assertAlmostEqual(q16["first_token_time_s"]["a"], 0.2)
        self.assertAlmostEqual(q1["finish_time_s"]["a"], q7["finish_time_s"]["a"])
        self.assertAlmostEqual(q7["finish_time_s"]["a"], q16["finish_time_s"]["a"])

    def test_request_average_can_pass_when_phase_local_per_token_rejects(self):
        p = huge_bandwidth(pipeline())
        w = (RequestSpec("a", 0.0, 20, 3),)
        sla = SLA(10.0, 0.15)
        core = evaluate_core(
            p,
            w,
            sla,
            ContextProfiles(),
            intrinsic=False,
            blocking_policy="none",
            decode_block_size=1,
        )
        j1 = evaluate(
            p,
            w,
            sla,
            ContextProfiles(),
            intrinsic=False,
            blocking_policy="none",
            decode_block_size=1,
            trace=True,
        )
        self.assertFalse(core["safe"])
        self.assertTrue(j1["safe"])
        self.assertAlmostEqual(
            j1["request_ledgers"]["a"]["tpot"]["predicted_metric_s"],
            0.125,
            places=9,
        )

    def test_recovered_blocking_debt_is_integrated_over_first_token_progress(self):
        p = huge_bandwidth(pipeline())
        w = (
            RequestSpec("a", 0.0, 20, 1),
            RequestSpec("b", 0.0, 20, 1),
        )
        r = evaluate(
            p,
            w,
            SLA(10.0, 10.0),
            OverlapProfiles(),
            intrinsic=False,
            trace=True,
        )
        self.assertAlmostEqual(
            r["request_ledgers"]["b"]["ttft"]["blocking_s"],
            1.0,
        )

    def test_shared_link_standard_horizon_commitments_aggregate(self):
        base = pipeline()
        input_tokens = 20
        sla = SLA(1.0, 100.0)
        residual = 0.8
        horizon_tokens = input_tokens + 1
        path_bytes = (
            sum(len(boundary.route_link_ids) for boundary in base.boundaries)
            * base.model.activation_bytes_per_token
            * horizon_tokens
        )
        one_request_commitment = path_bytes / residual
        capacity = 1.5 * one_request_commitment
        p = replace(
            base,
            links={
                link_id: replace(link, capacity_bytes_per_s=capacity)
                for link_id, link in base.links.items()
            },
        )
        single = evaluate(
            p,
            (RequestSpec("a", 0.0, input_tokens, 1),),
            sla,
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
        )
        pair = evaluate(
            p,
            (
                RequestSpec("a", 0.0, input_tokens, 1),
                RequestSpec("b", 0.0, input_tokens, 1),
            ),
            sla,
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
        )
        self.assertTrue(single["safe"])
        self.assertFalse(pair["safe"])
        self.assertEqual(pair["first_violation"]["kind"], "network")

    def test_one_request_sla_failure_is_workload_unsafe(self):
        r = evaluate(
            huge_bandwidth(pipeline()),
            (RequestSpec("a", 0.0, 20, 2),),
            SLA(0.15, 100.0),
            ConstantProfiles(),
            intrinsic=False,
            blocking_policy="none",
        )
        self.assertFalse(r["safe"])
        self.assertTrue(r["strict_all_request_safety"])
        self.assertEqual(r["first_violation"]["object"], "standard_ttft")



    def test_blocking_scale_is_accounting_only_sensitivity(self):
        p = huge_bandwidth(pipeline())
        w = (
            RequestSpec("a", 0.0, 20, 1),
            RequestSpec("b", 0.0, 20, 1),
        )
        args = dict(
            pipeline=p,
            workload=w,
            sla=SLA(10.0, 10.0),
            prof=OverlapProfiles(),
            intrinsic=False,
            trace=True,
        )
        full = evaluate(**args, blocking_scale=1.0)
        none = evaluate(**args, blocking_scale=0.0)
        self.assertEqual(full["core_trajectory_hash"], none["core_trajectory_hash"])
        self.assertEqual(full["final_time_s"], none["final_time_s"])
        self.assertGreater(full["request_ledgers"]["b"]["ttft"]["blocking_s"], 0.0)
        self.assertEqual(none["request_ledgers"]["b"]["ttft"]["blocking_s"], 0.0)
        self.assertEqual(full["blocking_scale"], 1.0)
        self.assertEqual(none["blocking_scale"], 0.0)

    def test_blocking_scale_rejects_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "blocking_scale"):
            evaluate(
                huge_bandwidth(pipeline()),
                (RequestSpec("a", 0.0, 20, 1),),
                SLA(10.0, 10.0),
                ConstantProfiles(),
                blocking_scale=-0.1,
            )

if __name__ == "__main__":
    unittest.main()
