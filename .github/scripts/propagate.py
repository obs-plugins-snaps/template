#!/usr/bin/env python3
"""Open template-update PRs on the managed plugin repositories.

Reads the plugin list from the meta repository (plugins/*.json records are
the single source of truth) and runs `copier update` on each plugin
repository whose `.copier-answers.yml` records an older template commit.
Each update lands on a `template-update-<tag>` branch with a pull request
for human review.

Environment:
    GITHUB_REPOSITORY       owner/name of the template repository
    GITHUB_REPOSITORY_OWNER organization login
    GITHUB_STEP_SUMMARY     summary file for the run report
Arguments:
    --tag       template tag to propagate, e.g. v0.0.6
    --plugins   JSON array of plugin names, e.g. ["source-record", ...]
    --summary   path of the GitHub step summary file
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass
class Result:
    plugin: str
    repo: str
    status: str
    detail: str = ""


def api(url: str, token: str, method: str = "GET", body: dict | None = None) -> dict:
    """Call the GitHub REST API and return the parsed JSON response."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = json.dumps(body).encode() if body is not None else None
    request = Request(url, headers=headers, data=data, method=method)
    try:
        with urlopen(request) as response:
            return json.load(response)
    except Exception as exc:  # noqa: BLE001 - reported per plugin below
        message = getattr(exc, "read", lambda: b"")()
        raise RuntimeError(f"{method} {url} failed: {exc} {message}") from exc


def run(*args: str, cwd: Path | None = None) -> str:
    """Run a command, returning stdout, or failing loudly."""
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def recorded_commit(repo: str, token: str) -> str | None:
    """Return the template commit a repo was generated from, if any."""
    url = f"https://api.github.com/repos/{repo}/contents/.copier-answers.yml"
    try:
        content = api(url, token)["content"]
    except RuntimeError:
        return None
    import base64

    text = base64.b64decode(content).decode()
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "_commit":
            return value.strip()
    return None


def branch_exists(repo: str, branch: str, token: str) -> bool:
    url = f"https://api.github.com/repos/{repo}/branches/{branch}"
    try:
        api(url, token)
    except RuntimeError:
        return False
    return True


def pr_exists(repo: str, head: str, token: str) -> bool:
    owner = repo.split("/", maxsplit=1)[0]
    url = f"https://api.github.com/repos/{repo}/pulls?head={owner}:{head}&state=open"
    return bool(api(url, token))


def template_changes(owner: str, old: str, tag: str, token: str) -> tuple[str, str]:
    """Summarize template history between old and tag for a PR body.

    Returns a Markdown section with the commits in between (message and
    author, from the compare API) and the files changed in the rendered
    part of the template (paths outside template/ are development-only
    and never reach a generated project).
    """
    try:
        comparison = api(
            f"https://api.github.com/repos/{owner}/template/compare/{old}...{tag}",
            token,
        )
    except RuntimeError:
        return "", ""

    commits = []
    for c in comparison.get("commits", []):
        sha = c["sha"][:7]
        title = c["commit"]["message"].splitlines()[0]
        commits.append(f"- [`{sha}`]({c['html_url']}) {title}")
    files = [
        f"- `{f['filename']}` ({f['status']})"
        for f in comparison.get("files", [])
        if f["filename"].startswith("template/")
    ]

    sections = []
    if commits:
        sections.append("Commits:\n" + "\n".join(commits))
    if files:
        sections.append("Files in the template:\n" + "\n".join(files))
    return "\n\n".join(sections), comparison["html_url"]


def repo_diffstat(work: Path) -> str:
    """Render the applied diff (what this repository actually got)."""
    lines = []
    try:
        stat = run("git", "diff", "--stat", "HEAD", cwd=work)
    except RuntimeError:
        # Defensive: conflicted merges leave the index in states some git
        # plumbing refuses; fall back to the porcelain status below.
        stat = ""
        lines.append("**Conflicts detected** - resolve the marked files in this PR.")
    if stat:
        lines += ["```diff", stat, "```"]
    status = run("git", "status", "--porcelain", cwd=work)
    entries = [
        line[2:].lstrip() for line in status.splitlines() if line and line[2:].strip()
    ]
    if entries:
        lines.append("Changed files:")
        lines += [f"- `{path}`" for path in entries]
    return "\n".join(lines) if lines else "(no changes)"


