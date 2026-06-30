# generate_deepseek_patches_defects4j.py

import os
import re
import csv
import time
import shutil
import subprocess
from pathlib import Path
from openai import OpenAI


# =========================
# CONFIG
# =========================

ROOT = Path.cwd()
WORK_DIR = ROOT / "work_deepseek"
PATCH_DIR = ROOT / "patches_deepseek"
LOG_DIR = ROOT / "logs_deepseek"

WORK_DIR.mkdir(exist_ok=True)
PATCH_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

RUNS_PER_BUG = 5
TIMEOUT = 900

DEEPSEEK_MODEL = "DeepSeek-V4-Pro"

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)


BUGS = [
    # Chart - 10
    *[("Chart", i) for i in range(1, 11)],

    # Closure - 10
    ("Closure", 1), ("Closure", 5), ("Closure", 10), ("Closure", 15), ("Closure", 20),
    ("Closure", 25), ("Closure", 30), ("Closure", 35), ("Closure", 40), ("Closure", 45),

    # Lang - 10
    ("Lang", 1), ("Lang", 5), ("Lang", 10), ("Lang", 15), ("Lang", 20),
    ("Lang", 25), ("Lang", 30), ("Lang", 35), ("Lang", 40), ("Lang", 45),

    # Math - 10
    ("Math", 1), ("Math", 5), ("Math", 10), ("Math", 15), ("Math", 20),
    ("Math", 25), ("Math", 30), ("Math", 35), ("Math", 40), ("Math", 45),

    # Time - 8
    ("Time", 1), ("Time", 3), ("Time", 5), ("Time", 7),
    ("Time", 9), ("Time", 11), ("Time", 13), ("Time", 15),

    # Mockito - 8
    ("Mockito", 1), ("Mockito", 3), ("Mockito", 5), ("Mockito", 7),
    ("Mockito", 9), ("Mockito", 11), ("Mockito", 13), ("Mockito", 15),

    # Cli - 6
    ("Cli", 1), ("Cli", 3), ("Cli", 5),
    ("Cli", 7), ("Cli", 9), ("Cli", 11),

    # Codec - 6
    ("Codec", 1), ("Codec", 3), ("Codec", 5),
    ("Codec", 7), ("Codec", 9), ("Codec", 11),

    # Collections - 6
    ("Collections", 25), ("Collections", 26), ("Collections", 27),
    ("Collections", 28), ("Collections", 29), ("Collections", 30),

    # Compress - 6
    ("Compress", 1), ("Compress", 5), ("Compress", 10),
    ("Compress", 15), ("Compress", 20), ("Compress", 25),

    # Csv - 4
    ("Csv", 1), ("Csv", 2), ("Csv", 3), ("Csv", 4),

    # Gson - 4
    ("Gson", 1), ("Gson", 2), ("Gson", 3), ("Gson", 4),

    # JacksonCore - 3
    ("JacksonCore", 1), ("JacksonCore", 5), ("JacksonCore", 10),

    # JacksonDatabind - 3
    ("JacksonDatabind", 1), ("JacksonDatabind", 10), ("JacksonDatabind", 20),

    # JacksonXml - 3
    ("JacksonXml", 1), ("JacksonXml", 2), ("JacksonXml", 3),

    # Jsoup - 3
    ("Jsoup", 1), ("Jsoup", 5), ("Jsoup", 10),
]

# BUGS = [
#     # Chart
#     ("Chart", i) for i in range(1, 16)],

#     # Closure
#     ("Closure", 1), ("Closure", 5), ("Closure", 10), ("Closure", 15), ("Closure", 20),
#     ("Closure", 25), ("Closure", 30), ("Closure", 35), ("Closure", 40), ("Closure", 45),
#     ("Closure", 50), ("Closure", 55), ("Closure", 60), ("Closure", 65), ("Closure", 70),

#     # Lang
#     ("Lang", 1), ("Lang", 5), ("Lang", 10), ("Lang", 15), ("Lang", 20),
#     ("Lang", 25), ("Lang", 30), ("Lang", 35), ("Lang", 40), ("Lang", 45),
#     ("Lang", 50), ("Lang", 55), ("Lang", 60), ("Lang", 65), ("Lang", 70),

