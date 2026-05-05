from __future__ import annotations

from pathlib import Path


def test_github_handoff_script_pushes_and_creates_pr_only_when_executed() -> None:
    script = Path("scripts/github-handoff.ps1").read_text(encoding="utf-8")

    assert 'Invoke-NativeCheck -FilePath "gh" -Arguments @("auth", "status")' in script
    assert "git remote add" in script
    assert "git push -u" in script
    assert "gh pr create" in script
    assert ".github\\PULL_REQUEST_DRAFT.md" in script
    assert "$Execute" in script


def test_github_handoff_reports_blockers_as_json() -> None:
    script = Path("scripts/github-handoff.ps1").read_text(encoding="utf-8")

    assert "github-handoff-v1" in script
    assert "remote_configured" in script
    assert "gh_authenticated" in script
    assert "worktree_clean" in script
    assert "next_commands" in script
