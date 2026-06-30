# evaluate_llm_patches_defects4j.py

import csv
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/home1/directory to /scripts")

PATCH_DIR = ROOT / "patches_deepseek"
if not PATCH_DIR.exists():
    PATCH_DIR = ROOT / "patches_llm"

WORK_DIR = ROOT / "work_eval"
RESULT_DIR = ROOT / "results_eval"

WORK_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

TIMEOUT = 900

BUGS = [
    *[("Chart", i) for i in range(1, 11)],

    ("Closure", 1), ("Closure", 5), ("Closure", 10), ("Closure", 15), ("Closure", 20),
    ("Closure", 25), ("Closure", 30), ("Closure", 35), ("Closure", 40), ("Closure", 45),

    ("Lang", 1), ("Lang", 5), ("Lang", 10), ("Lang", 15), ("Lang", 20),
    ("Lang", 25), ("Lang", 30), ("Lang", 35), ("Lang", 40), ("Lang", 45),

    ("Math", 1), ("Math", 5), ("Math", 10), ("Math", 15), ("Math", 20),
    ("Math", 25), ("Math", 30), ("Math", 35), ("Math", 40), ("Math", 45),

    ("Time", 1), ("Time", 3), ("Time", 5), ("Time", 7),
    ("Time", 9), ("Time", 11), ("Time", 13), ("Time", 15),

    ("Mockito", 1), ("Mockito", 3), ("Mockito", 5), ("Mockito", 7),
    ("Mockito", 9), ("Mockito", 11), ("Mockito", 13), ("Mockito", 15),

    ("Cli", 1), ("Cli", 3), ("Cli", 5), ("Cli", 7), ("Cli", 9), ("Cli", 11),

    ("Codec", 1), ("Codec", 3), ("Codec", 5), ("Codec", 7), ("Codec", 9), ("Codec", 11),

    ("Collections", 25), ("Collections", 26), ("Collections", 27),
    ("Collections", 28), ("Collections", 29), ("Collections", 30),

    ("Compress", 1), ("Compress", 5), ("Compress", 10),
    ("Compress", 15), ("Compress", 20), ("Compress", 25),

    ("Csv", 1), ("Csv", 2), ("Csv", 3), ("Csv", 4),

    ("Gson", 1), ("Gson", 2), ("Gson", 3), ("Gson", 4),

    ("JacksonCore", 1), ("JacksonCore", 5), ("JacksonCore", 10),

    ("JacksonDatabind", 1), ("JacksonDatabind", 10), ("JacksonDatabind", 20),

    ("JacksonXml", 1), ("JacksonXml", 2), ("JacksonXml", 3),

    ("Jsoup", 1), ("Jsoup", 5), ("Jsoup", 10),
]


def run(cmd, cwd=None, timeout=TIMEOUT):
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -999, "", "TIMEOUT"


def checkout_bug(project, bug_id, run_id):
    repo = WORK_DIR / f"{project}_{bug_id}_run{run_id}"

    if repo.exists():
        shutil.rmtree(repo, ignore_errors=True)

    code, out, err = run(
        f"defects4j checkout -p {project} -v {bug_id}b -w {repo}",
        cwd=ROOT,
    )

    return repo, code, out, err


def get_trigger_tests(repo):
    code, out, err = run("defects4j export -p tests.trigger", cwd=repo)
    return [x.strip() for x in out.splitlines() if x.strip()]


def run_trigger_tests(repo, trigger_tests):
    if not trigger_tests:
        code, out, err = run("defects4j test", cwd=repo)
        return code == 0, out + err

    all_pass = True
    logs = []

    for test in trigger_tests:
        code, out, err = run(f"defects4j test -t {test}", cwd=repo)
        logs.append(f"\n===== {test} =====\n{out}\n{err}")

        if code != 0:
            all_pass = False

    return all_pass, "\n".join(logs)


def normalize_patch(patch_file, project, bug_id, run_id):
    normalized_patch = RESULT_DIR / f"{project}_{bug_id}_run{run_id}_normalized.patch"

    text = patch_file.read_text(encoding="utf-8", errors="ignore")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # remove markdown fences if LLM accidentally returned them
    text = text.replace("```diff", "")
    text = text.replace("```patch", "")
    text = text.replace("```", "")

    normalized_patch.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")
    return normalized_patch


def normalize_repo_line_endings(repo):
    run("find . -name '*.java' -type f -exec sed -i 's/\\r$//' {} \\;", cwd=repo)
    run("find . -name '*.xml' -type f -exec sed -i 's/\\r$//' {} \\;", cwd=repo)
    run("find . -name '*.properties' -type f -exec sed -i 's/\\r$//' {} \\;", cwd=repo)