#     # Math
#     ("Math", 1), ("Math", 5), ("Math", 10), ("Math", 15), ("Math", 20),
#     ("Math", 25), ("Math", 30), ("Math", 35), ("Math", 40), ("Math", 45),
#     ("Math", 50), ("Math", 55), ("Math", 60), ("Math", 65), ("Math", 70),

#     # Time
#     ("Time", 1), ("Time", 3), ("Time", 5), ("Time", 7), ("Time", 9),
#     ("Time", 11), ("Time", 13), ("Time", 15), ("Time", 17), ("Time", 19),

#     # Mockito
#     ("Mockito", 1), ("Mockito", 3), ("Mockito", 5), ("Mockito", 7), ("Mockito", 9),
#     ("Mockito", 11), ("Mockito", 13), ("Mockito", 15), ("Mockito", 17), ("Mockito", 19),

#     # Cli
#     ("Cli", 1), ("Cli", 3), ("Cli", 5), ("Cli", 7), ("Cli", 9),
#     ("Cli", 11), ("Cli", 13), ("Cli", 15), ("Cli", 17), ("Cli", 19),

#     # Codec
#     ("Codec", 1), ("Codec", 3), ("Codec", 5), ("Codec", 7), ("Codec", 9),
#     ("Codec", 11), ("Codec", 13), ("Codec", 15), ("Codec", 17), ("Codec", 18),

#     # Collections
#     ("Collections", 25), ("Collections", 26), ("Collections", 27), ("Collections", 28), ("Collections", 29),
#     ("Collections", 30), ("Collections", 31), ("Collections", 32), ("Collections", 33), ("Collections", 34),

#     # Compress
#     ("Compress", 1), ("Compress", 5), ("Compress", 10), ("Compress", 15), ("Compress", 20),
#     ("Compress", 25), ("Compress", 30), ("Compress", 35), ("Compress", 40), ("Compress", 45),

#     # Csv
#     ("Csv", 1), ("Csv", 2), ("Csv", 3), ("Csv", 4), ("Csv", 5),

#     # Gson
#     ("Gson", 1), ("Gson", 2), ("Gson", 3), ("Gson", 4), ("Gson", 5),

#     # JacksonCore
#     ("JacksonCore", 1), ("JacksonCore", 5), ("JacksonCore", 10), ("JacksonCore", 15), ("JacksonCore", 20),

#     # JacksonDatabind
#     ("JacksonDatabind", 1), ("JacksonDatabind", 10), ("JacksonDatabind", 20),
#     ("JacksonDatabind", 30), ("JacksonDatabind", 40),

#     # JacksonXml
#     ("JacksonXml", 1), ("JacksonXml", 2), ("JacksonXml", 3), ("JacksonXml", 4), ("JacksonXml", 5),

#     # Jsoup
#     ("Jsoup", 1), ("Jsoup", 5), ("Jsoup", 10), ("Jsoup", 15), ("Jsoup", 20),
# ]


# =========================
# BASIC HELPERS
# =========================

def run_cmd(cmd, cwd=None, timeout=TIMEOUT):
    print(f"[CMD] {cmd}")

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

        return {
            "code": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "timeout": False,
        }

    except subprocess.TimeoutExpired as e:
        return {
            "code": -999,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "TIMEOUT",
            "timeout": True,
        }


def safe_name(project, bug_id):
    return f"{project}_{bug_id}"


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="ignore")


def read_text(path, max_chars=None):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + "\n\n/* TRUNCATED */\n"
    return text


# =========================
# DEFECTS4J OPERATIONS
# =========================

def checkout_bug(project, bug_id):
    repo = WORK_DIR / f"{project}_{bug_id}b"

    if repo.exists():
        shutil.rmtree(repo)

    result = run_cmd(
        f"defects4j checkout -p {project} -v {bug_id}b -w {repo}"
    )

    if result["code"] != 0:
        raise RuntimeError(result["stderr"])

    return repo


def compile_project(repo):
    return run_cmd("defects4j compile", cwd=repo)


