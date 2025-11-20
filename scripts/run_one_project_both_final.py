#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run MAJOR and PIT on the BUGGY ('b') revision of Defects4J projects.
OPTIMIZED FOR BATCH EXECUTION:
- Skips bugs that are already analyzed.
- Saves results incrementally (so you don't lose data if it crashes).
"""

import os, re, csv, sys, shutil, subprocess, argparse
from pathlib import Path
from typing import List, Tuple, Set, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIG
# ============================================================
D4J_HOME   = os.environ.get("D4J_HOME", "/home1/furqan/tools_and_libs/defects4j")
DEFECTS4J  = f"{D4J_HOME}/framework/bin/defects4j"
EXPROOT    = os.environ.get("EXPERIMENT_ROOT", "/home1/furqan/my_mutation_experiments")

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
    opts = ["-Dfile.encoding=UTF-8", "-Dsun.jnu.encoding=UTF-8"]
    if tools_jar.exists():
        opts.insert(0, f"-Xbootclasspath/a:{tools_jar}")
    
    e["ANT_OPTS"]   = f"-Xmx{jvm_xmx} " + " ".join(opts)
    e["MAVEN_OPTS"] = f"-Xmx{jvm_xmx} -Dmaven.repo.local={Path.home() / '.m2/repository'}"
    e["ANT_ARGS"] = "-Dhaltonfailure=false"
    return e

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def run(cmd: List[str], cwd: Optional[str] = None, env=None, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if p.stdout: pass # print(p.stdout, end="") # Silence stdout for batch runs to reduce noise
    if p.stderr: sys.stderr.write(p.stderr)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}")
    return p

def list_bugs(project: str) -> List[str]:
    f = Path(D4J_HOME) / f"framework/projects/{project}/active-bugs.csv"
    if not f.exists(): raise FileNotFoundError(f"{f} not found")
    ids = [line.split(",")[0].strip() for line in f.read_text().splitlines() if re.match(r"^\d+", line)]
    return sorted(set(ids), key=lambda x: int(x))

def checkout_rev(project: str, bug: str, rev: str, suffix: str, env11) -> Path:
    tgt = WORK / f"{project}-{bug}-{rev}-{suffix}"
    if tgt.exists():
        shutil.rmtree(tgt)
    tgt.mkdir(parents=True, exist_ok=True)
    run([DEFECTS4J, "checkout", "-p", project, "-v", f"{bug}{rev}", "-w", str(tgt)], env=env11)
    return tgt

def export_prop(prop: str, wd: Path, env11) -> str:
    p = run([DEFECTS4J, "export", "-p", prop], cwd=str(wd), env=env11, check=False)
    return (p.stdout or "").strip()

def remove_triggering_tests(wd: Path, env11):
    triggering_raw = export_prop("tests.trigger", wd, env11)
    triggers = set()
    for line in triggering_raw.splitlines():
        line = line.strip()
        if not line: continue
        triggers.add(line.split("::")[0])
    
    if not triggers: return

    # print(f"    Removing triggering tests: {triggers}")
    for t_class in triggers:
        simple_name = t_class.split(".")[-1]
        found_files = list(wd.rglob(f"{simple_name}.java"))
        for f in found_files:
            f.unlink()

def _unique_pkg_prefixes(names: List[str]) -> Set[str]:
    pkgs = set()
    for c in names:
        c = c.replace("/", ".").replace(".java", "")
        if "." in c: pkgs.add(".".join(c.split(".")[:-1]))
    result = set()
    for p in sorted(pkgs):
        if not any(p.startswith(q + ".") for q in result): result.add(p)
    return {p + ".*" for p in result} if result else {"*"}

def check_already_done(project: str, bug: str) -> bool:
    """Check if we already have results for this bug."""
    out = LOGS_ROOT / f"{project}-{bug}"
    major_csv = out / "major_summary.csv"
    pit_csv   = out / "pit_summary.csv"
    return major_csv.exists() and pit_csv.exists()

# ============================================================
# MAJOR ENGINE
# ============================================================
def run_major(project: str, bug: str, bug_dir: Path, env11, env8) -> Tuple[int,int,int]:
    out = LOGS_ROOT / f"{project}-{bug}"
    out.mkdir(parents=True, exist_ok=True)
    mutants_log = out / "mutants.log"
    kill_csv    = out / "kill.csv"

    remove_triggering_tests(bug_dir, env11)
    run([DEFECTS4J, "compile"], cwd=str(bug_dir), env=env11, check=True)

    mut_cmd = [
        DEFECTS4J, "mutation",
        "-w", str(bug_dir),
        "-r", "major",
        f"-Dmajor.java.home={MAJOR_JAVA_HOME}",
        f"-Dmajor.export.mutants.file={mutants_log}",
        f"-Dmajor.kill.log={kill_csv}",
        "-Dmajor.log.level=FINE"
    ]

    res = run(mut_cmd, cwd=str(bug_dir), env=env11, check=False)

    gen = kill = None
    for line in (res.stdout or "").splitlines():
        m = re.search(r"Mutants generated:\s*(\d+)", line)
        if m: gen = int(m.group(1))
        m = re.search(r"Mutants killed:\s*(\d+)", line)
        if m: kill = int(m.group(1))

    if not mutants_log.exists() and (bug_dir/"mutants.log").exists():
        shutil.copy2(bug_dir/"mutants.log", mutants_log)
    if not kill_csv.exists() and (bug_dir/"kill.csv").exists():
        shutil.copy2(bug_dir/"kill.csv", kill_csv)

    total = gen if gen is not None else 0
    killed = kill if kill is not None else 0

    if kill_csv.exists() and total == 0:
        try:
            with kill_csv.open(newline="") as f:
                rows = list(csv.reader(f))
                if len(rows) > 1:
                    total = len(rows) - 1
                    killed = sum(1 for r in rows[1:] if r[-1].lower() in ['killed', 'timeout', 'memoryerror'])
        except: pass

    survived = max(0, total - killed)
    
    with (out / "major_summary.csv").open("w", newline="") as f:
        csv.writer(f).writerow(["engine","project","bug","mutants_total","killed","survived"])
        csv.writer(f).writerow(["MAJOR", project, bug, total, killed, survived])

    return total, killed, survived

# ============================================================
# PIT ENGINE
# ============================================================
def run_pit(project: str, bug: str, bug_dir: Path, env11,
            threads: int, fork_count: int, jvm_xmx: str) -> Tuple[int,int,int]:
    out = LOGS_ROOT / f"{project}-{bug}"
    out.mkdir(parents=True, exist_ok=True)

    remove_triggering_tests(bug_dir, env11)
    
    # Env fix for 'defects4j compile -D...' issue
    compile_env = env11.copy()
    existing_args = compile_env.get("ANT_ARGS", "")
    compile_env["ANT_ARGS"] = f"{existing_args} -Dbuild.compiler=modern".strip()
    run([DEFECTS4J, "compile"], cwd=str(bug_dir), env=compile_env, check=True)

    pit_params = [
        DEFECTS4J, "mutation",
        "-w", str(bug_dir),
        "-r", "pit",
        f"-Dpit.report.dir={out}",
        f"-Dpit.failWhenNoMutations=false", 
        f"-Dpit.skipFailingTests=true",
        f"-Dpit.timeoutConstant=500",
        f"-Dpit.outputFormats=CSV",
        f"-Dpit.threads={threads}",
        f"-Dpit.forkCount={fork_count}",
        f"-Dpit.jvmArgs=-Xmx{jvm_xmx}"
    ]

    classes_rel = [c.strip() for c in export_prop("classes.relevant", bug_dir, env11).splitlines() if c.strip()]
    if classes_rel:
        pkgs = ",".join(sorted(_unique_pkg_prefixes(classes_rel)))
        pit_params.append(f"-Dpit.targetClasses={pkgs}")
    
    res = run(pit_params, cwd=str(bug_dir), env=env11, check=False)
    
    candidates = [out / "mutations.csv", out / "pitest-mutations.csv"]
    candidates += list(bug_dir.glob("**/pit-reports/**/mutations.csv"))
    found = next((p for p in candidates if p.exists()), None)

    total = killed = 0
    if found:
        shutil.copy2(found, out / "pit_mutations.csv")
        with found.open(newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                total += 1
                status = (row.get("Status") or row.get("status") or "").lower()
                if status in ("killed", "timeout", "memoryerror"):
                    killed += 1
    else:
        for line in (res.stdout or "").splitlines():
            if "Mutants generated" in line:
                 m = re.search(r"(\d+)", line)
                 if m: total = int(m.group(1))
            if "Mutants killed" in line:
                 m = re.search(r"(\d+)", line)
                 if m: killed = int(m.group(1))

    survived = max(0, total - killed)
    with (out / "pit_summary.csv").open("w", newline="") as f:
        csv.writer(f).writerow(["engine","project","bug","mutants_total","killed","survived"])
        csv.writer(f).writerow(["PIT", project, bug, total, killed, survived])
        
    return total, killed, survived

# ============================================================
# MAIN LOGIC
# ============================================================
def process_one_bug(project: str, bug: str, jvm_xmx: str, threads: int, forks: int) -> Tuple[str, List[List]]:
    # Skip if done
    if check_already_done(project, bug):
        print(f"[SKIP] {project}-{bug} already completed.")
        return bug, []

    env11 = _mk_env(JAVA11, jvm_xmx=jvm_xmx)
    env8  = _mk_env(JAVA8,  jvm_xmx=jvm_xmx)
    
    print(f"\n>>> PROCESSING {project}-{bug} <<<")

    # 1. MAJOR
    major_dir = checkout_rev(project, bug, 'b', "major", env11)
    try:
        m_total, m_killed, m_surv = run_major(project, bug, major_dir, env11, env8)
    except Exception as e:
        print(f"[{project}-{bug}] MAJOR FAILED: {e}")
        m_total, m_killed, m_surv = 0, 0, 0
    finally:
        shutil.rmtree(major_dir, ignore_errors=True)

    # 2. PIT
    pit_dir = checkout_rev(project, bug, 'b', "pit", env11)
    try:
        p_total, p_killed, p_surv = run_pit(project, bug, pit_dir, env11, threads, forks, jvm_xmx)
    except Exception as e:
        print(f"[{project}-{bug}] PIT FAILED: {e}")
        p_total, p_killed, p_surv = 0, 0, 0
    finally:
        shutil.rmtree(pit_dir, ignore_errors=True)

    rows = [
        ["MAJOR", project, bug, m_total, m_killed, m_surv],
        ["PIT",   project, bug, p_total, p_killed, p_surv]
    ]
    print(f"[{project}-{bug}] DONE. MAJOR: {m_total}, PIT: {p_total}")
    return bug, rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("bug_id", nargs="?")
    parser.add_argument("--bugs")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--jvm-xmx", default="8g")
    args = parser.parse_args()

    project = args.project
    if args.bugs:
        bugs = [b.strip() for b in args.bugs.split(",") if b.strip()]
    elif args.bug_id:
        bugs = [args.bug_id]
    else:
        bugs = list_bugs(project)

    print(f"=== {project}: {len(bugs)} bug(s) ===")
    
    # Prepare Output CSV with header
    outcsv = RESULTS / f"{project}_buggy_summary.csv"
    if not outcsv.exists():
        with outcsv.open("w", newline="") as f:
            csv.writer(f).writerow(["engine","project","bug","mutants_total","killed","survived"])

    def save_rows(rows):
        if not rows: return
        with outcsv.open("a", newline="") as f:
            csv.writer(f).writerows(rows)

    # Running
    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(process_one_bug, project, b, args.jvm_xmx, 1, 1): b for b in bugs}
            for fut in as_completed(futs):
                try:
                    _, rows = fut.result()
                    save_rows(rows) # Save immediately
                except Exception as e:
                    print(f"CRITICAL FAIL: {e}")
    else:
        for b in bugs:
            try:
                _, rows = process_one_bug(project, b, args.jvm_xmx, 1, 1)
                save_rows(rows) # Save immediately
            except Exception as e:
                print(f"CRITICAL FAIL on {b}: {e}")

    print(f"All Done. Results accumulated in {outcsv}")

if __name__ == "__main__":
    main()
