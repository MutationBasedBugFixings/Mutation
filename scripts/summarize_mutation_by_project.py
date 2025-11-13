#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, csv, json, re, sys
from pathlib import Path
from collections import defaultdict

# ---------- Utils ----------
def _read_csv_any(path: Path):
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            rdr = csv.reader(f)
            rows = list(rdr)
            if not rows: return []
            hdr = [h.strip().lower() for h in rows[0]]
            out=[]
            for r in rows[1:]:
                if not r: continue
                row = {hdr[i]: (r[i].strip() if i < len(hdr) else "") for i in range(len(hdr))}
                out.append(row)
            return out
    except Exception:
        return []

def _print_table(rows, cols, title=None):
    if title: print(f"\n== {title} ==")
    if not rows:
        print("No data."); return
    w = {c: max(len(c), max(len(str(r.get(c,""))) for r in rows)) for c in cols}
    print(" | ".join(c.ljust(w[c]) for c in cols))
    print("-+-".join("-"*w[c] for c in cols))
    for r in rows:
        print(" | ".join(str(r.get(c,"")).ljust(w[c]) for c in cols))

# ---------- MUTATION SCAN (MAJOR / PIT) ----------
def _infer_proj_bug_from_path(p: Path):
    s = str(p)
    m = re.search(r"[\\/](logs|LOGS)[\\/]([^\\/]+)-(\d+)[\\/]", s)
    if m:
        return m.group(2), m.group(3)
    return None, None

def parse_mutation_summary_file(path: Path, tool_hint: str):
    rows = _read_csv_any(path)
    out=[]
    for r in rows:
        eng = (r.get("engine") or tool_hint or "").strip().upper()
        proj = (r.get("project") or "").strip()
        bug  = (r.get("bug") or "").strip()
        tot  = int(r.get("mutants_total") or r.get("total") or r.get("mutants") or 0)
        kld  = int(r.get("killed") or 0)
        srv  = int(r.get("survived") or (tot - kld if tot>=kld else 0))
        if not proj or not bug:
            ip, ib = _infer_proj_bug_from_path(path)
            proj = proj or ip
            bug  = bug  or ib
        if proj and bug:
            out.append((proj, bug, eng or tool_hint, tot, kld, srv))
    return out

def scan_mutation_logs(log_root: Path):
    per_bug=[]
    for bugdir in sorted(log_root.glob("*-*")):
        if not bugdir.is_dir(): continue
        msum = bugdir / "major_summary.csv"
        psum = bugdir / "pit_summary.csv"
        if msum.exists(): per_bug += parse_mutation_summary_file(msum, "MAJOR")
        if psum.exists(): per_bug += parse_mutation_summary_file(psum, "PIT")
    return per_bug

def aggregate_mutation(per_bug):
    agg_by_tool = defaultdict(lambda: {"bugs": set(), "total": 0, "killed": 0, "survived": 0})
    agg_all     = defaultdict(lambda: {"bugs": set(), "total": 0, "killed": 0, "survived": 0})

    for proj, bug, tool, tot, kld, srv in per_bug:
        A = agg_by_tool[(proj, tool)]
        A["bugs"].add(bug); A["total"] += tot; A["killed"] += kld; A["survived"] += srv
        B = agg_all[proj]
        B["bugs"].add(bug); B["total"] += tot; B["killed"] += kld; B["survived"] += srv

    proj_rows=[]
    for (proj, tool), A in sorted(agg_by_tool.items()):
        total, killed, survived = A["total"], A["killed"], A["survived"]
        proj_rows.append({
            "project": proj,
            "tool": tool,
            "bugs_covered": len(A["bugs"]),
            "mutants_total": total,
            "killed": killed,
            "survived": survived,
            "kill_rate": f"{(killed/total) if total else 0:.3f}"
        })

    for proj, A in sorted(agg_all.items()):
        total, killed, survived = A["total"], A["killed"], A["survived"]
        proj_rows.append({
            "project": proj,
            "tool": "MAJOR+PIT",
            "bugs_covered": len(A["bugs"]),
            "mutants_total": total,
            "killed": killed,
            "survived": survived,
            "kill_rate": f"{(killed/total) if total else 0:.3f}"
        })

    bug_rows=[]
    for proj, bug, tool, tot, kld, srv in sorted(per_bug, key=lambda x: (x[0], int(x[1]), x[2])):
        bug_rows.append({
            "project": proj,
            "bug": bug,
            "tool": tool,
            "mutants_total": tot,
            "killed": kld,
            "survived": srv,
            "kill_rate": f"{(kld/tot) if tot else 0:.3f}"
        })
    return proj_rows, bug_rows

# ---------- APR SCAN ----------
D4J_PROJECTS = {
    "Time","Lang","Chart","Math","Closure","Mockito","Cli","Csv",
    "Compress","JxPath","Collections","Codec","Jsoup","Gson","JacksonCore",
    "JacksonDatabind","JacksonXml"
}

