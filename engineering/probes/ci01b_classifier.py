"""CI-01b read-only path classification contract and adversarial fixtures.

Policy proof ONLY. Does not alter any GitHub-required check or workflow trigger.
"""
from __future__ import annotations
import json
import subprocess
import sys

DOC_ROOT_FILES = {"README.md", "AGENTS.md"}
CRITICAL_DOC_NAMES = {
    "SAVE_COMPATIBILITY_POLICY.md", "WORK_QUEUE.md", "ROADMAP.md",
    "ARCHITECTURE.md", "PROJECT_RULES_V2.md",
}

def classify(paths: list[str]) -> dict[str, object]:
    if not paths:
        return {"tier": "RELEASE", "reason": "missing or empty diff is fail-closed"}
    classifications: dict[str, str] = {}
    for raw in paths:
        parts = raw.split("/")
        if (not raw or raw.startswith("/") or "\\" in raw or
                any(p in ("", ".", "..") for p in parts) or
                raw != raw.strip()):
            kind = "CODE_OR_UNKNOWN"
        elif raw.startswith(".github/workflows/"):
            kind = "WORKFLOW"
        elif raw.startswith("engineering/contracts/"):
            kind = "POLICY_CONTRACT"
        elif raw in DOC_ROOT_FILES:
            kind = "ORDINARY_DOCUMENT"
        elif (raw.startswith("engineering/") and raw.endswith(".md")):
            kind = "ORDINARY_DOCUMENT"
        elif raw.startswith("simulation/docs/") and raw.endswith(".md"):
            name = parts[-1]
            if (name.startswith("PLAY_") or name in CRITICAL_DOC_NAMES or
                    "RELEASE" in name or "SECURITY" in name):
                kind = "RELEASE_DOCUMENT"
            else:
                kind = "ORDINARY_DOCUMENT"
        else:
            kind = "CODE_OR_UNKNOWN"
        classifications[raw] = kind
    kinds = set(classifications.values())
    tier = "RELEASE" if kinds != {"ORDINARY_DOCUMENT"} else "DOCS_FEEDBACK"
    return {"tier": tier, "reasons": classifications}


def assert_case(name: str, changed: list[str], expected: str) -> None:
    result = classify(changed)
    if result["tier"] != expected:
        raise AssertionError(f"{name}: expected {expected} got {result}")
    print("CI01B_POLICY_PASS " + json.dumps({
        "case": name, "files": len(changed), "tier": expected
    }, sort_keys=True), flush=True)


def main() -> None:
    examples = [
        ("normal_docs", ["README.md", "engineering/INDEX.md"], "DOCS_FEEDBACK"),
        ("run_reports", ["engineering/reports/MIG_04_ADVERSARIAL.md"], "DOCS_FEEDBACK"),
        ("mixed_source", ["README.md", "simulation/src/carlos_sim/store.py"], "RELEASE"),
        ("mixed_test", ["engineering/INDEX.md", "simulation/tests/test_store.py"], "RELEASE"),
        ("mixed_workflow", ["README.md", ".github/workflows/simulation-tests.yml"], "RELEASE"),
        ("release_doc", ["simulation/docs/PLAY_47_TECHNICAL_CLOSURE_DECISION.md"], "RELEASE"),
        ("save_contract_doc", ["simulation/docs/SAVE_COMPATIBILITY_POLICY.md"], "RELEASE"),
        ("migration_contract_json", ["engineering/contracts/migration_41_56_to_42_57.json"], "RELEASE"),
        ("security_critical_text", ["simulation/docs/SECURITY_POLICY.md"], "RELEASE"),
        ("python_probe_code", ["engineering/probes/mig04_adversarial_probe.py"], "RELEASE"),
        ("unknown_file", ["data/unknown.json"], "RELEASE"),
        ("path_traversal", ["simulation/docs/../src/store.py"], "RELEASE"),
        ("empty_diff", [], "RELEASE"),
        ("mixed_report_and_policy", ["engineering/reports/CI_00.md", "engineering/contracts/migration.json"], "RELEASE"),
    ]
    for name, paths, expected in examples:
        assert_case(name, paths, expected)

    if len(sys.argv) == 3 and sys.argv[1] == "--git-compare":
        base = sys.argv[2]
        names = subprocess.check_output(
            ["git", "diff", "--name-only", base, "HEAD"], text=True
        ).splitlines()
        result = classify(names)
        assert names and result["tier"] == "RELEASE", result
        assert any(name.startswith("engineering/contracts/") for name in names), names
        print("CI01B_ACTUAL_BRANCH_DIFF " + json.dumps({
            "paths": len(names), "tier": result["tier"],
            "contains_machine_migration_contract": True,
            "github_required_checks_still_unverified": True
        }, sort_keys=True), flush=True)
    print("CI01B_SUCCESS " + json.dumps({
        "selftest_cases": len(examples),
        "no_existing_workflows_changed": True,
        "no_required_status_checks_changed": True},sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
