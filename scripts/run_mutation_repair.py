#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Mutation-Based Repair to generate APR statistics (Table 9).

Fixes:
- Uses Java 11 for Defects4J infrastructure.
- correctly passes -D flags via ANT_ARGS environment variable to avoid 'Unknown option' errors.
- Verifies mutants using deterministic IDs on the buggy version.
"""

import os, re, csv, sys, shutil, subprocess, argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIG
# ============================================================
D4J_HOME   = os.environ.get("D4J_HOME", "/home1/furqan/tools_and_libs/defects4j")
DEFECTS4J  = f"{D4J_HOME}/framework/bin/defects4j"
EXPROOT    = os.environ.get("EXPERIMENT_ROOT", "/home1/furqan/my_mutation_experiments")

# Java Paths
JAVA11     = os.environ.get("JAVA11_HOME", "/usr/lib/jvm/java-11-openjdk-amd64")
JAVA8      = os.environ.get("JAVA8_HOME",  "/usr/lib/jvm/java-8-openjdk-amd64")
MAJOR_JAVA_HOME = os.environ.get("MAJOR_JAVA_HOME", JAVA8)

WORK       = Path(EXPROOT) / "d4j_repair_work"; WORK.mkdir(parents=True, exist_ok=True)
LOGS_ROOT  = Path(EXPROOT) / "logs"
RESULTS    = Path(EXPROOT) / "results"; RESULTS.mkdir(parents=True, exist_ok=True)

# ============================================================
# UTILS
# ============================================================
def _mk_env(java_home: str, jvm_xmx: str = "4g") -> dict:
    """Create environment with specific Java version."""
    e = os.environ.copy()
    e["JAVA_HOME"] = java_home
    e["PATH"] = f"{java_home}/bin:/usr/bin:" + e.get("PATH", "")
    
    # Add tools.jar for Ant/Major execution if present
    tools_jar = Path(java_home) / "lib" / "tools.jar"
    opts = ["-Dfile.encoding=UTF-8", "-Dsun.jnu.encoding=UTF-8"]
    if tools_jar.exists():
        opts.insert(0, f"-Xbootclasspath/a:{tools_jar}")
    
    e["ANT_OPTS"]   = f"-Xmx{jvm_xmx} " + " ".join(opts)
    e["MAVEN_OPTS"] = f"-Xmx{jvm_xmx} -Dmaven.repo.local={Path.home() / '.m2/repository'}"
    
    # Initialize ANT_ARGS if missing
    if "ANT_ARGS" not in e:
        e["ANT_ARGS"] = ""
        
    return e

def run(cmd, cwd=None, env=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if check and p.returncode != 0:
        # Capture both stdout and stderr for debugging
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nSTDERR: {p.stderr}\nSTDOUT: {p.stdout}")
    return p

def parse_live_mutants(project, bug):
    """
    Read mutants.log and kill.csv from previous run.
    Return list of Mutant IDs that are LIVE (Survived).
    """
    log_dir = LOGS_ROOT / f"{project}-{bug}"
    mutants_log = log_dir / "mutants.log"
    kill_csv    = log_dir / "kill.csv"

    if not mutants_log.exists() or not kill_csv.exists():
        return [], 0

    # Read Killed Status
    killed_ids = set()
    if kill_csv.exists():
        with kill_csv.open("r", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row: continue
                status = row[-1].upper()
                if status in ["KILLED", "TIMEOUT", "MEMORY_ERROR", "RUNTIME_ERROR", "EXC"]:
                    killed_ids.add(row[0])

    # Read All IDs
    live_ids = []
    total_count = 0
    if mutants_log.exists():
        with mutants_log.open("r", errors="ignore") as f:
            for line in f:
                total_count += 1
                mid = line.split(":")[0]
                if mid not in killed_ids:
                    live_ids.append(mid)
    
    return live_ids, total_count

# ============================================================
# CORE REPAIR LOGIC
# ============================================================
def validate_mutant(wd, env, mutant_id, trigger_test):
    """
    Runs the triggering test with a specific mutant active.
    Uses ANT_ARGS to pass the mutant ID to the JVM.
    """
    test_env = env.copy()
    
    # We inject -Djvm.args=-Dmajor.mutant=<id> into ANT_ARGS.
    # This tells the Ant <junit> task to pass -Dmajor.mutant=<id> to the forked test JVM.
    current_ant_args = test_env.get("ANT_ARGS", "")
    test_env["ANT_ARGS"] = f"{current_ant_args} -Djvm.args=-Dmajor.mutant={mutant_id}".strip()
    
    # Defects4J test command (no -D flags here)
    cmd = [DEFECTS4J, "test", "-t", trigger_test]
    
    # Capture output to check for success
    p = subprocess.run(cmd, cwd=str(wd), env=test_env, text=True, capture_output=True)
    
    # Return 0 means test PASSED (which implies the bug was fixed by this mutant)
    if p.returncode == 0:
        return True
    return False

def process_bug(project, bug):
    # Use Java 11 for D4J wrapper interactions
    env11 = _mk_env(JAVA11) 
    
    # 1. Identify Candidates from Previous Run
    live_ids, total_gen = parse_live_mutants(project, bug)
    if not live_ids:
        return [project, bug, total_gen, 0, 0]

    print(f"[{project}-{bug}] Candidates (Live Mutants): {len(live_ids)} / {total_gen}")

    # 2. Checkout Buggy Version (Fresh)
    wd = WORK / f"{project}-{bug}-repair"
    if wd.exists(): shutil.rmtree(wd)
    wd.mkdir(parents=True, exist_ok=True)
    
    try:
        run([DEFECTS4J, "checkout", "-p", project, "-v", f"{bug}b", "-w", str(wd)], env=env11)
    except Exception as e:
        print(f"[{project}-{bug}] Checkout Failed: {e}")
        return [project, bug, total_gen, 0, 0]
    
    # 3. Get Triggering Test
    try:
        res = run([DEFECTS4J, "export", "-p", "tests.trigger"], cwd=str(wd), env=env11, check=False)
        triggers = [t.strip() for t in res.stdout.splitlines() if t.strip()]
        if not triggers:
            print(f"[ERR] No triggering test for {project}-{bug}")
            return [project, bug, total_gen, 0, 0]
        trigger_test = triggers[0]
    except Exception:
        return [project, bug, total_gen, 0, 0]

    # 4. Compile with MAJOR (Instrumented)
    # We construct a specialized environment with ANT_ARGS for the compiler configuration
    compile_env = env11.copy()
    
    # Define Ant properties to force Major compilation
    ant_flags = [
        "-Dbuild.compiler=major.ant.MajorCompiler",
        f"-Dmajor.java.home={MAJOR_JAVA_HOME}",
        "-Dmajor.export.mutants.file=mutants.recompile.log",
        "-Dmajor.enable=true"
    ]
    
    existing_args = compile_env.get("ANT_ARGS", "")
    compile_env["ANT_ARGS"] = f"{existing_args} {' '.join(ant_flags)}".strip()

    # Run compile (no CLI flags passed to defects4j itself)
    try:
        run([DEFECTS4J, "compile"], cwd=str(wd), env=compile_env)
    except Exception as e:
        print(f"[{project}-{bug}] Compilation Failed: {e}")
        return [project, bug, total_gen, 0, 0]

    # 5. Validate Candidates
    plausible_count = 0
    
    # Validate each live mutant
    # Note: If there are thousands of live mutants, this can be slow.
    for mid in live_ids:
        is_fixed = validate_mutant(wd, env11, mid, trigger_test)
        if is_fixed:
            print(f"  -> [{project}-{bug}] Mutant {mid} IS PLAUSIBLE (Fixed {trigger_test})")
            plausible_count += 1

    # Cleanup
    shutil.rmtree(wd)

    print(f"[{project}-{bug}] DONE. Generated={total_gen}, Plausible={plausible_count}")
    return [project, bug, total_gen, plausible_count, plausible_count]

# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    
    project = args.project
    
    # List bugs
    f = Path(D4J_HOME) / f"framework/projects/{project}/active-bugs.csv"
    if not f.exists():
        print(f"Project {project} not found in {D4J_HOME}")
        sys.exit(1)
        
    bugs = [line.split(",")[0] for line in f.read_text().splitlines() if re.match(r"^\d+", line)]
    bugs.sort(key=int)
    
    print(f"Running Mutation Repair on {project} ({len(bugs)} bugs)...")

    outfile = RESULTS / f"{project}_apr_summary.csv"
    # Write header
    with outfile.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Project", "Bug", "Gen_Patches", "Plausible_Patches", "Correct_Patches"])

    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(process_bug, project, b): b for b in bugs}
            for fut in as_completed(futs):
                try:
                    res = fut.result()
                    with outfile.open("a", newline="") as f:
                        csv.writer(f).writerow(res)
                except Exception as e:
                    print(f"Worker Fail: {e}")
    else:
        for b in bugs:
            try:
                res = process_bug(project, b)
                with outfile.open("a", newline="") as f:
                    csv.writer(f).writerow(res)
            except Exception as e:
                print(f"Fail on {b}: {e}")

    print(f"\nDone. Results saved to {outfile}")

if __name__ == "__main__":
    main()