def get_trigger_tests(repo):
    result = run_cmd("defects4j export -p tests.trigger", cwd=repo)

    tests = []
    for line in result["stdout"].splitlines():
        line = line.strip()
        if line:
            tests.append(line)

    return tests


def get_failing_output(repo, trigger_tests):
    if trigger_tests:
        outputs = []
        for test in trigger_tests[:5]:
            result = run_cmd(f"defects4j test -t {test}", cwd=repo, timeout=600)
            outputs.append(
                f"\n===== Trigger test: {test} =====\n"
                f"STDOUT:\n{result['stdout'][-8000:]}\n"
                f"STDERR:\n{result['stderr'][-8000:]}\n"
            )
        return "\n".join(outputs)

    result = run_cmd("defects4j test", cwd=repo, timeout=900)
    return result["stdout"][-12000:] + "\n" + result["stderr"][-12000:]


def get_source_dir(repo):
    result = run_cmd("defects4j export -p dir.src.classes", cwd=repo)

    src = result["stdout"].strip()
    if not src:
        src = "src/main/java"

    return repo / src


def get_test_dir(repo):
    result = run_cmd("defects4j export -p dir.src.tests", cwd=repo)

    src = result["stdout"].strip()
    if not src:
        src = "src/test/java"

    return repo / src


def get_relevant_java_files(repo, failing_output, trigger_tests, max_files=12):
    src_dir = get_source_dir(repo)
    test_dir = get_test_dir(repo)

    candidates = []

    text = failing_output + "\n" + "\n".join(trigger_tests)

    # Extract class names from stack traces and tests
    class_tokens = set(re.findall(r"([a-zA-Z_][\w$]*)(?:\.java|Test|::|\.)", text))

    java_files = []
    if src_dir.exists():
        java_files.extend(src_dir.rglob("*.java"))

    scored = []

    for f in java_files:
        score = 0
        name = f.stem

        if name in text:
            score += 10

        for token in class_tokens:
            if token and token in name:
                score += 5

        try:
            content = read_text(f, max_chars=30000)
            for test in trigger_tests:
                pieces = re.split(r"[.#:]", test)
                if any(p and p in content for p in pieces):
                    score += 2
        except Exception:
            pass

        scored.append((score, f))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [f for score, f in scored if score > 0][:max_files]

    if not selected:
        selected = java_files[:max_files]

    # Include triggering test files if available
    test_files = []
    if test_dir.exists():
        for test in trigger_tests:
            class_name = test.split("::")[0].split("#")[0]
            if class_name:
                rel = Path(*class_name.split(".")).with_suffix(".java")
                tf = test_dir / rel
                if tf.exists():
                    test_files.append(tf)

    return selected, test_files[:5]


# =========================
# PROMPT + DEEPSEEK
# =========================

def build_prompt(project, bug_id, repo, trigger_tests, failing_output, source_files, test_files):
    source_blocks = []

    for f in source_files:
        rel = f.relative_to(repo)
        content = read_text(f, max_chars=18000)
        source_blocks.append(
            f"\n--- FILE: {rel} ---\n"
            f"{content}\n"
        )

    test_blocks = []
    for f in test_files:
        rel = f.relative_to(repo)
        content = read_text(f, max_chars=12000)
        test_blocks.append(
            f"\n--- TEST FILE: {rel} ---\n"
            f"{content}\n"
        )

    return f"""
You are repairing a real Java bug from the Defects4J benchmark.

Project: {project}
Bug ID: {bug_id}

Triggering tests:
{chr(10).join(trigger_tests) if trigger_tests else "No triggering test was exported."}

Failing output:
{failing_output[-12000:]}

Relevant source files:
{chr(10).join(source_blocks)}

Relevant test files:
{chr(10).join(test_blocks)}

Task:
Generate a minimal developer-like patch that fixes the bug.

Strict output requirements:
1. Return ONLY a unified diff patch.
2. Do not include markdown.
3. Do not include explanation.
4. Use paths relative to the repository root.
5. The patch must be applicable from the repository root using:
   patch -p0 < patch_file
6. Prefer the smallest semantically correct change.
7. Do not modify tests.
"""


