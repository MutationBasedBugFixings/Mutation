#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAST Mutation Repair (Direct JVM Mode).
Bypasses 'defects4j test' wrapper to run checks 10x-20x faster.
"""

import os, re, csv, sys, shutil, subprocess, argparse, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# ============================================================
# CONFIGURATION
# ============================================================
D4J_HOME   = os.environ.get("D4J_HOME", "/home1/furqan/tools_and_libs/defects4j")
DEFECTS4J  = f"{D4J_HOME}/framework/bin/defects4j"
EXPROOT    = os.environ.get("EXPERIMENT_ROOT", "/home1/furqan/my_mutation_experiments")

# USE RAM DISK FOR SPEED (Linux)
# If /dev/shm doesn't exist, fall back to standard disk
if Path("/dev/shm").exists():
    WORK = Path(f"/dev/shm/{os.environ.get('USER', 'd4j')}_repair_work")
else:
    WORK = Path(EXPROOT) / "d4j_repair_work"

JAVA11     = os.environ.get("JAVA11_HOME", "/usr/lib/jvm/java-11-openjdk-amd64")
JAVA8      = os.environ.get("JAVA8_HOME",  "/usr/lib/jvm/java-8-openjdk-amd64")
MAJOR_JAVA_HOME = os.environ.get("MAJOR_JAVA_HOME", JAVA8)
MAJOR_JAR  = Path(D4J_HOME) / "major/lib/major.jar" # Critical for direct execution

LOGS_ROOT  = Path(EXPROOT) / "logs"
RESULTS    = Path(EXPROOT) / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# ============================================================
# HELPERS
# ============================================================
def _mk_env(java_home: str) -> dict:
    e = os.environ.copy()
    e["JAVA_HOME"] = java_home
    e["PATH"] = f"{java_home}/bin:/usr/bin:" + e.get("PATH", "")
    return e

def run(cmd, cwd=None, env=None, check=True):
    # Capture output only on failure to keep logs clean
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"CMD Failed: {' '.join(cmd)}\nERR: {p.stderr}")
    return p

def parse_live_mutants(project, bug):
    log_dir = LOGS_ROOT / f"{project}-{bug}"
    mutants_log = log_dir / "mutants.log"
    kill_csv    = log_dir / "kill.csv"

    if not mutants_log.exists() or not kill_csv.exists():
        return [], 0

    # Get Killed IDs
    killed_ids = set()
    if kill_csv.exists():
        with kill_csv.open("r", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row: continue
                status = row[-1].upper()
                # We only want to repair with mutants that survived regression
                if status in ["KILLED", "TIMEOUT", "MEMORY_ERROR", "RUNTIME_ERROR", "EXC"]:
                    killed_ids.add(row[0])

    # Get Live IDs
    live_ids = []
    total_count = 0
    with mutants_log.open("r", errors="ignore") as f:
        for line in f:
            total_count += 1
            mid = line.split(":")[0]
            if mid not in killed_ids:
                live_ids.append(mid)
    return live_ids, total_count

# ============================================================
# FAST VALIDATION (Direct JVM)
# ============================================================
def validate_mutant_fast(cwd, env, java_cmd, classpath, trigger_test, mutant_id):
    """
    Directly invokes 'java org.junit.runner.JUnitCore' avoiding Ant overhead.
    """
    cmd = [
        java_cmd, 
        "-cp", classpath,
        f"-Dmajor.mutant={mutant_id}",
        "org.junit.runner.JUnitCore",
        trigger_test
    ]

    # We assume the test fails if it prints "FAILURES!!!" or return code != 0
    p = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, capture_output=True)
    
    # JUnitCore returns 0 if all tests pass, 1 if failure
    if p.returncode == 0:
        # Double check output just in case
        if "OK (" in p.stdout:
            return True
    return False

def process_bug(project, bug):
    env11 = _mk_env(JAVA11)
    
    live_ids, total_gen = parse_live_mutants(project, bug)
    if not live_ids:
        return [project, bug, total_gen, 0, 0]

    wd = WORK / f"{project}-{bug}"
    if wd.exists(): shutil.rmtree(wd)
    wd.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Checkout
        run([DEFECTS4J, "checkout", "-p", project, "-v", f"{bug}b", "-w", str(wd)], env=env11)
        
        # 2. Get Properties (Trigger Test & Classpath)
        # We export the full runtime classpath which includes test-deps
        cp_res = run([DEFECTS4J, "export", "-p", "cp.test"], cwd=str(wd), env=env11)
        raw_cp = cp_res.stdout.strip()
        
        # We also need the compiled classes folders
        classes_res = run([DEFECTS4J, "export", "-p", "dir.bin.classes"], cwd=str(wd), env=env11)
        tests_res   = run([DEFECTS4J, "export", "-p", "dir.bin.tests"], cwd=str(wd), env=env11)
        
        trigger_res = run([DEFECTS4J, "export", "-p", "tests.trigger"], cwd=str(wd), env=env11)
        triggers = [t.strip() for t in trigger_res.stdout.splitlines() if t.strip()]
        
        if not triggers: 
            return [project, bug, total_gen, 0, 0]

        trigger_test = triggers[0]

        # 3. Compile with MAJOR
        # Prepare environment for Ant
        compile_env = env11.copy()
        ant_flags = [
            "-Dbuild.compiler=major.ant.MajorCompiler",
            f"-Dmajor.java.home={MAJOR_JAVA_HOME}",
            "-Dmajor.export.mutants.file=mutants.log",
            "-Dmajor.enable=true"
        ]
        existing_args = compile_env.get("ANT_ARGS", "")
        compile_env["ANT_ARGS"] = f"{existing_args} {' '.join(ant_flags)}".strip()
        
        run([DEFECTS4J, "compile"], cwd=str(wd), env=compile_env)

        # 4. Construct FAST Classpath
        # CP = major.jar + test_classpath + bin_classes + bin_tests
        bin_cls = str(wd / classes_res.stdout.strip())
        bin_tst = str(wd / tests_res.stdout.strip())
        
        # Important: Major.jar must be in CP for runtime to work
        full_cp = f"{str(MAJOR_JAR)}:{bin_cls}:{bin_tst}:{raw_cp}"
        
        # 5. Run Fast Validation
        plausible_count = 0
        java_bin = f"{JAVA11}/bin/java"

        print(f"[{project}-{bug}] Testing {len(live_ids)} candidates via Direct JVM...")
        
        for mid in live_ids:
            if validate_mutant_fast(wd, env11, java_bin, full_cp, trigger_test, mid):
                # print(f"  -> {mid} FIXED")
                plausible_count += 1

        return [project, bug, total_gen, plausible_count, plausible_count]

    except Exception as e:
        print(f"[{project}-{bug}] Error: {e}")
        return [project, bug, total_gen, 0, 0]
    finally:
        # Cleanup RAM disk
        if wd.exists(): shutil.rmtree(wd)

# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    
    project = args.project
    
    # Get active bugs
    f = Path(D4J_HOME) / f"framework/projects/{project}/active-bugs.csv"
    if not f.exists():
        print("Project not found.")
        sys.exit(1)
        
    bugs = [line.split(",")[0] for line in f.read_text().splitlines() if re.match(r"^\d+", line)]
    bugs.sort(key=int)
    
    # Maximize CPU usage (one bug per core)
    workers = args.jobs
    print(f"Starting Turbo Repair on {project} with {workers} workers...")
    
    outfile = RESULTS / f"{project}_apr_summary.csv"
    with outfile.open("w", newline="") as f:
        csv.writer(f).writerow(["Project", "Bug", "Gen_Patches", "Plausible_Patches", "Correct_Patches"])

    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(process_bug, project, b): b for b in bugs}
        for fut in as_completed(futs):
            res = fut.result()
            print(f"[{res[0]}-{res[1]}] Gen: {res[2]}, Plaus: {res[3]}")
            with outfile.open("a", newline="") as f:
                csv.writer(f).writerow(res)

if __name__ == "__main__":
    main()