def _read_lines(path: Path):
    try:
        return [x.strip() for x in path.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    except Exception:
        return []

def _auto_extract_from_test_results(bugdir: Path):
    csv_path = bugdir / "test_results.csv"
    plausible, correct = set(), set()
    if not csv_path.exists():
        return plausible, correct
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                rid = r.get("id") or r.get("patch_id") or r.get("patch") or r.get("name")
                status = (r.get("status") or r.get("result") or "").strip().upper()
                is_plaus = (r.get("is_plausible") or "").strip().lower() in {"1","true","yes"} or status in {"PASS","PLAUSIBLE"}
                is_correct = (r.get("is_correct") or "").strip().lower() in {"1","true","yes"} or status in {"CORRECT","TRUE_POSITIVE"}
                if rid and is_plaus: plausible.add(rid)
                if rid and is_correct: correct.add(rid)
        if plausible: (csv_path.parent / "plausible.txt").write_text("\n".join(sorted(plausible))+"\n")
        if correct:   (csv_path.parent / "correct.txt").write_text("\n".join(sorted(correct))+"\n")
    except Exception:
        pass
    return plausible, correct

def _load_plausible(bugdir: Path):
    for name in ["plausible.txt","plausible.json","test_results.csv"]:
        p = bugdir / name
        if not p.exists(): continue
        if p.name == "plausible.txt":
            return set(_read_lines(p))
        if p.name == "plausible.json":
            try:
                data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, list):
                    return {x if isinstance(x,str) else x.get("id") for x in data}
            except Exception:
                return set()
        if p.name == "test_results.csv":
            plaus, _ = _auto_extract_from_test_results(bugdir)
            return plaus
    return set()

def _load_correct(bugdir: Path):
    for name in ["correct.txt","correct.json","test_results.csv"]:
        p = bugdir / name
        if not p.exists(): continue
        if p.name == "correct.txt":
            return set(_read_lines(p))
        if p.name == "correct.json":
            try:
                data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, list):
                    return {x if isinstance(x,str) else x.get("id") for x in data}
            except Exception:
                return set()
        if p.name == "test_results.csv":
            _, corr = _auto_extract_from_test_results(bugdir)
            return corr
    return set()

def _count_generated(bugdir: Path, patches_dirname: str, patterns):
    candidates=[]
    if (bugdir/patches_dirname).is_dir():
        candidates.append(bugdir/patches_dirname)
    for alt in ["patches","generated_patches","output_patches","out/patches","results/patches"]:
        candidates += list((bugdir).rglob(alt))
    seen=set(); total=0
    for pd in candidates:
        if not pd.is_dir(): continue
        if pd in seen: continue
        seen.add(pd)
        for pat in patterns:
            total += len(list(pd.rglob(pat)))
    return total

def _find_project_bug_from_path(path: Path):
    """
    Robustly infer (project, bug) from many layouts:
      - .../<Project>/<bug>/...
      - .../<Project>-<bug>/...
      - .../logs/<Project>-<bug>/...
      - .../apr_runs/<Project>-<bug>/...
    """
    # 1) Project/bug as adjacent path segments
    parts = list(path.resolve().parts)
    for i, part in enumerate(parts):
        if part in D4J_PROJECTS and i+1 < len(parts):
            m = re.match(r"(\d+)", parts[i+1])
            if m: return part, m.group(1)

    # 2) Project-bug single segment anywhere (e.g., Time-19)
    s = str(path.resolve())
    m = re.search(r"[\\/](?P<proj>[A-Za-z]+)-(?P<bug>\d+)(?:[\\/]|$)", s)
    if m and m.group("proj") in D4J_PROJECTS:
        return m.group("proj"), m.group("bug")

    # 3) Fallback to logs-style pattern
    ip, ib = _infer_proj_bug_from_path(path)
    if ip and ib:
        return ip, ib

    return None, None

def scan_apr(apr_root: Path, patches_dirname: str, gen_patterns, debug=False):
    agg = defaultdict(lambda: {"bugs": set(), "generated": 0, "plausible": 0, "correct": 0, "fixed_bugs": set()})
    candidates=set()
    signals = {"plausible.txt","plausible.json","test_results.csv","correct.txt","correct.json"}

    for p in apr_root.rglob("*"):
        if not p.is_dir(): continue
        try:
            names = {x.name for x in p.iterdir()}
        except Exception:
            names=set()
        if ("patches" in names) or ("generated_patches" in names) or (signals & names):
            candidates.add(p)
        else:
            if list(p.glob("**/patches")) or list(p.glob("**/generated_patches")):
                candidates.add(p)

    # optional debug: show how many APR candidates we saw
    if debug:
        print(f"[APR DEBUG] candidates found: {len(candidates)}", file=sys.stderr)

    for bugdir in sorted(candidates):
        proj, bug = _find_project_bug_from_path(bugdir)
        if not proj or not bug:
            if debug:
                print(f"[APR DEBUG] skip (no proj/bug): {bugdir}", file=sys.stderr)
            continue

        gen  = _count_generated(bugdir, patches_dirname, gen_patterns)
        plaus= _load_plausible(bugdir)
        corr = _load_correct(bugdir)

        A = agg[proj]
        A["bugs"].add(bug)
        A["generated"] += gen
        A["plausible"] += len(plaus)
        A["correct"]   += len(corr)
        if corr:
            A["fixed_bugs"].add(bug)

    rows=[]
    for proj, A in sorted(agg.items()):
        rows.append({
            "project": proj,
            "num_bugs": len(A["bugs"]),
            "num_generated_patches": A["generated"],
            "num_plausible_patches": A["plausible"],
            "num_correct_patches": A["correct"],
            "num_fixed_bugs": len(A["fixed_bugs"]),
        })
    return rows