def update_one(plugin: str, repo: str, tag: str, token: str, owner: str) -> Result:
    branch = f"template-update-{tag}"

    if pr_exists(repo, branch, token):
        return Result(plugin, repo, "skipped", f"{branch} PR already exists")

    commit = recorded_commit(repo, token)
    if commit == tag:
        return Result(plugin, repo, "skipped", f"already on {tag}")

    # A previous run may have pushed the branch but failed to open the PR
    # (e.g. missing pull_requests permission); reuse the branch as-is.
    branch_ready = branch_exists(repo, branch, token)

    diffstat = ""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        clone_args = ["git", "clone", "--depth", "50"]
        if branch_ready:
            # --depth implies --single-branch; we need origin/main for the
            # diffstat below.
            clone_args += ["--branch", branch, "--no-single-branch"]
        clone_args += [f"https://x-access-token:{token}@github.com/{repo}", str(work)]
        run(*clone_args)

        if branch_ready:
            diffstat = (
                "```diff\n"
                + run("git", "diff", "--stat", "origin/main", "HEAD", cwd=work)
                + "\n```"
            )
        else:
            # The machine user identity: its registered SSH signing key
            # (repo secret CI_SSH_SIGNING_KEY) matches this noreply email, so
            # commits render as Verified.
            run("git", "config", "user.name", "obs-plugins-snaps-bot", cwd=work)
            run(
                "git",
                "config",
                "user.email",
                "346340553+obs-plugins-snaps-bot@users.noreply.github.com",
                cwd=work,
            )

            copier = ["uvx", "--from", "copier", "copier"]
            run(*copier, "update", "--defaults", "--vcs-ref", tag, cwd=work)

            if not run("git", "status", "--porcelain", cwd=work):
                return Result(plugin, repo, "skipped", "no changes rendered")

            diffstat = repo_diffstat(work)

            run("git", "checkout", "-b", branch, cwd=work)
            run("git", "add", "-A", cwd=work)
            run(
                "git",
                "commit",
                "-m",
                f"Update template to {tag}",
                cwd=work,
            )
            run("git", "push", "-u", "origin", branch, cwd=work)

    old = commit or "unknown"
    compare = f"https://github.com/{owner}/template/compare/{old}...{tag}"
    changes, compare_url = template_changes(owner, old, tag, token)
    if compare_url:
        compare = compare_url

    body_parts = [
        f"Automatic template update from `{old}` to `{tag}`.",
        f"[Full template comparison]({compare})",
    ]
    if changes:
        body_parts.append(f"## Template changes ({old} → {tag})\n\n{changes}")
    body_parts.append(f"## Applied to this repository\n\n{diffstat}")
    body_parts.append(
        "Generated with `copier update --defaults --vcs-ref "
        f"{tag}`; conflicts (if any) are marked in the files "
        "for manual resolution."
    )

    response = api(
        f"https://api.github.com/repos/{repo}/pulls",
        token,
        method="POST",
        body={
            "title": f"Update template to {tag}",
            "head": branch,
            "base": "main",
            "body": "\n\n".join(body_parts) + "\n",
        },
    )
    pr_url = response.get("html_url", "(url unavailable)")
    return Result(plugin, repo, "updated", f"[{pr_url}]({pr_url}) ({old} -> {tag})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--plugins", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    token = os.environ["GH_TOKEN"]
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]
    plugins: list[str] = json.loads(args.plugins)

    results: list[Result] = []
    for plugin in plugins:
        repo = f"{owner}/{plugin}-obs-studio-snap"
        try:
            # Fail early with a clear message when the repository does not
            # exist yet (record present, repo not created).
            api(f"https://api.github.com/repos/{repo}", token)
            results.append(update_one(plugin, repo, args.tag, token, owner))
        except RuntimeError as exc:
            text = str(exc)
            status = "missing repo" if "404" in text else "failed"
            results.append(Result(plugin, repo, status, text[:200]))

    lines = [
        "| Plugin | Repository | Status | Detail |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.plugin} | {r.repo} | {r.status} | {r.detail} |")
    Path(args.summary).write_text("\n".join(lines) + "\n")

    failures = [r for r in results if r.status == "failed"]
    if failures:
        sys.exit(f"{len(failures)} plugin(s) failed; see the summary")


if __name__ == "__main__":
    main()
