"""Cache-only Decode-lifetime pressure probe for first-token compute queuing."""
from __future__ import annotations

from pathlib import Path
import json, math, statistics, sys, time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"scripts"))
from aiccc_evaluator import evaluate as evaluate_j0
from high_load_ttft_diagnosis import point_rows
from j2_reference_profile_validation import CachedProfiles, inventory_fingerprint
from research import RequestSpec,SLA,pipeline
from sla_aware_mvp.capacity import scale_workload

RAW=ROOT/"results"/"raw_reference"
PROTOCOL=ROOT/"config"/"first_token_decode_lifetime_pressure_probe_v1.json"
BASE_PROTOCOL=ROOT/"config"/"high_load_ttft_diagnosis_v1.json"
OUTPUT=ROOT/"results"/"first_token_decode_lifetime_pressure_probe_v1"


def pearson(xs,ys):
    if len(xs)<2:return None
    mx,my=statistics.fmean(xs),statistics.fmean(ys)
    dx=[x-mx for x in xs];dy=[y-my for y in ys]
    den=math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    return None if den<=0 else sum(x*y for x,y in zip(dx,dy))/den


def boundaries(core):
    out={}
    for snap in core["trace"]:
        if snap["side"]!="post":continue
        for ev,rid in snap["events"]:
            if ev=="PrefillToDecode":out[rid]=snap
    return out


def main():
    started=time.perf_counter()
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    base_protocol=json.loads(BASE_PROTOCOL.read_text(encoding="utf-8"))
    before=inventory_fingerprint(RAW)
    refs=[]
    for rel in base_protocol["physical_case_files"]:refs.extend(point_rows(ROOT/rel,base_protocol))
    refidx={(int(r["seed"]),float(r["intensity"]),r["request_id"]):r for r in refs}
    prof=CachedProfiles();rows=[]
    for rel in base_protocol["physical_case_files"]:
        source=json.loads((ROOT/rel).read_text(encoding="utf-8"))
        case=source["case"];seed=int(case["seed"])
        base=tuple(RequestSpec(**r) for r in source["requests"])
        specs={r.id:r for r in base}
        sla=SLA(**source["sla"]);p=pipeline(case["placement"],case.get("shift",0),case.get("hetero",False))
        for saved in source["rows"]:
            intensity=float(saved["lambda"]);workload=scale_workload(base,intensity)
            live_specs={r.id:r for r in workload}
            core=evaluate_j0(p,workload,sla,prof,intrinsic=True,trace=True,drain=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",decode_block_size=16)
            bmap=boundaries(core)
            for target in workload:
                snap=bmap[target.id]
                remaining_tokens=[];remaining_work=0.0;details=[]
                for rid,ledger in snap["ledger"].items():
                    if rid==target.id or ledger["phase"]!="decode":continue
                    rem=max(0.0,live_specs[rid].output_tokens-float(ledger["progress"]))
                    service=float(ledger["compute_s"])
                    remaining_tokens.append(rem);remaining_work+=rem*service
                    details.append({"request_id":rid,"remaining_tokens":rem,"progress":float(ledger["progress"]),"profile_service_s":service})
                ref=refidx[(seed,intensity,target.id)]
                rows.append({
                    "seed":seed,"case_id":case["id"],"intensity":intensity,"request_id":target.id,
                    "competing_decode_count":len(remaining_tokens),
                    "remaining_decode_tokens":sum(remaining_tokens),
                    "remaining_decode_profile_work_s":remaining_work,
                    "minimum_remaining_decode_tokens":min(remaining_tokens) if remaining_tokens else 0.0,
                    "long_lived_competitor_count":sum(x>=8 for x in remaining_tokens),
                    "first_decode_excess_s":ref["reference_first_decode_runtime_s"]-ref["j1_predicted_first_decode_profile_s"],
                    "details":details,
                })
    after=inventory_fingerprint(RAW)
    if before!=after:raise RuntimeError("cache inventory changed")
    outcome=[r["first_decode_excess_s"] for r in rows]
    signals=["competing_decode_count","remaining_decode_tokens","remaining_decode_profile_work_s","minimum_remaining_decode_tokens","long_lived_competitor_count"]
    correlations={s:pearson([float(r[s]) for r in rows],outcome) for s in signals}
    focus=[]
    for seed,rid,lo,hi in ((0,"azure-00011",0.96,1.28),(7,"azure-00014",0.32,0.64)):
        pair=[]
        for intensity in (lo,hi):
            r=next(x for x in rows if x["seed"]==seed and x["request_id"]==rid and abs(x["intensity"]-intensity)<1e-12)
            pair.append({"intensity":intensity,**{s:r[s] for s in signals},"first_decode_excess_s":r["first_decode_excess_s"],"details":r["details"]})
        focus.append({"seed":seed,"request_id":rid,"lower":pair[0],"higher":pair[1]})
    top=[]
    for r in sorted(rows,key=lambda x:x["first_decode_excess_s"],reverse=True)[:30]:
        top.append({"seed":r["seed"],"case_id":r["case_id"],"intensity":r["intensity"],"request_id":r["request_id"],
            "first_decode_excess_s":r["first_decode_excess_s"],**{s:r[s] for s in signals}})
    summary={"schema":1,"experiment_id":protocol["experiment_id"],"status":"complete","new_helix_runs":0,
        "physical_points":len({(r["seed"],r["intensity"]) for r in rows}),"request_rows":len(rows),
        "correlations":correlations,"focus_pairs":focus,"top_excess_rows":top,
        "raw_reference_inventory_before":before,"raw_reference_inventory_after":after,
        "elapsed_s":time.perf_counter()-started}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
    print("FIRST_TOKEN_DECODE_LIFETIME_PRESSURE_PROBE "+json.dumps({"correlations":correlations,"focus_pairs":focus,"top_excess_rows":top,"elapsed_s":summary["elapsed_s"]},sort_keys=True,allow_nan=False),flush=True)

if __name__=="__main__":main()
