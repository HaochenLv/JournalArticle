"""Back-check the frozen tri-state TTFT compute-contention abstention guard.

The guard does not change J0/J1, does not add a fitted latency, and does not
simulate a production scheduler. It only refuses to certify a J1-safe workload
when the profile-driven first-Decode interval structurally contains more active
Decode requests than pipeline stages.
"""
from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

from aiccc_evaluator import evaluate as evaluate_j0
from aiccc_j1_evaluator import BLOCKING_MODE_REMAINING, evaluate as evaluate_j1
from formal_core import CONFIG, load_workload
from j2_reference_profile_validation import (
    CachedProfiles, inventory_fingerprint, load_reference, monotonic_summary
)
from research import RequestSpec, SLA, pipeline
from sla_aware_mvp.capacity import scale_workload

PROTOCOL=ROOT/"config"/"ttft_compute_contention_abstention_v1.json"
RAW=ROOT/"results"/"raw_reference"
OUTPUT=ROOT/"results"/"ttft_compute_contention_abstention_v1"


def first_decode_risk(p,w,sla,prof,j1,mode):
    core=evaluate_j0(
        p,w,sla,prof,intrinsic=True,trace=True,drain=True,
        blocking_policy="active-prefill-full-service-recovered-assumption",
        decode_block_size=16,
    )
    if core["trajectory_hash"]!=j1["core_trajectory_hash"]:
        raise RuntimeError("guard inspection changed the frozen J0 trajectory")
    first=j1["first_token_time_s"]
    p2d={}
    for snap in core["trace"]:
        if snap["side"]!="post":
            continue
        for ev,rid in snap["events"]:
            if ev=="PrefillToDecode":
                p2d[rid]=float(snap["time_s"])
    if set(p2d)!=set(first):
        raise RuntimeError("incomplete first-Decode boundaries")
    k=len(p.stages)
    per_request={}
    any_risk=False
    peak=0
    for rid in first:
        start=p2d[rid];end=float(first[rid])
        local=0
        for snap in core["trace"]:
            t=float(snap["time_s"])
            if t<start-1e-9 or t>end+1e-9:
                continue
            ledger=snap["ledger"].get(rid)
            if ledger is None or ledger["phase"]!="decode":
                continue
            local=max(local,int(snap["num_decode"]))
        risk=local>k if mode=="gt" else local>=k
        any_risk=any_risk or risk
        peak=max(peak,local)
        per_request[rid]={"peak_decode":local,"risk":risk}
    return {"risk":any_risk,"peak_decode":peak,"stage_count":k,"per_request":per_request}


def evaluate_point(p,w,sla,cache_key,population,identity):
    prof=CachedProfiles()
    ref,detail=load_reference(cache_key,sla)
    j1=evaluate_j1(
        p,w,sla,prof,intrinsic=True,trace=True,
        blocking_policy="active-prefill-full-service-recovered-assumption",
        blocking_scale=1.0,blocking_mode=BLOCKING_MODE_REMAINING,
        ttft_profile_uncertainty_fraction=0.0,decode_block_size=16,
    )
    strict=first_decode_risk(p,w,sla,prof,j1,"gt")
    ge=first_decode_risk(p,w,sla,prof,j1,"ge")
    if j1["safe"]:
        primary="uncertain" if strict["risk"] else "certified_safe"
        secondary="uncertain" if ge["risk"] else "certified_safe"
    else:
        primary=secondary="unsafe"
    return {
        "population":population,**identity,
        "base_safe":j1["safe"],"reference_safe":ref["safe"],
        "primary_verdict":primary,"secondary_verdict":secondary,
        "primary_risk":strict["risk"],"secondary_risk":ge["risk"],
        "primary_peak_decode":strict["peak_decode"],
        "stage_count":strict["stage_count"],
        "base_first_kind":None if j1["first_violation"] is None else j1["first_violation"]["kind"],
        "base_first_object":None if j1["first_violation"] is None else j1["first_violation"]["object"],
        "reference_cache_key":cache_key,
        **{f"reference_{k}":v for k,v in detail.items()},
    }


def process_design(path_string):
    path=Path(path_string);d=json.loads(path.read_text(encoding="utf-8"))
    if "reference_summary" not in d:return []
    case=d["case"];p=pipeline(case["placement"],case.get("shift",0),case.get("hetero",False))
    base=tuple(RequestSpec(**r) for r in d["requests"]);sla=SLA(**d["sla"])
    rows=[]
    for saved in d["rows"]:
        rows.append(evaluate_point(
            p,scale_workload(base,saved["lambda"]),sla,saved["reference"]["cache_key"],
            "design677",{"case":case["id"],"shift":case.get("shift",0),"intensity":saved["lambda"]},
        ))
    return rows


def sla_for(kind):
    cfg=CONFIG["a100_slas"]["decode"] if kind=="a100" else CONFIG["heterogeneous_slas"]["decode"]
    return SLA(**cfg,fixed_overhead_s=CONFIG["fixed_overhead_s"])


def process_formal(args):
    path_string,population=args
    d=json.loads(Path(path_string).read_text(encoding="utf-8"));group=d["group"]
    _,base=load_workload(group["workload"]);hetero=group["kind"]=="heterogeneous";sla=sla_for(group["kind"])
    rows=[]
    for saved in d["rows"]:
        if saved.get("status")!="ok":continue
        p=pipeline(group["link"],saved["shift"],hetero)
        rows.append(evaluate_point(
            p,scale_workload(base,saved["intensity"]),sla,saved["reference_cache_key"],population,
            {"case":group["id"],"shift":saved["shift"],"intensity":saved["intensity"]},
        ))
    return rows