def call_deepseek(prompt, temperature=0.7):
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Java automated program repair system. "
                    "Return only a valid unified diff patch. "
                    "No markdown. No explanation."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return response.choices[0].message.content


def clean_patch(text):
    text = text.strip()

    text = re.sub(r"^```(?:diff|patch)?", "", text)
    text = re.sub(r"```$", "", text)
    text = text.strip()

    # Remove explanations before first diff marker
    markers = ["diff --git", "--- "]
    positions = [text.find(m) for m in markers if text.find(m) != -1]

    if positions:
        text = text[min(positions):]

    return text.strip() + "\n"


def looks_like_patch(text):
    return (
        ("--- " in text and "+++ " in text and "@@" in text)
        or "diff --git" in text
    )


# =========================
# MAIN PIPELINE
# =========================

def main():
    summary_rows = []

    for project, bug_id in BUGS:
        bug_key = safe_name(project, bug_id)
        print(f"\n==============================")
        print(f"Generating DeepSeek patches for {project}-{bug_id}")
        print(f"==============================")

        try:
            repo = checkout_bug(project, bug_id)

            compile_result = compile_project(repo)
            write_text(LOG_DIR / f"{bug_key}_compile.log",
                       compile_result["stdout"] + "\n" + compile_result["stderr"])

            trigger_tests = get_trigger_tests(repo)
            write_text(LOG_DIR / f"{bug_key}_trigger_tests.txt", "\n".join(trigger_tests))

            failing_output = get_failing_output(repo, trigger_tests)
            write_text(LOG_DIR / f"{bug_key}_failing_output.log", failing_output)

            source_files, test_files = get_relevant_java_files(
                repo=repo,
                failing_output=failing_output,
                trigger_tests=trigger_tests,
            )

            prompt = build_prompt(
                project=project,
                bug_id=bug_id,
                repo=repo,
                trigger_tests=trigger_tests,
                failing_output=failing_output,
                source_files=source_files,
                test_files=test_files,
            )

            write_text(LOG_DIR / f"{bug_key}_prompt.txt", prompt)

            for run_id in range(1, RUNS_PER_BUG + 1):
                print(f"[DEEPSEEK] {project}-{bug_id}, run {run_id}")

                try:
                    raw = call_deepseek(prompt, temperature=0.7)
                    patch = clean_patch(raw)

                    raw_file = PATCH_DIR / f"{bug_key}_llm_{run_id}_raw.txt"
                    patch_file = PATCH_DIR / f"{bug_key}_llm_{run_id}.patch"

                    write_text(raw_file, raw)
                    write_text(patch_file, patch)

                    valid_shape = looks_like_patch(patch)

                    summary_rows.append({
                        "project": project,
                        "bug_id": bug_id,
                        "run_id": run_id,
                        "patch_file": str(patch_file),
                        "raw_file": str(raw_file),
                        "looks_like_patch": valid_shape,
                        "status": "generated",
                    })

                    print(f"[SAVED] {patch_file} | looks_like_patch={valid_shape}")

                    time.sleep(1)

                except Exception as e:
                    err_file = LOG_DIR / f"{bug_key}_run_{run_id}_deepseek_error.txt"
                    write_text(err_file, str(e))

                    summary_rows.append({
                        "project": project,
                        "bug_id": bug_id,
                        "run_id": run_id,
                        "patch_file": "",
                        "raw_file": "",
                        "looks_like_patch": False,
                        "status": f"deepseek_error: {e}",
                    })

        except Exception as e:
            err_file = LOG_DIR / f"{bug_key}_pipeline_error.txt"
            write_text(err_file, str(e))

            summary_rows.append({
                "project": project,
                "bug_id": bug_id,
                "run_id": "",
                "patch_file": "",
                "raw_file": "",
                "looks_like_patch": False,
                "status": f"pipeline_error: {e}",
            })

    summary_csv = LOG_DIR / "deepseek_generation_summary.csv"

    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "project",
                "bug_id",
                "run_id",
                "patch_file",
                "raw_file",
                "looks_like_patch",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\n[DONE] Summary saved to: {summary_csv}")


if __name__ == "__main__":
    main()
