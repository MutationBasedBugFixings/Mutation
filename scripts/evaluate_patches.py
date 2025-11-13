#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export developer patches (buggy vs fixed diffs) for Defects4J projects.

Usage:
  # list detected projects
  python3 export_dev_patches_all.py --list

  # export diffs for specific project(s) only (no auto-run)
  python3 export_dev_patches_all.py JxPath
  python3 export_dev_patches_all.py Lang Mockito --force
"""

import os, re, sys, subprocess, argparse
from pathlib import Path

# === Configuration ===
D4J_HOME  = os.environ.get("D4J_HOME", "/cd to directory/defects4j")
DEFECTS4J = f"{D4J_HOME}/framework/bin/defects4j"
EXPROOT   = Path(os.environ.get("EXPERIMENT_ROOT", "/cd to directory/my_mutation_experiments"))

WORK      = EXPROOT / "d4j_work_diff"
OUT_ROOT  = EXPROOT / "results" / "dev_patches"

# Disable problematic projects (you can remove Chart later if needed)
SKIP_PROJECTS = {"Chart"}

# Excludes to keep diffs clean / avoid binary noise
EXCLUDES = [
    ".git", ".svn", ".hg", ".idea", ".settings", ".classpath", ".project",
    "target", "build", "out", "bin",
    "*.class", "*.jar", "*.war", "*.ear", "*.zip", "*.tar", "*.gz"
]

# === Helpers ===
def env_java11():
    """Return a clean env with Java 11 on PATH + stable English locale."""
    env = os.environ.copy()

    # Prefer explicit JAVA11_HOME; else JAVA_HOME
    java11 = env.get("JAVA11_HOME") or env.get("JAVA_HOME")
    if java11:
        env["JAVA_HOME"] = java11
        env["PATH"] = f"{java11}/bin:" + env.get("PATH", "")

    # Force English version strings so D4J regex is happy
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    env["_JAVA_OPTIONS"] = (env.get("_JAVA_OPTIONS", "") + " -Duser.language=en -Duser.region=US").strip()

    # Perl libs if installed via conda/cpanm
    if "CONDA_PREFIX" in env:
        perl_base = env["CONDA_PREFIX"]
        env["PERL5LIB"] = (
            f"{perl_base}/lib/perl5:"
            f"{perl_base}/lib/perl5/x86_64-linux-thread-multi:" +
            env.get("PERL5LIB", "")
        )
    return env

def run(cmd, cwd=None, env=None, quiet=False, check=True, text=True):
    if not quiet:
        print(">>>", " ".join(cmd))
    cp = subprocess.run(
        cmd, cwd=cwd, env=env, text=text,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if check and cp.returncode != 0:
        raise RuntimeError(
            f"Failed: {' '.join(cmd)}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"
        )
    return cp

def preflight_java():
    """Ensure java is present, is JDK 11, and defects4j can respond."""
    env = env_java11()

    # java present?
    cp_which = run(["which", "java"], env=env, check=False)
    if cp_which.returncode != 0 or not cp_which.stdout.strip():
        raise RuntimeError("No 'java' on PATH (after forcing JAVA_HOME/bin).")

    # must be Java 11
    cp_ver = run(["java", "-version"], env=env, check=False, text=False)
    out = (cp_ver.stdout or b"") + (cp_ver.stderr or b"")
    s = out.decode("utf-8", errors="replace")
    if " version \"11" not in s and " 11." not in s:
        raise RuntimeError(f"'java -version' is not Java 11:\n{s}")

    # defects4j OK? Use 'pids' (supported & returns 0 on success)
    run([DEFECTS4J, "pids"], env=env)

def list_detected_projects():
    root = Path(D4J_HOME) / "framework" / "projects"
    if not root.exists():
        return []
    projs = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if (d / "active-bugs.csv").exists():
            projs.append(d.name)
    return projs

def list_bugs(project: str):
    path = Path(D4J_HOME) / "framework" / "projects" / project / "active-bugs.csv"
    if not path.exists():
        print(f"[WARN] Skipping {project}: no active-bugs.csv at {path}")
        return []
    ids = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if re.match(r"^\d+", line):
                ids.append(line.strip().split(",")[0])
    return sorted(set(ids), key=lambda x: int(x))

def checkout(project: str, bug: str, rev: str) -> Path:
    """rev in {'b','f'}"""
    env = env_java11()
    w = WORK / f"{project}-{bug}-{rev}"
    if not w.exists():
        run([DEFECTS4J, "checkout", "-p", project, "-v", f"{bug}{rev}", "-w", str(w)],
            env=env, quiet=False, check=True)
    return w

def export_project(project: str, force: bool = False):
    if project in SKIP_PROJECTS:
        print(f"[SKIP] {project} is disabled in SKIP_PROJECTS.")
        return

    WORK.mkdir(parents=True, exist_ok=True)
    out_dir = OUT_ROOT / project
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build diff command with excludes
    diff_prefix = ["diff", "-ruN"]
    for pat in EXCLUDES:
        diff_prefix += ["--exclude", pat]

    env = env_java11()
    bugs = list_bugs(project)
    if not bugs:
        return

    print(f"\n=== Exporting developer diffs for {project} ({len(bugs)} bugs) ===")
    for bug in bugs:
        bdir = checkout(project, bug, 'b')
        fdir = checkout(project, bug, 'f')
        diff_path = out_dir / f"{project}-{bug}.diff"

        if diff_path.exists() and not force:
            print(f"[SKIP] {diff_path.name} exists (use --force to overwrite)")
            continue

        # raw bytes to avoid Unicode issues
        cmd = diff_prefix + [str(bdir), str(fdir)]
        print(">>>", " ".join(cmd))
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        if cp.returncode in (0, 1):
            diff_path.write_bytes(cp.stdout)
            print(f"[OK] {diff_path} ({'empty' if cp.returncode == 0 else 'non-empty'})")
        else:
            print(f"[WARN] diff failed for {project}-{bug} (code {cp.returncode})")
            try:
                sys.stderr.write(cp.stderr.decode('utf-8', errors='replace'))
            except Exception:
                pass

    print(f"[DONE] All diffs saved in: {out_dir}\n")

# === CLI ===
def main():
    ap = argparse.ArgumentParser(
        description="Export developer diffs (fixed vs buggy) for Defects4J projects."
    )
    ap.add_argument("projects", nargs="*", help="Projects to export (e.g., JxPath Lang).")
    ap.add_argument("--force", action="store_true", help="Overwrite existing .diff files.")
    ap.add_argument("--list", action="store_true", help="List detected projects and exit.")
    args = ap.parse_args()

    # Preflight first so we fail fast if Java/Defects4J is off
    try:
        preflight_java()
    except Exception as e:
        print(f"[FATAL] Java preflight failed: {e}")
        sys.exit(2)

    if args.list:
        projs = list_detected_projects()
        if not projs:
            print(f"[WARN] No projects detected under {D4J_HOME}/framework/projects")
        else:
            print("[INFO] Detected projects:")
            for p in projs:
                flag = " (SKIPPED)" if p in SKIP_PROJECTS else ""
                print(f"  - {p}{flag}")
        return

    if not args.projects:
        print("Usage: python3 export_dev_patches_all.py <Project> [<Project> ...] [--force]")
        print("Try:   python3 export_dev_patches_all.py --list")
        sys.exit(1)

    # Normalize + apply skip
    projects = [p.strip() for p in args.projects if p.strip()]
    projects = [p for p in projects if p not in SKIP_PROJECTS]
    if not projects:
        print("[INFO] Nothing to run (all requested projects are skipped or empty).")
        return

    print(f"[INFO] Projects to export: {' '.join(projects)}")
    for proj in projects:
        try:
            export_project(proj, force=args.force)
        except Exception as e:
            print(f"[ERROR] Failed to export for {proj}: {e}")

if __name__ == "__main__":
    main()