# ---------- MAIN ----------
def main():
    ap = argparse.ArgumentParser(description="Build supervisor-ready table by merging mutation (MAJOR/PIT) and APR metrics.")
    ap.add_argument("log_root", type=Path, help="Path to mutation logs root")
    ap.add_argument("--apr-root", type=Path, default=None, help="APR results root (default: log_root)")
    ap.add_argument("--patches-dirname", default="patches")
    ap.add_argument("--gen-pattern", action="append", help="Globs for generated patches (repeatable)")
    ap.add_argument("--outdir", type=Path, default=Path("./"))
    ap.add_argument("--apr-debug", action="store_true", help="Print APR scan debug info to stderr")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    apr_root = args.apr_root or args.log_root
    gen_patterns = args.gen_pattern or ["*.patch","*.diff","*.edits","patch*.txt"]

    # 1) Mutation summaries
    per_bug = scan_mutation_logs(args.log_root)
    proj_rows, bug_rows = aggregate_mutation(per_bug)

    mut_proj_csv = args.outdir / "mutation_summary_by_project.csv"
    mut_bug_csv  = args.outdir / "mutation_summary_by_bug.csv"
    if proj_rows:
        with mut_proj_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(proj_rows[0].keys()))
            w.writeheader(); w.writerows(proj_rows)
    if bug_rows:
        with mut_bug_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(bug_rows[0].keys()))
            w.writeheader(); w.writerows(bug_rows)

    _print_table(proj_rows, ["project","tool","bugs_covered","mutants_total","killed","survived","kill_rate"], "Mutation (project × tool)")
    _print_table(bug_rows, ["project","bug","tool","mutants_total","killed","survived","kill_rate"], "Mutation (per-bug)")

    # 2) APR summary by project
    apr_rows = scan_apr(apr_root, args.patches_dirname, gen_patterns, debug=args.apr_debug)
    apr_csv = args.outdir / "apr_summary_by_project.csv"
    if apr_rows:
        with apr_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(apr_rows[0].keys()))
            w.writeheader(); w.writerows(apr_rows)
    _print_table(apr_rows, ["project","num_bugs","num_generated_patches","num_plausible_patches","num_correct_patches","num_fixed_bugs"], "APR (project totals)")

    # 3) Join APR + Mutation (use combined MAJOR+PIT row)
    apr_by_proj = {r["project"]: r for r in apr_rows}
    mut_combined = {r["project"]: r for r in proj_rows if r.get("tool") == "MAJOR+PIT"}

    final_rows=[]
    for proj in sorted(set(list(apr_by_proj.keys()) + list(mut_combined.keys()))):
        apr = apr_by_proj.get(proj, {})
        mut = mut_combined.get(proj, {})
        total = int(mut.get("mutants_total", 0) or 0)
        killed= int(mut.get("killed", 0) or 0)
        survived = int(mut.get("survived", 0) or 0)
        kill_rate = f"{(killed/total) if total else 0:.3f}"
        final_rows.append({
            "project": proj,
            "num_bugs": apr.get("num_bugs", 0),
            "num_generated_patches": apr.get("num_generated_patches", 0),
            "num_plausible_patches": apr.get("num_plausible_patches", 0),
            "num_correct_patches": apr.get("num_correct_patches", 0),
            "num_fixed_bugs": apr.get("num_fixed_bugs", 0),
            "mutants_total_all": total,
            "killed_all": killed,
            "survived_all": survived,
            "kill_rate_all": kill_rate
        })

    final_csv = args.outdir / "supervisor_table.csv"
    if final_rows:
        with final_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(final_rows[0].keys()))
            w.writeheader(); w.writerows(final_rows)

    _print_table(final_rows, [
        "project","num_bugs","num_generated_patches","num_plausible_patches","num_correct_patches",
        "num_fixed_bugs","mutants_total_all","killed_all","survived_all","kill_rate_all"
    ], "Supervisor Table (APR + Mutation combined)")

    print(f"\n[Saved] {mut_proj_csv}")
    print(f"[Saved] {mut_bug_csv}")
    print(f"[Saved] {apr_csv}")
    print(f"[Saved] {final_csv}")

if __name__ == "__main__":
    main()
