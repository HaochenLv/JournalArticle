"""Diagnostic back-check of the frozen accounting candidate on the 677-point design set."""
from __future__ import annotations
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json, sys, time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

from aiccc_j1_evaluator import evaluate as evaluate_j1
from j2_reference_profile_validation import CachedProfiles,classify_pair,inventory_fingerprint,load_reference
from research import RequestSpec,SLA,pipeline
from sla_aware_mvp.capacity import scale_workload

PROTOCOL=ROOT/"config"/"accounting_candidate_backcheck.json"
OUTPUT=ROOT/"results"/"accounting_candidate_backcheck"
RAW=ROOT/"results"/"raw_reference"

def process_case(args):
    source,path_string,comparisons=args
    d=json.loads(Path(path_string).read_text(encoding="utf-8"))
    if "reference_summary" not in d:return []
    case=d["case"];p=pipeline(case["placement"],case.get("shift",0),case.get("hetero",False))
    base=tuple(RequestSpec(**r) for r in d["requests"]);sla=SLA(**d["sla"]);prof=CachedProfiles()
    out=[]
    for saved in d["rows"]:
        w=scale_workload(base,saved["lambda"])
        ref,detail=load_reference(saved["reference"]["cache_key"],sla)
        baseline_hash=None;baseline_final=None
        for comp in comparisons:
            result=evaluate_j1(
                p,w,sla,prof,intrinsic=True,
                blocking_policy="active-prefill-full-service-recovered-assumption",
                blocking_scale=1.0,
                blocking_mode=comp["blocking_mode"],
                ttft_profile_uncertainty_fraction=comp["ttft_profile_uncertainty_fraction"],
                decode_block_size=16,
            )
            if baseline_hash is None:
                baseline_hash=result["core_trajectory_hash"];baseline_final=result["final_time_s"]
            elif result["core_trajectory_hash"]!=baseline_hash or result["final_time_s"]!=baseline_final:
                raise RuntimeError("candidate changed frozen J0 trajectory")
            first=result["first_violation"]
            out.append({
                "source":source,"case":case["id"],"intensity":saved["lambda"],
                "comparison":comp["label"],
                "evaluator_safe":result["safe"],"reference_safe":ref["safe"],
                "class":classify_pair(result["safe"],ref["safe"]),
                "evaluator_first_kind":None if first is None else first["kind"],
                "evaluator_first_object":None if first is None else first["object"],
                "evaluator_max_standard_ttft_s":result["max_standard_ttft_s"],
                "evaluator_max_average_tpot_s":result["max_average_tpot_s"],
                "reference_cache_key":saved["reference"]["cache_key"],
                **{f"reference_{k}":v for k,v in detail.items()},
            })
    return out

def summarize(rows,label):
    g=[r for r in rows if r["comparison"]==label]
    counts={k:sum(r["class"]==k for r in g) for k in ("safe_safe","false_acceptance","false_rejection","unsafe_unsafe")}
    fas=[r for r in g if r["class"]=="false_acceptance"]
    return {
        "comparison":label,"pairs":len(g),**counts,
        "agreement":(counts["safe_safe"]+counts["unsafe_unsafe"])/len(g),
        "false_acceptance_cases":[{
            "source":r["source"],"case":r["case"],"intensity":r["intensity"],
            "reference_max_standard_ttft_s":r["reference_max_standard_ttft_s"],
            "reference_max_average_tpot_s":r["reference_max_average_tpot_s"],
            "reference_max_normalized_excess":r["reference_max_normalized_excess"],
            "evaluator_max_standard_ttft_s":r["evaluator_max_standard_ttft_s"],
            "evaluator_first_kind":r["evaluator_first_kind"],
            "evaluator_first_object":r["evaluator_first_object"],
        } for r in fas],
    }

def main():
    started=time.perf_counter();protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"));before=inventory_fingerprint(RAW)
    tasks=[]
    for folder_string in protocol["population"]:
        folder=ROOT/folder_string;source=folder.name
        for path in sorted(folder.glob("*.json")):
            d=json.loads(path.read_text(encoding="utf-8"))
            if "reference_summary" in d:tasks.append((source,str(path),protocol["comparison"]))
    rows=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for rs in pool.map(process_case,tasks):rows.extend(rs)
    after=inventory_fingerprint(RAW)
    if before!=after:raise RuntimeError("raw reference inventory changed")
    summaries=[summarize(rows,x["label"]) for x in protocol["comparison"]]
    result={"status":"complete","protocol":protocol,"new_helix_runs":0,"physical_rows":len(rows)//len(protocol["comparison"]),"summaries":summaries,"elapsed_s":time.perf_counter()-started}
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT/"summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    print("ACCOUNTING_BACKCHECK_SUMMARY "+json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":main()
