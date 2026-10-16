#!/usr/bin/env python3
"""Reference packages, static gallery builds, and explicit GitHub publishing."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from urllib.parse import parse_qsl, quote, urlsplit

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
CHECKS = ("new_screen", "visual", "states", "responsive", "accessibility")
STATES = {"pass", "fail", "not-run", "not-applicable"}
TOKEN_TYPES = {"color", "dimension", "fontFamily", "fontWeight", "duration", "cubicBezier", "number", "strokeStyle", "border", "transition", "shadow", "gradient", "typography"}


class UserError(Exception):
    """An actionable input error without raw config or credential disclosure."""


def require(condition, message):
    if not condition:
        raise UserError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def choice(value, values):
    return isinstance(value, str) and value in values


def source_location(value):
    require(nonempty(value), "Source location must be non-empty.")
    require(not any(ord(c) < 32 for c in value), "Source location contains control characters.")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise UserError("Source URL cannot be parsed.") from None
    require(not parsed.username and not parsed.password, "Source URL contains credentials; supply a credential-free source location.")
    sensitive = {"access_token", "token", "api_key", "apikey", "password", "secret", "authorization", "signature", "sig", "code"}
    require(not any(key.lower() in sensitive for key, _ in parse_qsl(parsed.query) + parse_qsl(parsed.fragment)), "Source URL contains a sensitive query/fragment parameter; supply a public canonical source location.")
    return value


def load_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise UserError(f"Missing file: {path}. Create it with the documented setup/new command.") from None
    except (OSError, UnicodeError):
        raise UserError(f"Cannot read UTF-8 file: {path}") from None
    except json.JSONDecodeError as exc:
        raise UserError(f"Invalid JSON in {path} at line {exc.lineno}, column {exc.colno}; fix it before continuing.") from None
    require(isinstance(value, dict), f"Expected a JSON object in {path}")
    return value


def dump_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def config_path(explicit):
    if explicit:
        return Path(explicit).expanduser().absolute()
    root = os.environ.get("XDG_CONFIG_HOME")
    require(not root or Path(root).is_absolute(), "XDG_CONFIG_HOME must be absolute; fix it or pass --config.")
    return (Path(root) if root else Path.home() / ".config") / "reference-ui/config.json"


def remote_identity(value, strict=False):
    """Compare common HTTPS/SSH forms, without assuming SSH aliases are resolvable."""
    if not value:
        return None
    require(isinstance(value, str), "Remote URL must be a string.")
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise UserError("Remote URL contains whitespace or control characters.")
    match = re.fullmatch(r"[^/@:]+@([^/:]+):(.+)", value)
    if match:
        host, repo = match.groups()
        port = None
    else:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            raise UserError("Remote URL cannot be parsed.") from None
        valid = parsed.scheme in {"https", "ssh"} and parsed.hostname and not parsed.query and not parsed.fragment
        if not valid:
            require(not strict, "Use a credential-free HTTPS or SSH repository URL.")
            return None
        require(not parsed.password and not (parsed.scheme == "https" and parsed.username), "Store credentials in the existing credential manager, not in the repository URL.")
        host, repo = parsed.hostname, parsed.path
        if (parsed.scheme, port) in {("https", 443), ("ssh", 22)}:
            port = None
    repo = repo.strip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    require(bool(repo) and ".." not in repo.split("/"), "Remote URL needs a repository path.")
    return (host.lower(), port, repo)


def normalize_config(data):
    require(set(data) <= {"workspace_path", "bootstrap_url", "remote_name"}, "Unknown config key; use workspace_path, bootstrap_url, remote_name.")
    require(nonempty(data.get("workspace_path")), "workspace_path is empty; run config init/set --workspace with the gallery checkout.")
    workspace = Path(data["workspace_path"]).expanduser()
    require(workspace.is_absolute(), "workspace_path must be absolute or start with ~/.")
    remote = data.get("remote_name", "origin")
    require(isinstance(remote, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote), "remote_name must be a simple Git remote name.")
    bootstrap = data.get("bootstrap_url", "")
    require(isinstance(bootstrap, str), "bootstrap_url must be a string; use an empty string for a local-only gallery.")
    remote_identity(bootstrap, strict=True)
    return {"workspace_path": str(workspace.resolve()), "bootstrap_url": bootstrap, "remote_name": remote}


@contextmanager
def config_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise UserError(f"Config is locked: {lock}. Check the other writer before retrying.") from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def save_config(path, data):
    require(not path.is_symlink(), "Config file is a symlink; select its canonical path with --config.")
    # Write beside the destination so replacement is atomic on the same filesystem.
    fd, name = tempfile.mkstemp(prefix=".reference-ui-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(dump_json(data))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def configure(args, path):
    with config_lock(path):
        if args.action == "init":
            data = load_json(ASSETS / "config.example.json")
        else:
            data = load_json(path)
        for argument, key in (("workspace", "workspace_path"), ("bootstrap_url", "bootstrap_url"), ("remote_name", "remote_name")):
            value = getattr(args, argument)
            if value is not None:
                data[key] = value
        data = normalize_config(data)
        if args.action == "init" and path.exists():
            require(normalize_config(load_json(path)) == data, "Config already exists with different values; use config set explicitly.")
            return {"config": str(path), "changed": False}
        save_config(path, data)
    return {"config": str(path), "changed": True}


def git(workspace, *arguments, optional=False):
    try:
        # These local metadata commands should finish promptly; no fetch is performed.
        result = subprocess.run(["git", "-C", str(workspace), *arguments], capture_output=True, text=True, timeout=15)
    except FileNotFoundError:
        raise UserError("Git is unavailable; install it through the environment's package workflow.") from None
    except subprocess.TimeoutExpired:
        raise UserError("Git metadata query timed out; inspect the selected checkout.") from None
    if result.returncode:
        if optional:
            return []
        raise UserError("Selected workspace is not an accessible Git checkout root.")
    return result.stdout.strip().splitlines()


def workspace_info(data):
    workspace = Path(data["workspace_path"])
    require(workspace.is_dir(), "Workspace does not exist; clone/create the intended gallery explicitly, then run doctor.")
    if (SKILL_ROOT / "SKILL.md").exists():
        require(workspace != SKILL_ROOT and SKILL_ROOT not in workspace.parents and workspace not in SKILL_ROOT.parents, "Gallery checkout must be separate from the skill installation.")
    roots = git(workspace, "rev-parse", "--show-toplevel")
    require(roots and Path(roots[0]).resolve() == workspace.resolve(), "workspace_path must name the Git checkout root, not a nested folder.")
    remote = data["remote_name"]
    fetch = git(workspace, "remote", "get-url", "--all", remote, optional=True)
    push = git(workspace, "remote", "get-url", "--push", "--all", remote, optional=True)
    expected = remote_identity(data["bootstrap_url"], strict=True)
    actual = [remote_identity(url) for url in fetch + push]
    comparison = "not-configured" if not expected else "match"
    if expected and (not actual or any(value != expected for value in actual)):
        comparison = "mismatch-or-unresolved"
    refs = workspace / "references"
    require(not refs.is_symlink(), "references directory must not be a symlink.")
    return workspace, {"workspace": str(workspace), "remote_name": remote, "remote_configured": bool(fetch), "fetch_url_count": len(fetch), "push_url_count": len(push), "bootstrap_comparison": comparison, "entries": len(list(refs.glob("*/reference.json"))) if refs.is_dir() else 0}


def safe_path(root, relative, exists=False):
    require(nonempty(relative) and "\\" not in relative and ":" not in relative, "Use a non-empty forward-slash relative file path.")
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts and not any(part.startswith(".") for part in path.parts), "Entry paths must stay inside the item and cannot name hidden files.")
    result = root.joinpath(*path.parts)
    require(result.resolve().is_relative_to(root.resolve()), "Entry path escapes its item directory.")
    cursor = root
    for part in path.parts:
        cursor /= part
        require(not cursor.is_symlink(), "Entry paths must not traverse symlinks.")
    if exists:
        require(result.is_file(), f"Referenced file is missing: {relative}")
    return result


def entry_root(workspace, slug):
    require(isinstance(slug, str) and SLUG.fullmatch(slug), "Entry id must be one lowercase kebab-case path segment.")
    root = workspace / "references" / slug
    require(not root.is_symlink(), "Entry directory must not be a symlink.")
    return root


def new_entry(args, workspace):
    root = entry_root(workspace, args.slug)
    require(not root.exists(), "Entry already exists; read and update its files instead of recreating it.")
    metadata = load_json(ASSETS / "reference-template.json")
    metadata.update(id=args.slug, title=args.title, platforms=[args.platform])
    metadata["sources"][0]["location"] = source_location(args.source)
    require(nonempty(args.title) and nonempty(args.source), "Title and source must be non-empty.")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()  # Exclusive creation prevents overwriting an existing item.
    contents = {"reference.json": dump_json(metadata), "tokens.json": (ASSETS / "tokens-template.json").read_text(encoding="utf-8"), "DESIGN.md": (ASSETS / "design-template.md").read_text(encoding="utf-8").replace("{{title}}", args.title)}
    for name, content in contents.items():
        with (root / name).open("x", encoding="utf-8") as stream:
            stream.write(content)
    return {"entry": str(root), "status": "draft", "created": list(contents), "next": "Fill rules and tokens, implement preview, record checks, then validate --ready."}


def validate_tokens(document):
    tokens = {}

    def collect(group, prefix="", inherited=None):
        require(isinstance(group, dict), "Token groups must be JSON objects.")
        require("$extends" not in group and "$ref" not in group, "This basic checker supports curly-brace aliases; use a full DTCG validator for $extends/$ref before adapting the checker.")
        kind = group.get("$type", inherited)
        if "$value" in group:
            require(prefix, "A token must have a name.")
            tokens[prefix] = (group["$value"], kind)
            return
        for key, value in group.items():
            if key.startswith("$"):
                continue
            require(not any(character in key for character in ".{}") and bool(key), "Token names cannot contain dots or braces.")
            collect(value, f"{prefix}.{key}" if prefix else key, kind)

    collect(document)

    def references(value):
        if isinstance(value, str):
            match = re.fullmatch(r"\{([^{}]+)\}", value)
            return [match[1]] if match else []
        if isinstance(value, dict):
            require("$ref" not in value, "JSON Pointer references need a full DTCG validator; this checker only resolves curly-brace aliases.")
            return [ref for item in value.values() for ref in references(item)]
        if isinstance(value, list):
            return [ref for item in value for ref in references(item)]
        return []

    resolved = {}

    def visit(name, trail):
        require(name in tokens, f"Missing token alias target: {name}")
        require(name not in trail, f"Circular token alias involving: {name}")
        if name in resolved:
            return resolved[name]
        value, kind = tokens[name]
        refs = references(value)
        target_types = [visit(ref, trail | {name}) for ref in refs]
        whole_alias = isinstance(value, str) and re.fullmatch(r"\{[^{}]+\}", value)
        effective = kind or (target_types[0] if whole_alias else None)
        require(choice(effective, TOKEN_TYPES), f"Token {name} needs a supported $type (direct, inherited, or aliased).")
        if whole_alias and kind:
            require(kind == target_types[0], f"Token alias type mismatch: {name}")
        resolved[name] = effective
        return effective

    for name in tokens:
        visit(name, set())
    return len(tokens)


def validate_entry(root, ready=False, public=False):
    metadata = load_json(safe_path(root, "reference.json", exists=True))
    require(type(metadata.get("schema_version")) is int and metadata["schema_version"] == 1, "Unsupported reference schema_version; expected 1.")
    require(metadata.get("id") == root.name and SLUG.fullmatch(root.name), "Metadata id must match the entry folder.")
    require(nonempty(metadata.get("title")), "Entry title is missing.")
    require(choice(metadata.get("status"), {"draft", "ready"}), "Entry status must be draft or ready.")
    ready = ready or public or metadata["status"] == "ready"
    platforms = metadata.get("platforms")
    require(isinstance(platforms, list) and platforms and all(choice(x, {"web", "mobile", "desktop"}) for x in platforms), "platforms must list web, mobile, or desktop.")
    require(isinstance(metadata.get("tags"), list) and all(nonempty(x) for x in metadata["tags"]), "tags must be an array of non-empty strings.")
    document = safe_path(root, "DESIGN.md", exists=True).read_text(encoding="utf-8")
    count = validate_tokens(load_json(safe_path(root, "tokens.json", exists=True)))
    safe_path(root, metadata.get("preview"), exists=ready)
    if metadata.get("thumbnail"):
        safe_path(root, metadata["thumbnail"], exists=True)
    sources = metadata.get("sources")
    require(isinstance(sources, list) and sources, "At least one source is required.")
    ids = []
    for source in sources:
        require(isinstance(source, dict) and nonempty(source.get("id")) and nonempty(source.get("location")), "Each source needs id and location.")
        source_location(source["location"])
        ids.append(source["id"])
        if ready:
            require(nonempty(source.get("method")), "Record the observation/extraction method for each source.")
        if public:
            require(not source["location"].startswith(("/", "~", "file:")) and not re.match(r"^[A-Za-z]:", source["location"]), "Public source locations cannot expose local filesystem paths.")
    require(len(ids) == len(set(ids)), "Source ids must be unique.")
    evidence = metadata.get("evidence")
    require(isinstance(evidence, list), "evidence must be an array.")
    for fact in evidence:
        require(isinstance(fact, dict) and choice(fact.get("kind"), {"observed", "measured", "inferred", "proposed"}), "Evidence needs an explicit observed/measured/inferred/proposed kind.")
        require(fact.get("source_id") in ids and nonempty(fact.get("locator")) and nonempty(fact.get("finding")), "Evidence needs a known source_id, locator, and finding.")
    checks = metadata.get("verification")
    require(isinstance(checks, dict), "verification must be an object.")
    for name in CHECKS:
        check = checks.get(name)
        require(isinstance(check, dict) and choice(check.get("status"), STATES), f"verification.{name} needs a valid status.")
        require(isinstance(check.get("evidence"), list), f"verification.{name}.evidence must be an array.")
        if check["status"] == "pass":
            require(check["evidence"], f"verification.{name}: pass needs an evidence file.")
        for item in check["evidence"]:
            safe_path(root, item, exists=True)
        if check["status"] == "not-applicable":
            require(nonempty(check.get("reason")), f"verification.{name}: not-applicable needs a reason.")
        if ready:
            allowed = {"pass"} if name in {"new_screen", "visual"} else {"pass", "not-applicable"}
            require(check["status"] in allowed, f"verification.{name} is not ready; perform the check and record evidence.")
    publication = metadata.get("publication")
    require(isinstance(publication, dict) and choice(publication.get("review"), {"pending", "approved", "rejected"}) and choice(publication.get("rights"), {"unreviewed", "cleared", "blocked"}), "publication needs review and rights status.")
    if ready:
        require(count > 0 and evidence, "Ready items need tokens and extraction evidence.")
        require(len(document.strip()) > 0 and "작성 필요" not in document and "{{" not in document, "Complete the DESIGN.md template before marking ready.")
        prototype = metadata.get("prototype")
        require(isinstance(prototype, dict) and all(nonempty(prototype.get(key)) for key in ("stack", "reason", "run")), "Record prototype stack, selection reason, and run instructions.")
    if public:
        require(publication["review"] == "approved" and publication["rights"] == "cleared" and nonempty(publication.get("notes")), "Public catalog requires approved review, cleared rights, and review notes.")
    return metadata, {"id": root.name, "tokens": count, "check": "ready-records" if ready else "draft-structure", "visual_quality": "not-automatically-assessed"}


def catalog(workspace, include_drafts=False, public=False):
    require(not (include_drafts and public), "--public cannot include drafts.")
    directory = workspace / "references"
    items = []
    if not directory.exists():
        return {"schema_version": 1, "items": items}
    for root in sorted(directory.iterdir()):
        if root.name.startswith(".") or not root.is_dir():
            continue
        root = entry_root(workspace, root.name)
        metadata = load_json(safe_path(root, "reference.json", exists=True))
        require(choice(metadata.get("status"), {"draft", "ready"}), f"Invalid entry status: {root.name}")
        if metadata["status"] != "ready" and not include_drafts:
            continue
        publication = metadata.get("publication", {})
        require(isinstance(publication, dict), f"Invalid publication object: {root.name}")
        if public and publication.get("review") != "approved":
            continue
        metadata, _ = validate_entry(root, public=public)
        prefix = f"references/{root.name}/"
        items.append({"id": root.name, "title": metadata["title"], "status": metadata["status"], "platforms": metadata["platforms"], "tags": metadata["tags"], "preview": prefix + quote(metadata["preview"], safe="/"), "design": prefix + "DESIGN.md", "tokens": prefix + "tokens.json", "metadata": prefix + "reference.json", "thumbnail": prefix + quote(metadata["thumbnail"], safe="/") if metadata.get("thumbnail") else ""})
    return {"schema_version": 1, "items": items}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--config", help="Explicit user JSON config, before the subcommand; useful for isolated tests")
    cli.add_argument("--workspace", help="Explicit Git checkout for CI; bypasses user config without modifying it")
    commands = cli.add_subparsers(dest="command", required=True)
    config = commands.add_parser("config", help="Create or explicitly change external user settings")
    actions = config.add_subparsers(dest="action", required=True)
    for name in ("init", "set"):
        action = actions.add_parser(name)
        action.add_argument("--workspace", required=name == "init")
        action.add_argument("--bootstrap-url", help="Credential-free clone/recovery URL; empty string clears it")
        action.add_argument("--remote-name")
    commands.add_parser("doctor", help="Read-only checkout and remote checks; URL values stay redacted")
    create = commands.add_parser("new", help="Create a draft package without fabricating preview or passing evidence")
    create.add_argument("slug")
    create.add_argument("--title", required=True)
    create.add_argument("--source", required=True)
    create.add_argument("--platform", required=True, choices=("web", "mobile", "desktop"))
    validate = commands.add_parser("validate", help="Check package records and basic token references, not visual correctness")
    validate.add_argument("slug")
    validate.add_argument("--ready", action="store_true", help="Require completed verification records and a preview")
    validate.add_argument("--public", action="store_true", help="Also require recorded publication and rights review")
    listing = commands.add_parser("catalog", help="Emit gallery JSON from metadata; does not build HTML or publish")
    listing.add_argument("--include-drafts", action="store_true")
    listing.add_argument("--public", action="store_true")
    setup = commands.add_parser("setup-gallery", help="Plan or explicitly create/connect a GitHub gallery and external config")
    setup.add_argument("--repo", required=True, help="OWNER/REPOSITORY")
    setup.add_argument("--directory", required=True)
    setup.add_argument("--visibility", required=True, choices=("public", "private"))
    setup.add_argument("--apply", action="store_true")
    build = commands.add_parser("build", help="Build only explicitly approved files into a fresh static Pages artifact")
    build.add_argument("--output", required=True)
    build.add_argument("--drafts", action="store_true", help="Local-only preview with an explicit draft label; rejected inside GitHub Actions")
    publish = commands.add_parser("publish", help="Plan or create a reviewed entry PR, then optionally merge and verify Pages")
    publish.add_argument("source", help="Directory of a ready reference package with an explicit public file list")
    publish.add_argument("--apply", action="store_true")
    publish.add_argument("--merge", action="store_true", help="Merge only after the PR build passes; requires authorization")
    publish.add_argument("--timeout", type=int, default=300, help="Seconds allowed for each asynchronous CI/Pages wait")
    finish = commands.add_parser("finish", help="Resume an existing PR without creating a duplicate publication")
    finish.add_argument("--pr", type=int, required=True)
    finish.add_argument("--entry", help="Expected reference id when resuming a PR whose title was changed")
    finish.add_argument("--apply", action="store_true")
    finish.add_argument("--merge", action="store_true")
    finish.add_argument("--timeout", type=int, default=300)
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        path = config_path(args.config)
        if args.command == "config":
            output = configure(args, path)
        elif args.command == "setup-gallery":
            from gallery import setup_gallery
            output = setup_gallery(args, path, sys.modules[__name__])
        else:
            data = normalize_config({"workspace_path": args.workspace, "bootstrap_url": "", "remote_name": "origin"}) if args.workspace else normalize_config(load_json(path))
            workspace, info = workspace_info(data)
            if args.command == "doctor":
                output = {"config": str(path), **info}
                print(dump_json(output), end="")
                return 1 if info["bootstrap_comparison"] == "mismatch-or-unresolved" else 0
            require(info["bootstrap_comparison"] != "mismatch-or-unresolved", "Bootstrap URL and Git remotes differ or cannot be resolved; inspect doctor and Git settings before continuing.")
            if args.command == "new":
                output = new_entry(args, workspace)
            elif args.command == "validate":
                _, output = validate_entry(entry_root(workspace, args.slug), ready=args.ready, public=args.public)
            elif args.command == "catalog":
                output = catalog(workspace, args.include_drafts, args.public)
            else:
                import gallery
                if args.command == "build":
                    output = gallery.build_site(workspace, args.output, sys.modules[__name__], args.drafts)
                elif args.command == "publish":
                    require(args.timeout > 0, "--timeout must be positive.")
                    output = gallery.publish(args, workspace, data, sys.modules[__name__])
                else:
                    require(args.timeout > 0, "--timeout must be positive.")
                    repo = gallery.repo_name(workspace, data["remote_name"], sys.modules[__name__])
                    output = gallery.finish(repo, args.pr, workspace, data["remote_name"], args.merge, args.timeout, sys.modules[__name__], args.entry) if args.apply else {"stage": "plan", "repository": repo, "pr": args.pr, "merge_requested": args.merge}
        print(dump_json(output), end="")
        return 0
    except (UserError, RuntimeError, OSError, UnicodeError) as exc:
        message = str(exc) if isinstance(exc, (UserError, RuntimeError)) else f"Filesystem operation failed ({type(exc).__name__}); check permissions and the selected path."
        print(dump_json({"error": message}), file=sys.stderr, end="")
        return 1


if __name__ == "__main__":
    sys.exit(main())
