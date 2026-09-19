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


    def test_tied_arrivals_commute(self):
        w = (
            RequestSpec("a", 0.0, 20, 33),
            RequestSpec("b", 0.0, 30, 17),
        )
        p = pipeline()
        sla = SLA(100, 100)
        a = evaluate(p, w, sla, ConstantProfiles(), trace=True, drain=True)
        b = evaluate(p, w[::-1], sla, ConstantProfiles(), trace=True, drain=True)
        self.assertEqual(a["trajectory_hash"], b["trajectory_hash"])
        arrival_post = next(
            x
            for x in a["trace"]
            if x["side"] == "post"
            and {("Arrival", "a"), ("Arrival", "b")} <= set(x["events"])
        )
        self.assertEqual(arrival_post["num_prefill"], 2)

    def test_fractional_decode_progress_survives_unrelated_arrival(self):
        block_size = 7
        w = (
            RequestSpec("a", 0.0, 20, 33),
            RequestSpec("b", 0.15, 20, 1),
        )
        r = evaluate(
            pipeline(),
            w,
            SLA(100, 100),
            ConstantProfiles(),
            trace=True,
            drain=True,
            decode_block_size=block_size,
        )
        pre = next(
            x
            for x in r["trace"]
            if x["side"] == "pre" and abs(x["time_s"] - 0.15) < 1e-9
        )
        self.assertAlmostEqual(pre["ledger"]["a"]["progress"], 0.5)
        self.assertEqual(r["decode_block_size"], block_size)

    def test_configurable_block_boundary_context_and_kv_are_consistent(self):
        block_size = 7
        input_tokens = 20
        p = pipeline()
        r = evaluate(
            p,
            (RequestSpec("a", 0.0, input_tokens, 20),),
            SLA(100, 100),
            ConstantProfiles(),
            trace=True,
            drain=True,
            decode_block_size=block_size,
        )
        post = next(
            x
            for x in r["trace"]
            if x["side"] == "post"
            and ("DecodeBlockUpdate", "a") in x["events"]
        )
        pre = next(
            x
            for x in r["trace"]
            if x["side"] == "pre" and abs(x["time_s"] - post["time_s"]) < 1e-9
        )
        self.assertEqual(pre["ledger"]["a"]["context"], input_tokens + block_size)
        self.assertEqual(
            post["ledger"]["a"]["context"],
            input_tokens + 2 * block_size,
        )
        layers = p.layers_by_node()
        node_id = next(iter(p.nodes))
        expected_kv_delta = (
            block_size
            * p.model.kv_bytes_per_token_per_layer
            * layers[node_id]
        )
        self.assertAlmostEqual(
            post["memory"][node_id] - pre["memory"][node_id],
            expected_kv_delta,
        )
        self.assertEqual(r["decode_block_size"], block_size)

    def test_simultaneous_constraint_violations_are_all_retained(self):
        p = pipeline()
        layers = p.layers_by_node()
        p = replace(
            p,
            nodes={
                node_id: replace(
                    node,
                    memory_capacity_bytes=int(
                        p.model.weight_bytes
                        * layers[node_id]
                        / p.model.num_layers
                        + node.workspace_bytes
                        + node.memory_margin_bytes
                        + 1
                    ),
                )
                for node_id, node in p.nodes.items()
            },
        )
        r = evaluate(
            p,
            (RequestSpec("a", 0.0, 20, 33),),
            SLA(0.01, 0.01),
            ConstantProfiles(),
        )
        self.assertEqual(
            {x["kind"] for x in r["first_violations"]},
            {"sla_time", "memory"},
        )

    def test_prompt_kv_and_activation_memory_are_reserved_at_arrival(self):
        p = pipeline()
        input_tokens = 200
        r = evaluate(
            p,
            (RequestSpec("a", 0.0, input_tokens, 1),),
            SLA(100, 100),
            ConstantProfiles(),
            trace=True,
            drain=True,
        )
        arrival = next(
            x
            for x in r["trace"]
            if x["side"] == "post" and ("Arrival", "a") in x["events"]
        )
        layers = p.layers_by_node()
        node_id = next(iter(p.nodes))
        node = p.nodes[node_id]
        stage_count = sum(s.node_id == node_id for s in p.stages)
        static = (
            p.model.weight_bytes * layers[node_id] / p.model.num_layers
            + node.workspace_bytes
            + node.memory_margin_bytes
        )
        expected = (
            static
            + p.model.kv_bytes_per_token_per_layer
            * input_tokens
            * layers[node_id]
            + stage_count
            * p.model.activation_bytes_per_token
            * input_tokens
        )
        self.assertAlmostEqual(arrival["memory"][node_id], expected)

    def test_event_limit_is_explicit_error(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "AICCC evaluator event limit exceeded",
        ):
            evaluate(
                pipeline(),
                (RequestSpec("a", 0.0, 10, 100),),
                SLA(100, 100),
                ConstantProfiles(),
                max_events=1,
            )

    def test_shared_link_commitments_aggregate_to_overload(self):
        base = pipeline()
        input_tokens = 20
        sla = SLA(1.0, 100.0)
        residual_s = sla.ttft_s - 0.1
        path_bytes = (
            sum(len(boundary.route_link_ids) for boundary in base.boundaries)
            * base.model.activation_bytes_per_token
            * input_tokens
        )
        one_request_commitment = path_bytes / residual_s
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
        )

        self.assertTrue(single["safe"])
        self.assertFalse(pair["safe"])
        self.assertEqual(pair["first_violation"]["kind"], "network")
        self.assertGreater(pair["peak_network_utilization"], 1.0)


if __name__ == "__main__":
    unittest.main()
