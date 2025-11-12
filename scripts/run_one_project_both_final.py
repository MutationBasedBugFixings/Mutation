#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run MAJOR (on FIXED rev, JDK8 for compilation) and PIT (on FIXED rev, JDK11 runtime)
for Defects4J projects, using Defects4J's built-in mutation wrappers.

- MAJOR via 'defects4j mutation -r major' (MajorCompiler uses -Dmajor.java.home=JDK8)
- PIT   via 'defects4j mutation -r pit'   (wrapper wires PIT dependencies)
- Defects4J CLI itself must run under Java 11.

This version adds:
  * Parallel PIT workers (threads/forks) and per-bug parallelism (--jobs)
  * Memory tuning flags
  * --list-bugs, --bugs, --jobs, --threads, --forks, --jvm-xmx
  * Tolerant MAJOR + PIT execution (non-fatal RuntimeException / test failures)
  * Skip bugs that already have MAJOR + PIT summary CSVs
"""

import os, re, csv, sys, shutil, subprocess, argparse
from pathlib import Path
from typing import List, Tuple, Set, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIG
# ============================================================
D4J_HOME   = os.environ.get("D4J_HOME", "/cd to directory/defects4j")
DEFECTS4J  = f"{D4J_HOME}/framework/bin/defects4j"
EXPROOT    = os.environ.get("EXPERIMENT_ROOT", "/cd to directory/my_mutation_experiments")

JAVA11     = os.environ.get("JAVA11_HOME", "/usr/lib/jvm/java-11-openjdk-amd64")
JAVA8      = os.environ.get("JAVA8_HOME",  "/usr/lib/jvm/java-8-openjdk-amd64")
MAJOR_JAVA_HOME = os.environ.get("MAJOR_JAVA_HOME", JAVA8)

WORK       = Path(EXPROOT) / "d4j_work"; WORK.mkdir(parents=True, exist_ok=True)
LOGS_ROOT  = Path(EXPROOT) / "logs";     LOGS_ROOT.mkdir(parents=True, exist_ok=True)
RESULTS    = Path(EXPROOT) / "results";  RESULTS.mkdir(parents=True, exist_ok=True)

# ============================================================
# ENVIRONMENT HELPERS
# ============================================================
def _mk_env(java_home: str, jvm_xmx: str = "8g") -> dict:
    e = os.environ.copy()
    e["JAVA_HOME"] = java_home
    e["PATH"] = f"{java_home}/bin:/usr/bin:" + e.get("PATH", "")
    tools_jar = Path(java_home) / "lib" / "tools.jar"
    opts = ["-Dfile.encoding=UTF-8", "-Dsun.jnu.encoding=UTF-8", "-Dmajor.log.level=FINE"]
    if tools_jar.exists():
        opts.insert(0, f"-Xbootclasspath/a:{tools_jar}")
    e["ANT_OPTS"]   = f"-Xmx{jvm_xmx} " + " ".join(opts)
    e["MAVEN_OPTS"] = f"-Xmx{jvm_xmx} -Dmaven.repo.local={Path.home() / '.m2/repository'}"
    return e

ENV11 = None
ENV8  = None

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def run(cmd: List[str], cwd: Optional[str] = None, env=None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n>>> RUN: {' '.join(cmd)}\n    CWD: {cwd or os.getcwd()}")
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout, end="")
    if p.stderr:
        sys.stderr.write(p.stderr)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}")
    return p

def ensure_time_m2_jars():
    base = Path(D4J_HOME) / "framework/projects/Time/lib"
    candidates = [
        base / "org/joda/joda-convert/1.2/joda-convert-1.2.jar",
        base / "junit/junit/3.8.2/junit-3.8.2.jar",
    ]
    for src in candidates:
        if src.exists():
            dst = Path.home() / ".m2/repository" / src.relative_to(base)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)

def list_bugs(project: str) -> List[str]:
    f = Path(D4J_HOME) / f"framework/projects/{project}/active-bugs.csv"
    if not f.exists():
        raise FileNotFoundError(f"{f} not found")
    ids = [line.split(",")[0].strip() for line in f.read_text().splitlines() if re.match(r"^\d+", line)]
    return sorted(set(ids), key=lambda x: int(x))

def checkout_rev(project: str, bug: str, rev: str, env11) -> Path:
    tgt = WORK / f"{project}-{bug}-{'buggy' if rev=='b' else 'fixed'}"
    if not tgt.exists():
        run([DEFECTS4J, "checkout", "-p", project, "-v", f"{bug}{rev}", "-w", str(tgt)], env=env11)
    return tgt

def export_prop(prop: str, wd: Path, env11) -> str:
    p = run([DEFECTS4J, "export", "-p", prop], cwd=str(wd), env=env11, check=False)
    return (p.stdout or "").strip()

def _unique_pkg_prefixes(names: List[str]) -> Set[str]:
    pkgs: Set[str] = set()
    for c in names:
        c = c.replace("/", ".").replace(".java", "")
        if "." in c:
            pkgs.add(".".join(c.split(".")[:-1]))
    result: Set[str] = set()
    for p in sorted(pkgs):
        if not any(p.startswith(q + ".") for q in result):
            result.add(p)
    return {p + ".*" for p in result} if result else {"*"}

# ============================================================
# RESULT-SKIP HELPER
# ============================================================
def load_existing_summaries(project: str, bug: str) -> Optional[List[List]]:
    """
    If this bug already has per-bug summary CSVs (MAJOR + PIT),
    load them and return as rows:
      [["MAJOR", project, bug, total, killed, survived],
       ["PIT",   project, bug, total, killed, survived]]
    Otherwise return None.
    """
    bug_dir = LOGS_ROOT / f"{project}-{bug}"
    major_csv = bug_dir / "major_summary.csv"
    pit_csv   = bug_dir / "pit_summary.csv"

    rows: List[List] = []

    def _read_single(path: Path) -> Optional[List]:
        if not path.exists():
            return None
        with path.open(newline="") as f:
            rdr = csv.reader(f)
            next(rdr, None)  # skip header
            for row in rdr:
                # first data row
                return row
        return None

    major_row = _read_single(major_csv)
    pit_row   = _read_single(pit_csv)

    # Only consider it "done" if both engines have summaries
    if major_row and pit_row:
        rows.append(major_row)
        rows.append(pit_row)
        return rows
    return None

# ============================================================
# MAJOR ENGINE (tolerant)
# ============================================================
def run_major(project: str, bug: str, bug_dir: Path, env11, env8) -> Tuple[int,int,int]:
    ensure_time_m2_jars()
    out = LOGS_ROOT / f"{project}-{bug}"
    out.mkdir(parents=True, exist_ok=True)
    mutants_log = out / "mutants.log"
    kill_csv    = out / "kill.csv"

    run([DEFECTS4J, "compile"], cwd=str(bug_dir), env=env11, check=True)

    mut_cmd = [
        DEFECTS4J, "mutation",
        "-w", str(bug_dir),
        "-r", "major",
        f"-Dmajor.java.home={MAJOR_JAVA_HOME}",
        f"-Dmajor.export.mutants.file={mutants_log}",
        f"-Dmajor.kill.log={kill_csv}",
        "-Dhaltonfailure=false",
        "-Dmajor.log.level=FINE"
    ]

    res = run(mut_cmd, cwd=str(bug_dir), env=env11, check=False)
    if res.returncode != 0:
        print(f"[WARN] MAJOR returned non-zero exit code ({res.returncode}) for {project}-{bug}; parsing logs anyway.")

    gen = kill = None
    for line in (res.stdout or "").splitlines():
        m = re.search(r"Mutants generated:\s*(\d+)", line)
        if m: gen = int(m.group(1))
        m = re.search(r"Mutants killed:\s*(\d+)", line)
        if m: kill = int(m.group(1))

    if not mutants_log.exists():
        default_log = bug_dir / "mutants.log"
        if default_log.exists():
            shutil.copy2(default_log, mutants_log)

    total = gen if gen is not None else 0
    killed = kill if kill is not None else 0

    if not kill_csv.exists():
        default_kill = bug_dir / "kill.csv"
        if default_kill.exists():
            shutil.copy2(default_kill, kill_csv)

    if kill_csv.exists() and (gen is None or kill is None):
        total = killed = 0
        with kill_csv.open(newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                total += 1
                status = (row.get("status") or row.get("Status") or
                          row.get("result") or row.get("Result") or
                          row.get("outcome") or "").lower()
                if status in ("killed", "timeout", "memoryerror"):
                    killed += 1

    survived = max(0, (total or 0) - (killed or 0))
    with (out / "major_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["engine","project","bug","mutants_total","killed","survived"])
        w.writerow(["MAJOR", project, bug, total, killed, survived])

    print(f"[MAJOR DONE] {project}-{bug} total={total} killed={killed} survived={survived}")
    return total, killed, survived

# ============================================================
# PIT ENGINE (tolerant)
# ============================================================
def run_pit(project: str, bug: str, bug_dir: Path, env11,
            threads: int, fork_count: int, jvm_xmx: str) -> Tuple[int,int,int]:
    """
    Run PIT via 'defects4j mutation -r pit' on the FIXED revision.
    Non-zero exit (e.g., Compress-20 TAR failure) is treated as warning.
    """
    out = LOGS_ROOT / f"{project}-{bug}"
    out.mkdir(parents=True, exist_ok=True)
    run([DEFECTS4J, "compile"], cwd=str(bug_dir), env=env11, check=True)

    pit_params = [
        DEFECTS4J, "mutation",
        "-w", str(bug_dir),
        "-r", "pit",
        f"-Dpit.report.dir={out}",
        f"-Dpit.failWhenNoMutations=false",
        f"-Dpit.skipFailingTests=true",
        f"-Dpit.timeoutConstant=300",
        f"-Dpit.timestampedReports=false",
        f"-Dpit.outputFormats=CSV",
        f"-Dpit.threads={threads}",
        f"-Dpit.forkCount={fork_count}",
        f"-Dpit.jvmArgs=-Xmx{jvm_xmx}"
    ]

    classes_rel = [c.strip() for c in export_prop("classes.relevant", bug_dir, env11).splitlines() if c.strip()]
    if classes_rel:
        pkgs = ",".join(sorted(_unique_pkg_prefixes(classes_rel)))
        pit_params.append(f"-Dpit.targetClasses={pkgs}")
    pit_params.append("-Dpit.targetTests=*Test")

    res = run(pit_params, cwd=str(bug_dir), env=env11, check=False)
    if res.returncode != 0:
        print(f"[WARN] PIT returned non-zero exit code ({res.returncode}) for {project}-{bug}; "
              f"attempting to parse logs or continue with zeros.")

    candidates = [out / "mutations.csv", out / "pitest-mutations.csv"]
    candidates += list(bug_dir.glob("**/pit-reports/**/mutations.csv"))
    candidates += list(bug_dir.glob("**/mutations.csv"))
    found = next((p for p in candidates if p.exists()), None)

    if not found:
        gen = kill = None
        for line in (res.stdout or "").splitlines():
            m = re.search(r"Mutants generated:\s*(\d+)", line)
            if m: gen = int(m.group(1))
            m = re.search(r"Mutants killed:\s*(\d+)", line)
            if m: kill = int(m.group(1))
        if gen is not None and kill is not None:
            total, killed = gen, kill
        else:
            print(f"[WARN] No PIT report for {project}-{bug}; recording zeros.")
            total = killed = 0
    else:
        total = killed = 0
        with found.open(newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                total += 1
                status = (row.get("Status") or row.get("status") or
                          row.get("result") or row.get("Result") or "").lower()
                if status in ("killed","timeout","memoryerror"):
                    killed += 1

    survived = max(0, total - killed)
    with (out / "pit_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["engine","project","bug","mutants_total","killed","survived"])
        w.writerow(["PIT", project, bug, total, killed, survived])
    print(f"[PIT DONE] {project}-{bug} total={total} killed={killed} survived={survived}")
    return total, killed, survived

# ============================================================
# PER-BUG EXECUTOR & MAIN
# ============================================================
def process_one_bug(project: str, bug: str, jvm_xmx: str, threads: int, forks: int) -> Tuple[str, List[List]]:
    # 1) Check if we already have results for this bug
    existing = load_existing_summaries(project, bug)
    if existing is not None:
        print("\n" + "="*60)
        print(f"[SKIP] {project}-{bug} already has MAJOR+PIT summaries; skipping execution.")
        print("="*60)
        return bug, existing

    # 2) Otherwise, run as before
    env11 = _mk_env(JAVA11, jvm_xmx=jvm_xmx)
    env8  = _mk_env(JAVA8,  jvm_xmx=jvm_xmx)
    print("\n" + "="*60)
    print(f"Processing {project}-{bug}")
    print("="*60)

    fixed_dir = checkout_rev(project, bug, 'f', env11)
    m_total, m_killed, m_surv = run_major(project, bug, fixed_dir, env11, env8)

    fixed_dir_pit = checkout_rev(project, bug, 'f', env11)
    p_total, p_killed, p_surv = run_pit(project, bug, fixed_dir_pit, env11, threads, forks, jvm_xmx)

    rows = [
        ["MAJOR", project, bug, m_total, m_killed, m_surv],
        ["PIT",   project, bug, p_total, p_killed, p_surv]
    ]
    return bug, rows

def main():
    parser = argparse.ArgumentParser(description="Run MAJOR and PIT for a Defects4J project (parallel).")
    parser.add_argument("project")
    parser.add_argument("bug_id", nargs="?")
    parser.add_argument("--list-bugs", action="store_true")
    parser.add_argument("--bugs")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--forks", type=int, default=0)
    parser.add_argument("--jvm-xmx", default="8g")
    args = parser.parse_args()

    global ENV11, ENV8
    ENV11 = _mk_env(JAVA11, jvm_xmx=args.jvm_xmx)
    ENV8  = _mk_env(JAVA8,  jvm_xmx=args.jvm_xmx)
    project = args.project

    if args.list_bugs:
        for b in list_bugs(project):
            print(b)
        return

    if args.bugs:
        bugs = [b.strip() for b in args.bugs.split(",") if b.strip()]
    elif args.bug_id:
        bugs = [args.bug_id.strip()]
    else:
        bugs = list_bugs(project)

    print(f"=== {project}: {len(bugs)} bug(s) ===")
    cpu = max(1, os.cpu_count() or 1)
    threads = args.threads if args.threads > 0 else cpu
    forks   = args.forks   if args.forks   > 0 else max(1, cpu // 2)

    all_rows: List[List] = []
    if args.jobs <= 1 or len(bugs) == 1:
        for b in bugs:
            _, rows = process_one_bug(project, b, args.jvm_xmx, threads, forks)
            all_rows.extend(rows)
    else:
        with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as ex:
            futs = {ex.submit(process_one_bug, project, b, args.jvm_xmx, threads, forks): b for b in bugs}
            for fut in as_completed(futs):
                b = futs[fut]
                try:
                    _, rows = fut.result()
                    all_rows.extend(rows)
                except Exception as e:
                    print(f"[ERROR] {project}-{b}: {e}", file=sys.stderr)

    outcsv = RESULTS / f"{project}_summary.csv"
    with outcsv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["engine","project","bug","mutants_total","killed","survived"])
        w.writerows(all_rows)
    print(f"\n[SAVED] Combined results at {outcsv}")
    print("All bugs done.")

if __name__ == "__main__":
    main()
