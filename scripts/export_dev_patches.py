#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export developer patches (buggy vs fixed diffs) for Defects4J projects.

Usage:
  # list detected projects under $D4J_HOME/framework/projects
  python3 export_dev_patches_all.py --list

  # export diffs for specific project(s)
  python3 export_dev_patches_all.py JxPath
  python3 export_dev_patches_all.py Lang Mockito --force
"""

import os, re, sys, subprocess, argparse
from pathlib import Path

# === Configuration ===
D4J_HOME  = os.environ.get("D4J_HOME", "cd to directory/defects4j")
DEFECTS4J = f"{D4J_HOME}/framework/bin/defects4j"
EXPROOT   = Path(os.environ.get("EXPERIMENT_ROOT", "/cd to directory/my_mutation_experiments"))

WORK      = EXPROOT / "d4j_work_diff"
OUT_ROOT  = EXPROOT / "results" / "dev_patches"

# Projects you might want to skip (keep empty unless needed)
SKIP_PROJECTS = set()

# Exclude noisy/binary paths from diffs
EXCLUDES = [
    ".git", ".svn", ".hg", ".idea", ".settings", ".classpath", ".project",
    "target", "build", "out", "bin",
    "*.class", "*.jar", "*.war", "*.ear", "*.zip", "*.tar", "*.gz"
]

# === Helpers ===
def env_java11() -> dict:
    """Return an environment with Java 11 first on PATH and stable English locale."""
    env = os.environ.copy()

    # Prefer explicit JAVA11_HOME; fall back to JAVA_HOME if needed
    java11 = env.get("JAVA11_HOME") or env.get("JAVA_HOME")
    if java11:
        env["JAVA_HOME"] = java11
        env["PATH"] = f"{java11}/bin:" + env.get("PATH", "")

    # Force English output so regex / tools behave predictably
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    # Keep user's _JAVA_OPTIONS, just enforce en_US
    env["_JAVA_OPTIONS"] = (env.get("_JAVA_OPTIONS", "") + " -Duser.language=en -Duser.region=US").strip()

    # If using conda + cpanm, make sure perl libs are visible to defects4j
    if "CONDA_PREFIX" in env:
        perl_base = env["CONDA_PREFIX"]
        env["PERL5LIB"] = (
            f"{perl_base}/lib/perl5:"
            f"{perl_base}/lib/perl5/x86_64-linux-thread-multi:"
            + env.get("PERL5LIB", "")
        )
    return env


def run(cmd, cwd=None, env=None, quiet=False, check=True, text=True) -> subprocess.CompletedProcess:
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
    """Ensure java is present, is JDK 11, and defects4j is runnable (use 'pids' as probe)."""
    env = env_java11()

    # java present?
    cp_which = run(["which", "java"], env=env, check=False)
    if cp_which.returncode != 0 or not cp_which.stdout.strip():
        raise RuntimeError("No 'java' on PATH (after forcing JAVA_HOME/bin).")

    # java is 11.x?
    cp_ver = run(["java", "-version"], env=env, check=False, text=False)
    s = ((cp_ver.stdout or b"") + (cp_ver.stderr or b"")).decode("utf-8", errors="replace")
    if " version \"11" not in s and " 11." not in s:
        raise RuntimeError(f"'java -version' is not Java 11:\n{s}")

    # defects4j probe (avoid 'version' subcommand; not present on all builds)
    probe = run([DEFECTS4J, "pids"], env=env, check=False)
    if probe.returncode != 0 or not (probe.stdout or "").strip():
        raise RuntimeError(
            f"'defects4j pids' failed:\nSTDOUT:\n{probe.stdout}\nSTDERR:\n{probe.stderr}"
        )


def list_detected_projects():
    root = Path(D4J_HOME) / "framework" / "projects"
    if not root.exists():
        return []
    return sorted([d.name for d in root.iterdir() if d.is_dir() and (d / "active-bugs.csv").exists()])


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
        if cp.returncode in (0, 1):  # 0 = no differences, 1 = differences found
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
    ap.add_argument("projects", nargs="*", help="Projects to export (e.g., JxPath Lang). Required unless --list.")
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