def summarize(rows,verdict_key):
    n=len(rows);ref_safe=sum(r["reference_safe"] for r in rows);ref_unsafe=n-ref_safe
    certified=[r for r in rows if r[verdict_key]=="certified_safe"]
    uncertain=[r for r in rows if r[verdict_key]=="uncertain"]
    unsafe=[r for r in rows if r[verdict_key]=="unsafe"]
    false_cert=[r for r in certified if not r["reference_safe"]]
    safe_cert=[r for r in certified if r["reference_safe"]]
    safe_abst=[r for r in uncertain if r["reference_safe"]]
    unsafe_abst=[r for r in uncertain if not r["reference_safe"]]
    base_fr=[r for r in unsafe if r["reference_safe"]]
    return {
        "pairs":n,"reference_safe":ref_safe,"reference_unsafe":ref_unsafe,
        "certified_safe":len(certified),"uncertain":len(uncertain),"unsafe":len(unsafe),
        "false_certified_safe":len(false_cert),
        "unsafe_caught_by_abstention":len(unsafe_abst),
        "safe_sent_to_abstention":len(safe_abst),
        "base_false_rejection":len(base_fr),
        "binary_equivalent_false_rejection":len(base_fr)+len(safe_abst),
        "certification_coverage_given_reference_safe":len(safe_cert)/ref_safe if ref_safe else None,
        "unsafe_certification_rate_given_reference_unsafe":len(false_cert)/ref_unsafe if ref_unsafe else None,
        "false_certified_cases":[{
            "case":r["case"],"shift":r["shift"],"intensity":r["intensity"],
            "reference_max_normalized_excess":r["reference_max_normalized_excess"],
            "peak_decode":r["primary_peak_decode"],
        } for r in false_cert],
        "unsafe_abstention_cases":[{
            "case":r["case"],"shift":r["shift"],"intensity":r["intensity"],
            "reference_max_normalized_excess":r["reference_max_normalized_excess"],
            "peak_decode":r["primary_peak_decode"],
        } for r in unsafe_abst],
    }


def capacity(rows,verdict_key):
    groups=defaultdict(list)
    for r in rows:groups[(r["case"],r["shift"])].append(r)
    details=[]
    for key,rs in sorted(groups.items()):
        adapted=[{**r,"cert":r[verdict_key]=="certified_safe"} for r in rs]
        e=monotonic_summary(adapted,"cert");ref=monotonic_summary(adapted,"reference_safe")
        comparable=e["single_boundary_supported"] and ref["single_boundary_supported"]
        details.append({
            "case":key[0],"shift":key[1],"guard":e,"reference":ref,
            "comparable_edge":comparable,
            "exact_edge":comparable and (e["largest_safe"],e["nearest_unsafe_above"])==(ref["largest_safe"],ref["nearest_unsafe_above"]),
        })
    comp=[x for x in details if x["comparable_edge"]]
    return {
        "sequences":len(details),"comparable_edges":len(comp),"exact_edges":sum(x["exact_edge"] for x in comp),
        "guard_nonmonotone":sum(x["guard"]["nonmonotone"] for x in details),
        "reference_nonmonotone":sum(x["reference"]["nonmonotone"] for x in details),
    }


def main():
    started=time.perf_counter();protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"));before=inventory_fingerprint(RAW)
    design_paths=[]
    for folder in ("results/diagnostic/nominal_gap","results/diagnostic/partition_ranking"):
        for path in sorted((ROOT/folder).glob("*.json")):
            if "reference_summary" in json.loads(path.read_text(encoding="utf-8")):
                design_paths.append(str(path))
    formal=[]
    for workload,pop in (
        ("h103-o500-d30","short528"),("h105-o900-d30","short528"),
        ("h104-o700-d120","long490"),("h106-o1100-d120","long490"),
    ):
        for kind in ("a100","heterogeneous"):
            matches=sorted((ROOT/"results"/"formal"/"groups").glob(f"{workload}-{kind}-*.json"))
            if len(matches)!=1:raise RuntimeError(f"expected one group for {workload} {kind}")
            formal.append((str(matches[0]),pop))
    rows=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for rs in pool.map(process_design,design_paths):rows.extend(rs)
        for rs in pool.map(process_formal,formal):rows.extend(rs)
    after=inventory_fingerprint(RAW)
    if before!=after:raise RuntimeError("raw reference inventory changed")
    result={"schema":1,"experiment_id":protocol["experiment_id"],"status":"complete","new_helix_runs":0,
        "raw_reference_inventory_before":before,"raw_reference_inventory_after":after,"elapsed_s":time.perf_counter()-started,
        "populations":{}}
    for pop in ("design677","short528","long490"):
        subset=[r for r in rows if r["population"]==pop]
        result["populations"][pop]={
            "primary_gt_K":summarize(subset,"primary_verdict"),
            "secondary_ge_K":summarize(subset,"secondary_verdict"),
            "primary_capacity":capacity(subset,"primary_verdict"),
        }
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/"summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
    print("TTFT_COMPUTE_CONTENTION_ABSTENTION "+json.dumps(result,sort_keys=True,allow_nan=False),flush=True)

if __name__=="__main__":main()
