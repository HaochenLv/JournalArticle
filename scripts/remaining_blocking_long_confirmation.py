"""Long-workload confirmation of the remaining-Prefill blocking correction only."""
from __future__ import annotations
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json, sys, time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

from aiccc_j1_evaluator import evaluate as evaluate_j1
from formal_core import CONFIG,load_workload
from j2_reference_profile_validation import CachedProfiles,classify_pair,inventory_fingerprint,load_reference,monotonic_summary
from research import SLA,pipeline
from sla_aware_mvp.capacity import scale_workload

PROTOCOL=ROOT/"config"/"remaining_blocking_long_confirmation.json"
OUTPUT=ROOT/"results"/"remaining_blocking_long_confirmation"
RAW=ROOT/"results"/"raw_reference"

def sla_for(kind):
    cfg=CONFIG["a100_slas"]["decode"] if kind=="a100" else CONFIG["heterogeneous_slas"]["decode"]
    return SLA(**cfg,fixed_overhead_s=CONFIG["fixed_overhead_s"])

def process_group(path_string):
    data=json.loads(Path(path_string).read_text(encoding="utf-8"));group=data["group"]
    _,base=load_workload(group["workload"]);hetero=group["kind"]=="heterogeneous";sla=sla_for(group["kind"]);prof=CachedProfiles()
    out=[]
    for saved in data["rows"]:
        if saved.get("status")!="ok":continue
        p=pipeline(group["link"],saved["shift"],hetero);w=scale_workload(base,saved["intensity"])
        ref,detail=load_reference(saved["reference_cache_key"],sla)
        result=evaluate_j1(
            p,w,sla,prof,intrinsic=True,
            blocking_policy="active-prefill-full-service-recovered-assumption",
            blocking_scale=1.0,
            blocking_mode="remaining-profile-service-full-intrinsic",
            ttft_profile_uncertainty_fraction=0.0,
            decode_block_size=16,
        )
        first=result["first_violation"]
        out.append({
            "group":group["id"],"shift":saved["shift"],"intensity":saved["intensity"],
            "evaluator_safe":result["safe"],"reference_safe":ref["safe"],
            "class":classify_pair(result["safe"],ref["safe"]),
            "evaluator_first_kind":None if first is None else first["kind"],
            "evaluator_first_object":None if first is None else first["object"],
            "core_trajectory_hash":result["core_trajectory_hash"],
            **{f"reference_{k}":v for k,v in detail.items()},
        })
    return out

def summarize(rows):
    counts={k:sum(r["class"]==k for r in rows) for k in ("safe_safe","false_acceptance","false_rejection","unsafe_unsafe")}
    ref_safe=sum(r["reference_safe"] for r in rows);ref_unsafe=len(rows)-ref_safe
    return {
        "pairs":len(rows),**counts,
        "agreement":(counts["safe_safe"]+counts["unsafe_unsafe"])/len(rows),
        "fa_rate_given_reference_unsafe":counts["false_acceptance"]/ref_unsafe if ref_unsafe else None,
        "fr_rate_given_reference_safe":counts["false_rejection"]/ref_safe if ref_safe else None,
        "false_acceptance_cases":[{
            "group":r["group"],"shift":r["shift"],"intensity":r["intensity"],
            "reference_max_normalized_excess":r["reference_max_normalized_excess"]
        } for r in rows if r["class"]=="false_acceptance"],
        "false_rejection_by_kind":{
            kind:sum(r["class"]=="false_rejection" and r["evaluator_first_kind"]==kind for r in rows)
            for kind in sorted({r["evaluator_first_kind"] for r in rows if r["class"]=="false_rejection"})
        },
    }

def capacity(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r["group"],r["shift"])].append(r)
    details=[]
    for (g,s),rs in sorted(groups.items()):
        e=monotonic_summary(rs,"evaluator_safe");ref=monotonic_summary(rs,"reference_safe")
        comparable=e["single_boundary_supported"] and ref["single_boundary_supported"]
        details.append({
            "group":g,"shift":s,"evaluator":e,"reference":ref,
            "comparable_edge":comparable,
            "exact_edge":comparable and (e["largest_safe"],e["nearest_unsafe_above"])==(ref["largest_safe"],ref["nearest_unsafe_above"])
        })
    comp=[x for x in details if x["comparable_edge"]]
    return {
        "case_shift_sequences":len(details),"comparable_edges":len(comp),
        "exact_edges":sum(x["exact_edge"] for x in comp),
        "evaluator_nonmonotone_sequences":sum(x["evaluator"]["nonmonotone"] for x in details),
        "reference_nonmonotone_sequences":sum(x["reference"]["nonmonotone"] for x in details),
        "details":details,
    }

def main():
    started=time.perf_counter();protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"));before=inventory_fingerprint(RAW)
    paths=[]
    for w in protocol["long_workloads"]:
        for kind in ("a100","heterogeneous"):
            m=sorted((ROOT/"results"/"formal"/"groups").glob(f"{w}-{kind}-*.json"))
            if len(m)!=1:raise RuntimeError(f"expected one group for {w} {kind}, got {len(m)}")
            paths.append(str(m[0]))
    rows=[]
    with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
        for rs in pool.map(process_group,paths):rows.extend(rs)
    after=inventory_fingerprint(RAW)
    if before!=after:raise RuntimeError("raw reference inventory changed")
    summary=summarize(rows);cap=capacity(rows);baseline=protocol["baseline_comparison"]["current_accounting"]
    result={
        "status":"complete","protocol":protocol,"new_helix_runs":0,
        "summary":summary,"capacity":cap,
        "comparison_to_prior_baseline":{
            "false_acceptance_change":summary["false_acceptance"]-baseline["false_acceptance"],
            "false_rejection_change":summary["false_rejection"]-baseline["false_rejection"],
            "agreement_change":summary["agreement"]-baseline["agreement"],
        },
        "elapsed_s":time.perf_counter()-started,
    }
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/"summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print("REMAINING_BLOCKING_LONG_SUMMARY "+json.dumps({
        "summary":summary,
        "capacity":{k:cap[k] for k in ("case_shift_sequences","comparable_edges","exact_edges","evaluator_nonmonotone_sequences")},
        "comparison_to_prior_baseline":result["comparison_to_prior_baseline"],
        "elapsed_s":result["elapsed_s"],
    },sort_keys=True),flush=True)

if __name__=="__main__":main()
