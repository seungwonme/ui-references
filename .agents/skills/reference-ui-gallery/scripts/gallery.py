"""Deterministic gallery build and explicit GitHub publication operations."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

VERSION = "0.4.0"
WORKFLOW = "UI reference pages"
PROJECT_SKILL_NAME = "reference-ui-gallery"
PROJECT_SKILL_ROOT = ".agents/skills/" + PROJECT_SKILL_NAME
RUNTIME_FILES = (
    "scripts/reference-ui.py", "scripts/gallery.py", "assets/config.example.json",
    "assets/reference-template.json", "assets/tokens-template.json", "assets/design-template.md",
    "assets/gallery.html", "assets/gallery.css", "assets/gallery.js", "assets/pages.yml",
)
SKILL_FILES = RUNTIME_FILES + (
    "SKILL.md", "README.md", "references/setup.md", "references/extraction.md",
    "references/package-contract.md", "references/gallery-and-reuse.md",
    "tests/test_reference_ui.py", "tests/eval-cases.json", "tests/eval-report.md",
)


def progress(stage, detail):
    print(f"[reference-ui] {stage}: {detail}", file=sys.stderr, flush=True)


def command(argv, cwd=None, check=True):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        diagnostic = result.stderr.strip() or result.stdout.strip() or "No diagnostic output."
        raise RuntimeError(f"{argv[0]} {argv[1] if len(argv)>1 else ''} failed (exit {result.returncode}): {diagnostic[:1500]}")
    return result


def repo_name(workspace, remote, api):
    urls = api.git(workspace, "remote", "get-url", remote)
    identity = api.remote_identity(urls[0]) if urls else None
    api.require(identity and identity[0] == "github.com" and identity[1] is None, "Publication requires a github.com remote; inspect doctor and configure the intended repository.")
    api.require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", identity[2]), "Remote must identify one GitHub owner/repository.")
    return identity[2]


def github_json(repo, endpoint, *args):
    return json.loads(command(["gh", "api", f"repos/{repo}/{endpoint}".rstrip("/"), *args]).stdout)


def managed_path(root, relative, api):
    path = Path(relative)
    api.require(not path.is_absolute() and ".." not in path.parts, "Managed path must stay within the checkout.")
    cursor = root
    for part in path.parts:
        cursor /= part
        api.require(not cursor.is_symlink(), f"Managed path traverses a symlink: {relative}")
    api.require(cursor.resolve().is_relative_to(root.resolve()), "Managed path escapes the checkout.")
    if cursor.is_file():
        api.require(cursor.stat().st_nlink == 1, "Managed files must not be hard links.")
    return cursor


def setup_gallery(args, path, api):
    api.require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo), "Use OWNER/REPOSITORY for --repo.")
    workspace = Path(args.directory).expanduser().resolve()
    desired = api.normalize_config({"workspace_path": str(workspace), "bootstrap_url": f"https://github.com/{args.repo}.git", "remote_name": "origin"})
    if path.exists():
        api.require(api.normalize_config(api.load_json(path)) == desired, "Existing user config selects another gallery; use config set explicitly instead of replacing it.")
    if workspace.exists():
        api.require(workspace.is_dir(), "Gallery directory is not a directory.")
        _, info = api.workspace_info(desired)
        api.require(info["bootstrap_comparison"] == "match", "Existing checkout does not match the requested repository.")
    plan = {"repository": args.repo, "workspace": str(workspace), "visibility": args.visibility, "config": str(path), "applied": False}
    if not args.apply:
        return plan
    found = command(["gh", "api", f"repos/{args.repo}"], check=False)
    if found.returncode:
        api.require("404" in found.stderr, "Cannot inspect repository; repair GitHub authentication or network access before setup.")
        command(["gh", "repo", "create", args.repo, f"--{args.visibility}", "--add-readme", "--description", "Reusable UI reference studies, design systems, and working prototypes"])
    else:
        actual = json.loads(found.stdout)
        api.require(actual["private"] == (args.visibility == "private"), "Existing repository visibility differs; setup will not change it.")
    if not workspace.exists():
        workspace.parent.mkdir(parents=True, exist_ok=True)
        command(["gh", "repo", "clone", args.repo, str(workspace)])
    api.workspace_info(desired)
    with api.config_lock(path):
        if not path.exists():
            api.save_config(path, desired)
    plan["applied"] = True
    return plan


def public_files(root, metadata, api):
    files = metadata["publication"].get("files")
    api.require(isinstance(files, list) and files and all(api.nonempty(x) for x in files), "publication.files must explicitly list the files approved for export.")
    api.require(len(files) == len(set(files)), "publication.files contains duplicates.")
    required = {"DESIGN.md", "tokens.json", "reference.json", metadata["preview"]}
    if metadata.get("thumbnail"):
        required.add(metadata["thumbnail"])
    for check in metadata["verification"].values():
        required.update(check["evidence"])
    api.require(required <= set(files), "publication.files omits a document, preview, thumbnail, or verification evidence file.")
    for relative in files:
        path = api.safe_path(root, relative, exists=True)
        api.require(path.stat().st_nlink == 1, "Public files must not be hard links.")
        if path.suffix.lower() in {".html", ".css", ".js", ".json", ".md", ".txt", ".svg"}:
            content = path.read_text(encoding="utf-8")
            check_public_text(content, relative, api)
    return sorted(files)


def check_public_text(content, label, api):
    api.require(not re.search(r"file:///|/Users/|/private/var/folders/|/var/folders/|/home/[^/\s]+/", content), f"Public file contains a machine-local path: {label}")
    api.require(not re.search(r"https?://[^\s/\"'<>]+:[^\s/@\"'<>]+@|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", content), f"Public file contains a credential marker: {label}")


def gallery_style(path, api):
    path = managed_path(path.parent, path.name, api)
    api.require(path.is_file() and path.suffix == ".css", "Gallery style must be an existing UTF-8 .css file.")
    content = path.read_text(encoding="utf-8")
    check_public_text(content, "gallery.css", api)
    return content


def token_css(document, api):
    """Opt-in CSS export for primitive tokens; source token values remain canonical."""
    nodes = {}
    def walk(group, prefix="", inherited=None):
        kind = group.get("$type", inherited)
        if "$value" in group:
            nodes[prefix] = (group, kind)
            return
        for key, value in group.items():
            if not key.startswith("$"):
                walk(value, f"{prefix}.{key}" if prefix else key, kind)
    walk(document)
    def value_for(name, chain=()):
        api.require(name not in chain and name in nodes, "Cannot export an unresolved token alias.")
        node, kind = nodes[name]
        value = node["$value"]
        if isinstance(value, str) and re.fullmatch(r"\{[^{}]+\}", value):
            target = value[1:-1]
            target_node = nodes.get(target, ({}, None))[0]
            css_name = target_node.get("$extensions", {}).get("reference-ui", {}).get("css_name")
            if css_name:
                return f"var({css_name})"
            return value_for(target, (*chain, name))
        if kind == "dimension" or kind == "duration":
            api.require(isinstance(value, dict) and isinstance(value.get("value"), (float, int)) and value.get("unit") in {"px", "rem", "ms", "s"}, f"Invalid dimension/duration for CSS export: {name}")
            return f'{value["value"]:g}{value["unit"]}'
        if kind == "color":
            api.require(isinstance(value, dict) and isinstance(value.get("components"), list), f"Invalid color for CSS export: {name}")
            space = value.get("colorSpace")
            api.require(space in {"srgb", "oklch", "oklab"}, f"CSS exporter needs srgb/oklch/oklab color: {name}")
            components = " ".join(str(v) for v in value["components"])
            alpha = value.get("alpha", 1)
            return f'color(srgb {components} / {alpha})' if space == "srgb" else f'{space}({components} / {alpha})'
        if kind == "fontFamily":
            return ",".join(json.dumps(v) for v in value) if isinstance(value, list) else json.dumps(value)
        api.require(kind in {"number", "fontWeight"}, f"CSS exporter does not support this token type: {name}")
        api.require(isinstance(value, (int, float)) and not isinstance(value, bool), f"CSS numeric token needs a number: {name}")
        return str(value)
    rules = {}
    for name, (node, _) in nodes.items():
        extension = node.get("$extensions", {}).get("reference-ui", {})
        css_name = extension.get("css_name")
        if not css_name:
            continue
        api.require(re.fullmatch(r"--[a-zA-Z0-9_-]+", css_name), "Invalid CSS custom-property name.")
        theme = extension.get("theme", "base")
        api.require(theme in {"base", "light", "dark"}, "CSS token theme must be base, light, or dark.")
        rules.setdefault(theme, []).append(f"{css_name}:{value_for(name)};")
    selectors = {"base": ":root", "light": ":root,.light", "dark": ":root.dark,.dark"}
    return "/* Generated from tokens.json. */\n" + "\n".join(selectors[theme] + "{" + "".join(rules[theme]) + "}" for theme in ("base", "light", "dark") if theme in rules) + "\n"


def check_links(site, api):
    for path in site.rglob("*"):
        if path.suffix not in {".html", ".css"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', text) if path.suffix == ".html" else []
        links += re.findall(r'url\(["\']?([^\s)"\']+)', text)
        for link in links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            api.require(not parsed.path.startswith("/"), f"Use relative links for Pages project paths: {path.name}")
            target = (path.parent / unquote(parsed.path)).resolve()
            api.require(target.is_relative_to(site.resolve()), f"Link escapes built site: {path.name}")
            api.require(target.exists(), f"Broken built-site link: {path.relative_to(site)} -> {parsed.path}")


def build_site(workspace, output, api, drafts=False):
    api.require(not (drafts and os.environ.get("GITHUB_ACTIONS") == "true"), "Draft builds are local-only; CI publishes reviewed entries.")
    output = Path(output).expanduser().resolve()
    api.require(output != workspace and not workspace.is_relative_to(output), "Build output cannot be the checkout or its parent.")
    api.require(not output.exists() or (output.is_dir() and not any(output.iterdir())), "Build output must be new or empty; use a fresh directory so stale files cannot be published.")
    listing = api.catalog(workspace, include_drafts=drafts, public=not drafts)
    api.require(listing["items"], "No reviewed, ready public entries are available to build.")
    prepared = []
    for item in listing["items"]:
        root = api.entry_root(workspace, item["id"])
        metadata, _ = api.validate_entry(root, public=not drafts)
        files = public_files(root, metadata, api)
        prepared.append((root, metadata, files))
    output.mkdir(parents=True, exist_ok=True)
    for root, metadata, files in prepared:
        destination = output / "references" / root.name
        destination.mkdir(parents=True)
        for relative in files:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        css_output = metadata["prototype"].get("token_css")
        if css_output:
            api.require(css_output not in files, "Generated token CSS must not be a separately maintained input file.")
            target = api.safe_path(destination, css_output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(token_css(api.load_json(root / "tokens.json"), api), encoding="utf-8")
    assets = output / "assets"
    assets.mkdir()
    for name in ("gallery.css", "gallery.js"):
        shutil.copyfile(api.ASSETS / name, assets / name)
    data = api.dump_json(listing).replace("<", "\\u003c")
    style = managed_path(workspace, "gallery.css", api)
    custom = ""
    if style.exists():
        (output / "gallery.css").write_text(gallery_style(style, api), encoding="utf-8")
        custom = '<link rel="stylesheet" href="gallery.css">'
    document = (api.ASSETS / "gallery.html").read_text(encoding="utf-8")
    document = document.replace("<!-- GALLERY_STYLE -->", custom)
    document = document.replace("<!-- DRAFT_NOTICE -->", '<p class="draft-notice" role="status">DRAFT / 검증 전 로컬 미리보기</p>' if drafts else "")
    (output / "index.html").write_text(document.replace("CATALOG_DATA", data), encoding="utf-8")
    (output / "catalog.json").write_text(api.dump_json(listing), encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    check_links(output, api)
    commit = api.git(workspace, "rev-parse", "HEAD")[0]
    manifest = {"schema_version": 1, "commit": commit, "builder_version": VERSION, "drafts": drafts, "entries": [item["id"] for item in listing["items"]], "files": {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob("*")) if p.is_file()}}
    (output / "build.json").write_text(api.dump_json(manifest), encoding="utf-8")
    return {"output": str(output), "entries": manifest["entries"], "commit": commit, "files": len(manifest["files"]) + 1}


def project_skill_file(relative, api):
    source = managed_path(api.SKILL_ROOT, relative, api)
    api.require(source.is_file(), "Project skill export requires the complete skill package; run publish from the installed full skill, not a minimal CI runtime.")
    content = source.read_text(encoding="utf-8")
    if relative == "SKILL.md" and "\nname: reference-ui\n" in content:
        content = content.replace("\nname: reference-ui\n", "\nname: " + PROJECT_SKILL_NAME + "\n", 1)
        content = content.replace('description: "', 'description: "이 갤러리 저장소에서 ', 1)
    elif relative == "README.md":
        content = content.replace("# reference-ui\n", "# " + PROJECT_SKILL_NAME + "\n", 1)
    elif relative == "tests/eval-cases.json":
        data = json.loads(content)
        data["skill_name"] = PROJECT_SKILL_NAME
        content = api.dump_json(data)
    return content.encode("utf-8")


def install_bundle(worktree, default_branch, api, project_skill=False):
    api.require(re.fullmatch(r"[A-Za-z0-9._/-]+", default_branch), "Default branch name cannot be embedded safely in the workflow template.")
    generated = {}
    for relative in RUNTIME_FILES:
        generated[".reference-ui/" + relative] = (api.SKILL_ROOT / relative).read_bytes()
    project_skill = project_skill or (worktree / PROJECT_SKILL_ROOT / "SKILL.md").exists()
    if project_skill:
        for relative in SKILL_FILES:
            generated[PROJECT_SKILL_ROOT + "/" + relative] = project_skill_file(relative, api)
    wrapper = '''#!/usr/bin/env python3
import runpy
import sys
from pathlib import Path
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
runner = root / ".agents/skills/reference-ui-gallery/scripts/reference-ui.py"
if not runner.is_file():
    runner = root / ".reference-ui/scripts/reference-ui.py"
sys.path.insert(0, str(runner.parent))
sys.argv = [str(runner), "--workspace", str(root), *sys.argv[1:]]
runpy.run_path(str(runner), run_name="__main__")
'''
    generated["scripts/gallery.py"] = wrapper.encode()
    generated[".github/workflows/pages.yml"] = (api.ASSETS / "pages.yml").read_text().replace("DEFAULT_BRANCH", default_branch).encode()
    manifest_path = managed_path(worktree, ".reference-ui/bundle.json", api)
    previous = api.load_json(manifest_path).get("files", {}) if manifest_path.exists() else {}
    for name, data in generated.items():
        target = managed_path(worktree, name, api)
        if target.exists() and target.read_bytes() != data:
            api.require(name in previous and hashlib.sha256(target.read_bytes()).hexdigest() == previous[name], f"Managed file was edited outside the generator: {name}; review it before updating.")
    for name, data in generated.items():
        target = worktree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest_path.write_text(api.dump_json({"version": VERSION, "project_skill": PROJECT_SKILL_NAME if project_skill else None, "files": {name: hashlib.sha256(data).hexdigest() for name, data in generated.items()}}), encoding="utf-8")
    return list(generated) + [".reference-ui/bundle.json"]


def wait_workflow(repo, commit, event, timeout):
    deadline = time.monotonic() + timeout
    previous = None
    while time.monotonic() < deadline:
        result = command(["gh", "run", "list", "--repo", repo, "--commit", commit, "--event", event, "--limit", "30", "--json", "databaseId,workflowName,status,conclusion,url,headSha"])
        runs = [x for x in json.loads(result.stdout) if x["workflowName"] == WORKFLOW and x["headSha"] == commit]
        if runs:
            run = runs[0]
            if run["status"] != previous:
                progress(event, f"{run['status']} {run['url']}")
                previous = run["status"]
            if run["status"] == "completed":
                if run["conclusion"] != "success":
                    raise RuntimeError(f"Workflow failed ({run['conclusion']}): {run['url']}. Inspect gh run view {run['databaseId']} --repo {repo} --log-failed.")
                return run
        time.sleep(5)  # GitHub queues and publishes asynchronous workflow state.
    raise RuntimeError(f"Timed out waiting for {event} workflow at commit {commit}; inspect GitHub Actions and resume with finish.")


def enable_pages(repo):
    existing = command(["gh", "api", f"repos/{repo}/pages"], check=False)
    if existing.returncode:
        if "404" not in existing.stderr:
            raise RuntimeError("Cannot inspect Pages settings; repair GitHub access before enabling deployment.")
        return github_json(repo, "pages", "--method", "POST", "-f", "build_type=workflow")
    current = json.loads(existing.stdout)
    if current.get("build_type") != "workflow":
        raise RuntimeError("Existing Pages site uses another publishing source; review that site before changing it.")
    return current


def finish(repo, pr_number, workspace, remote, merge, timeout, api, expected_entry=None):
    info = json.loads(command(["gh", "pr", "view", str(pr_number), "--repo", repo, "--json", "state,headRefOid,headRefName,baseRefName,mergeCommit,url,title"]).stdout)
    match = re.fullmatch(r"feat\(references\): publish ([a-z0-9]+(?:-[a-z0-9]+)*)", info["title"])
    expected_entry = expected_entry or (match[1] if match else None)
    api.require(expected_entry and api.SLUG.fullmatch(expected_entry), "Cannot identify the requested entry; pass --entry explicitly when resuming a renamed PR.")
    if info["state"] == "OPEN":
        checks = wait_workflow(repo, info["headRefOid"], "pull_request", timeout)
        if not merge:
            return {"stage": "review-ready", "pr": info["url"], "checks": checks["url"]}
        enable_pages(repo)
        progress("merge", info["url"])
        command(["gh", "pr", "merge", str(pr_number), "--repo", repo, "--merge", "--match-head-commit", info["headRefOid"]])
        info = json.loads(command(["gh", "pr", "view", str(pr_number), "--repo", repo, "--json", "state,headRefOid,headRefName,baseRefName,mergeCommit,url,title"]).stdout)
    api.require(info["state"] == "MERGED", "PR is not open or merged; inspect it before continuing.")
    commit = info["mergeCommit"]["oid"]
    deployment = wait_workflow(repo, commit, "push", timeout)
    pages = github_json(repo, "pages")
    url = pages["html_url"]
    api.require(urlsplit(url).scheme == "https", "Expected a public HTTPS Pages URL.")
    deadline = time.monotonic() + timeout
    actual = None
    while time.monotonic() < deadline:
        try:
            with urlopen(Request(urljoin(url, "build.json") + "?commit=" + commit, headers={"Cache-Control": "no-cache"}), timeout=15) as response:
                actual = json.load(response)
            if actual.get("commit") == commit and actual.get("drafts") is False:
                break
        except (OSError, ValueError):
            pass
        time.sleep(5)
    api.require(actual and actual.get("commit") == commit and actual.get("drafts") is False, "Pages has not served the reviewed merged build manifest yet; resume finish instead of publishing another PR.")
    api.require(expected_entry in actual.get("entries", []), "Deployed manifest is missing the requested reference entry.")
    entry_metadata = f"references/{expected_entry}/reference.json"
    api.require(entry_metadata in actual.get("files", {}), "Deployed manifest is missing the requested entry metadata.")
    with urlopen(urljoin(url, entry_metadata) + "?commit=" + commit, timeout=15) as response:
        payload = response.read()
        api.require(hashlib.sha256(payload).hexdigest() == actual["files"][entry_metadata], "Published entry does not match the reviewed build manifest.")
    for relative in ("index.html", "catalog.json"):
        with urlopen(urljoin(url, relative), timeout=15) as response:
            api.require(response.status == 200, "Published gallery resource is unavailable.")
    command(["git", "fetch", remote], cwd=workspace)
    branch = api.git(workspace, "branch", "--show-current")[0]
    updated = False
    if branch == info["baseRefName"]:
        updated = command(["git", "merge", "--ff-only", f"{remote}/{branch}"], cwd=workspace, check=False).returncode == 0
    result = {"stage": "deployed", "pr": info["url"], "url": url, "commit": commit, "workflow": deployment["url"], "workspace_updated": updated, "head_branch": info["headRefName"], "entries": actual["entries"]}
    progress("verified", url)
    # Clean only worktrees carrying this publisher's receipt and matching PR/head.
    for block in command(["git", "worktree", "list", "--porcelain"], cwd=workspace).stdout.strip().split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        if fields.get("branch") != "refs/heads/" + info["headRefName"]:
            continue
        candidate = Path(fields["worktree"])
        receipt = candidate.parent / "result.json"
        if not candidate.parent.name.startswith("reference-ui-publish-") or not receipt.is_file() or receipt.is_symlink():
            continue
        record = api.load_json(receipt)
        if record.get("pr") != info["url"] or record.get("head") != info["headRefOid"]:
            continue
        api.require(api.git(candidate, "rev-parse", "HEAD")[0] == record["head"], "Published worktree has additional commits; preserve it and inspect before cleanup.")
        api.require(not command(["git", "status", "--porcelain"], cwd=candidate).stdout.strip(), "Published worktree has additional changes; preserve it and inspect before cleanup.")
        api.require(not command(["git", "ls-files", "--others", "--ignored", "--exclude-standard"], cwd=candidate).stdout.strip(), "Published worktree has ignored files; preserve them before cleanup.")
        command(["git", "worktree", "remove", str(candidate)], cwd=workspace)
        command(["git", "branch", "-d", info["headRefName"]], cwd=workspace)
        if command(["git", "ls-remote", "--heads", remote, "refs/heads/" + info["headRefName"]], cwd=workspace).stdout.strip():
            command(["git", "push", remote, "--delete", info["headRefName"]], cwd=workspace)
        result["receipt"] = str(receipt)
        receipt.write_text(api.dump_json(result), encoding="utf-8")
    return result


def publish(args, workspace, data, api):
    source = Path(args.source).expanduser().resolve()
    metadata, _ = api.validate_entry(source, public=True)
    api.require(metadata["status"] == "ready", "Publish requires status=ready; draft references are excluded from public builds.")
    files = public_files(source, metadata, api)
    style = gallery_style(Path(args.gallery_style).expanduser().absolute(), api) if args.gallery_style else None
    repo = repo_name(workspace, data["remote_name"], api)
    plan = {"stage": "plan", "repository": repo, "entry": metadata["id"], "files": files, "merge_requested": args.merge, "gallery_style": "gallery.css" if style is not None else None}
    plan["project_skill"] = PROJECT_SKILL_NAME if args.project_skill or (workspace / PROJECT_SKILL_ROOT / "SKILL.md").exists() else None
    if not args.apply:
        return plan
    repository = github_json(repo, "")
    existing = json.loads(command(["gh", "pr", "list", "--repo", repo, "--state", "open", "--search", f'"feat(references): publish {metadata["id"]}" in:title', "--json", "number,title,url"]).stdout)
    duplicate = next((pr for pr in existing if pr["title"] == f'feat(references): publish {metadata["id"]}'), None)
    api.require(not duplicate, f"An entry PR is already open; inspect it and resume with finish --pr {duplicate['number']} --apply instead of publishing again." if duplicate else "")
    default_branch = repository["default_branch"]
    remote = data["remote_name"]
    command(["git", "fetch", remote], cwd=workspace)
    run = Path(tempfile.mkdtemp(prefix="reference-ui-publish-"))
    worktree = run / "worktree"
    branch = "feat/reference-" + metadata["id"] + "-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    receipt = run / "result.json"
    receipt.write_text(api.dump_json({**plan, "stage": "preparing", "worktree": str(worktree), "branch": branch}), encoding="utf-8")
    progress("receipt", str(receipt))
    try:
        command(["git", "worktree", "add", "--no-track", "-b", branch, str(worktree), f"{remote}/{default_branch}"], cwd=workspace)
        target = managed_path(worktree, "references/" + metadata["id"], api)
        for relative in files:
            destination = api.safe_path(target, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
        managed = install_bundle(worktree, default_branch, api, project_skill=args.project_skill)
        if style is not None:
            managed_path(worktree, "gallery.css", api).write_text(style, encoding="utf-8")
            managed.append("gallery.css")
        built = build_site(worktree, run / "site", api)
        api.require(metadata["id"] in built["entries"], "Local build omitted the requested entry.")
        progress("local-build", f"{metadata['id']}: {built['files']} files")
        command(["git", "add", "--", *managed, "references/" + metadata["id"]], cwd=worktree)
        command(["git", "diff", "--cached", "--check"], cwd=worktree)
        changed = command(["git", "diff", "--cached", "--quiet"], cwd=worktree, check=False).returncode
        api.require(changed == 1, "No changed reference/runtime files to publish.")
        command(["git", "commit", "-m", f"feat(references): publish {metadata['id']}"], cwd=worktree)
        head = api.git(worktree, "rev-parse", "HEAD")[0]
        command(["git", "push", "-u", remote, branch], cwd=worktree)
        body = run / "pr-body.md"
        body.write_text(f"## Summary\n\nPublish `{metadata['id']}` with its prototype, design rules, tokens and reviewed assets.\n\n## Validation\n\nPackage/public-record validation and local static build passed ({built['files']} files). CI repeats validation and builds the Pages artifact. Visual verification scope is recorded in the entry metadata.\n\n## Review\n\nReview source fidelity, recorded limitations and the explicit public file list. Deployment occurs after merge.\n", encoding="utf-8")
        url = command(["gh", "pr", "create", "--repo", repo, "--base", default_branch, "--head", branch, "--title", f"feat(references): publish {metadata['id']}", "--body-file", str(body)], cwd=worktree).stdout.strip()
        number = int(url.rstrip("/").split("/")[-1])
        progress("pull-request", url)
        receipt.write_text(api.dump_json({**plan, "stage": "pr-created", "pr": url, "head": head, "worktree": str(worktree), "resume": f"finish --pr {number} --merge --apply"}), encoding="utf-8")
        result = finish(repo, number, workspace, remote, args.merge, args.timeout, api, metadata["id"])
        result["receipt"] = str(receipt)
        if result["stage"] != "deployed":
            result["worktree"] = str(worktree)
            result.update(head=head, branch=branch)
        receipt.write_text(api.dump_json(result), encoding="utf-8")
        return result
    except Exception as exc:
        raise RuntimeError(f"{exc}\nPublication state preserved at {receipt}. Resume the existing PR with finish when available.") from None