def try_apply_patch(repo, normalized_patch, log_file):
    commands = [
        f"patch -p0 -l --fuzz=10 < {normalized_patch}",
        f"patch -p1 -l --fuzz=10 < {normalized_patch}",
        f"git apply --ignore-space-change --ignore-whitespace {normalized_patch}",
        f"git apply -p0 --ignore-space-change --ignore-whitespace {normalized_patch}",
    ]

    for idx, cmd in enumerate(commands, start=1):
        code, out, err = run(cmd, cwd=repo)

        with log_file.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(f"\nPATCH TRY {idx}:\nCOMMAND: {cmd}\n{out}\n{err}\n")

        if code == 0:
            return True, f"patch_applied_try_{idx}"

        # clean failed partial changes before next attempt
        run("git checkout -- .", cwd=repo)
        run("find . -name '*.rej' -delete", cwd=repo)
        run("find . -name '*.orig' -delete", cwd=repo)
        normalize_repo_line_endings(repo)

    return False, "patch_apply_failed"


def evaluate_patch(project, bug_id, run_id, patch_file):
    repo = None

    row = {
        "project": project,
        "bug_id": bug_id,
        "run_id": run_id,
        "patch_file": str(patch_file),
        "checkout_ok": False,
        "patch_apply_ok": False,
        "compile_ok": False,
        "trigger_tests_pass": False,
        "all_tests_pass": False,
        "status": "",
    }

    try:
        repo, checkout_code, checkout_out, checkout_err = checkout_bug(project, bug_id, run_id)

        row["checkout_ok"] = checkout_code == 0

        log_file = RESULT_DIR / f"{project}_{bug_id}_run{run_id}.log"
        log_file.write_text(
            f"CHECKOUT:\n{checkout_out}\n{checkout_err}\n",
            encoding="utf-8",
            errors="ignore",
        )

        if checkout_code != 0:
            row["status"] = "checkout_failed"
            return row

        trigger_tests = get_trigger_tests(repo)
        normalized_patch = normalize_patch(patch_file, project, bug_id, run_id)

        normalize_repo_line_endings(repo)

        applied, apply_status = try_apply_patch(repo, normalized_patch, log_file)

        if not applied:
            row["status"] = apply_status
            return row

        row["patch_apply_ok"] = True

        compile_code, compile_out, compile_err = run("defects4j compile", cwd=repo)

        with log_file.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(f"\nCOMPILE:\n{compile_out}\n{compile_err}\n")

        if compile_code != 0:
            row["status"] = "compile_failed"
            return row

        row["compile_ok"] = True

        trigger_pass, trigger_log = run_trigger_tests(repo, trigger_tests)

        with log_file.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(f"\nTRIGGER TESTS:\n{trigger_log}\n")

        row["trigger_tests_pass"] = trigger_pass

        all_code, all_out, all_err = run("defects4j test", cwd=repo, timeout=1200)

        with log_file.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(f"\nALL TESTS:\n{all_out}\n{all_err}\n")

        row["all_tests_pass"] = all_code == 0

        if row["all_tests_pass"]:
            row["status"] = "correct"
        elif row["trigger_tests_pass"]:
            row["status"] = "plausible"
        else:
            row["status"] = "failed"

        return row

    finally:
        if repo is not None and repo.exists():
            shutil.rmtree(repo, ignore_errors=True)


def write_results(rows):
    out_csv = RESULT_DIR / "llm_patch_evaluation_results.csv"

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "project",
                "bug_id",
                "run_id",
                "patch_file",
                "checkout_ok",
                "patch_apply_ok",
                "compile_ok",
                "trigger_tests_pass",
                "all_tests_pass",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return out_csv


def main():
    rows = []

    for project, bug_id in BUGS:
        for run_id in range(1, 6):
            patch_file = PATCH_DIR / f"{project}_{bug_id}_llm_{run_id}.patch"

            if not patch_file.exists():
                rows.append({
                    "project": project,
                    "bug_id": bug_id,
                    "run_id": run_id,
                    "patch_file": str(patch_file),
                    "checkout_ok": False,
                    "patch_apply_ok": False,
                    "compile_ok": False,
                    "trigger_tests_pass": False,
                    "all_tests_pass": False,
                    "status": "patch_file_missing",
                })
                write_results(rows)
                continue

            print(f"[EVAL] {project}-{bug_id} run {run_id}")
            row = evaluate_patch(project, bug_id, run_id, patch_file)
            rows.append(row)
            write_results(rows)

    print(f"\nDONE: {RESULT_DIR / 'llm_patch_evaluation_results.csv'}")


if __name__ == "__main__":
    main()
