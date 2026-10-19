"""Isolated behavioral checks; evidence fixtures do not assert visual quality."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reference-ui.py"


class ReferenceUiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="reference-ui-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "gallery"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.config = self.base / "settings/config.json"
        self.call("config", "init", "--workspace", str(self.repo))

    def call(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), "--config", str(self.config), *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stdout + result.stderr)
        return json.loads(result.stdout if result.stdout else result.stderr)

    def create(self):
        self.call("new", "sample-glass", "--title", "Sample glass", "--source", "https://example.org/ui", "--platform", "desktop")
        return self.repo / "references/sample-glass"

    def save(self, root, name, value):
        (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def ready(self):
        root = self.create()
        self.save(root, "tokens.json", {"space": {"$type": "dimension", "base": {"$value": {"value": 8, "unit": "px"}}, "gap": {"$value": "{space.base}"}}})
        (root / "DESIGN.md").write_text("# Synthetic fixture\nUse space.gap for the gap. This record only tests the validator.\n", encoding="utf-8")
        (root / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Fixture</title><p>Synthetic fixture</p>', encoding="utf-8")
        (root / "verification.md").write_text("Synthetic record used only to exercise file validation, not actual visual QA.\n", encoding="utf-8")
        meta = json.loads((root / "reference.json").read_text())
        meta["sources"][0]["method"] = "synthetic fixture"
        meta["evidence"] = [{"kind": "proposed", "source_id": "source-1", "locator": "fixture", "finding": "Synthetic spacing rule"}]
        meta["prototype"] = {"stack": "HTML", "reason": "Fixture", "run": "Open index.html"}
        for check in meta["verification"].values():
            check.update(status="pass", evidence=["verification.md"])
        self.save(root, "reference.json", meta)
        return root, meta

    def test_config_is_idempotent_and_change_is_explicit(self):
        before = self.config.read_bytes()
        self.assertFalse(self.call("config", "init", "--workspace", str(self.repo))["changed"])
        self.call("config", "init", "--workspace", str(self.base / "other"), ok=False)
        self.assertEqual(self.config.read_bytes(), before)
        self.call("config", "set", "--workspace", str(self.base / "other"))
        self.assertFalse((self.base / "other").exists())
        self.assertIn("does not exist", self.call("doctor", ok=False)["error"])

    def test_bad_json_does_not_fall_back_or_write(self):
        self.config.write_text('{"workspace_path":', encoding="utf-8")
        before = self.config.read_bytes()
        self.assertIn("Invalid JSON", self.call("doctor", ok=False)["error"])
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.repo / "references").exists())

    def test_config_lock_is_not_silently_removed(self):
        lock = self.config.with_name("config.json.lock")
        lock.write_text("owned by another writer")
        self.call("config", "set", "--remote-name", "upstream", ok=False)
        self.assertTrue(lock.exists())

    def test_remote_identity_and_mismatch_do_not_modify_git(self):
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "git@example.org:team/gallery.git"], check=True)
        self.call("config", "set", "--bootstrap-url", "https://example.org/team/gallery.git")
        self.assertEqual(self.call("doctor")["bootstrap_comparison"], "match")
        self.call("config", "set", "--bootstrap-url", "https://example.org/team/another.git")
        self.assertEqual(self.call("doctor", ok=False)["bootstrap_comparison"], "mismatch-or-unresolved")
        self.call("new", "wrong", "--title", "Wrong", "--source", "source", "--platform", "web", ok=False)
        remote = subprocess.check_output(["git", "-C", str(self.repo), "remote", "get-url", "origin"], text=True)
        self.assertEqual(remote.strip(), "git@example.org:team/gallery.git")
        self.assertFalse((self.repo / "references/wrong").exists())

    def test_credentials_are_rejected_without_echo(self):
        output = self.call("config", "set", "--bootstrap-url", "https://user:example-password@example.org/team/gallery", ok=False)
        self.assertNotIn("example-password", json.dumps(output))
        self.assertEqual(json.loads(self.config.read_text())["bootstrap_url"], "")

    def test_new_preserves_existing_item_and_rejects_traversal(self):
        root = self.create()
        original = (root / "reference.json").read_bytes()
        self.call("new", "sample-glass", "--title", "Overwrite", "--source", "source", "--platform", "web", ok=False)
        self.assertEqual((root / "reference.json").read_bytes(), original)
        self.call("new", "../escape", "--title", "Escape", "--source", "source", "--platform", "web", ok=False)
        self.assertFalse((self.repo / "escape").exists())

    def test_source_credentials_rejected_before_creating_entry(self):
        for source in ["https://demo:synthetic-secret@example.org/ui", "https://example.org/ui?access_token=synthetic-secret", "https://example.org/ui#access_token=synthetic-secret"]:
            output = self.call("new", "credential-source", "--title", "Fixture", "--source", source, "--platform", "web", ok=False)
            self.assertNotIn("synthetic-secret", json.dumps(output))
            self.assertFalse((self.repo / "references/credential-source").exists())

    def test_existing_source_credentials_block_public_validation(self):
        root, meta = self.ready()
        meta["sources"][0]["location"] = "https://demo:synthetic-secret@example.org/ui"
        self.save(root, "reference.json", meta)
        output = self.call("validate", "sample-glass", "--public", ok=False)
        self.assertIn("credentials", output["error"])
        self.assertNotIn("synthetic-secret", json.dumps(output))

    def test_draft_is_not_ready_and_not_in_default_catalog(self):
        self.create()
        self.call("validate", "sample-glass")
        self.call("validate", "sample-glass", "--ready", ok=False)
        self.assertEqual(self.call("catalog")["items"], [])
        self.assertEqual(len(self.call("catalog", "--include-drafts")["items"]), 1)

    def test_ready_and_public_are_separate_gates(self):
        root, meta = self.ready()
        self.assertEqual(self.call("validate", "sample-glass", "--ready")["tokens"], 2)
        self.call("validate", "sample-glass", "--public", ok=False)
        meta["status"] = "ready"
        self.save(root, "reference.json", meta)
        self.assertEqual(len(self.call("catalog")["items"]), 1)
        self.assertEqual(self.call("catalog", "--public")["items"], [])
        meta["publication"] = {"review": "approved", "rights": "cleared", "notes": "Synthetic authored fixture"}
        self.save(root, "reference.json", meta)
        item = self.call("catalog", "--public")["items"][0]
        self.assertEqual(item["design"], "references/sample-glass/DESIGN.md")
        self.assertNotIn("sources", item)
        self.call("catalog", "--public", "--include-drafts", ok=False)

    def test_broken_alias_and_cycle_fail_before_valid_graph(self):
        root, _ = self.ready()
        self.save(root, "tokens.json", {"a": {"$type": "number", "$value": "{missing}"}})
        self.assertIn("Missing token", self.call("validate", "sample-glass", ok=False)["error"])
        self.save(root, "tokens.json", {"a": {"$value": "{b}"}, "b": {"$value": "{a}"}})
        self.assertIn("Circular", self.call("validate", "sample-glass", ok=False)["error"])
        self.save(root, "tokens.json", {"a": {"$type": "number", "$value": 1}, "b": {"$value": "{a}"}})
        self.call("validate", "sample-glass", "--ready")

    def test_ready_requires_actual_evidence_file(self):
        root, meta = self.ready()
        meta["verification"]["new_screen"]["evidence"] = ["missing.md"]
        self.save(root, "reference.json", meta)
        self.call("validate", "sample-glass", "--ready", ok=False)
        meta["verification"]["new_screen"] = {"status": "not-applicable", "evidence": [], "reason": "Not tested"}
        self.save(root, "reference.json", meta)
        self.call("validate", "sample-glass", "--ready", ok=False)

    def test_local_and_symlink_preview_escape_rejected(self):
        root, meta = self.ready()
        outside = self.base / "private.html"
        outside.write_text("Private fixture")
        meta["preview"] = "../../private.html"
        self.save(root, "reference.json", meta)
        self.call("validate", "sample-glass", ok=False)
        (root / "linked.html").symlink_to(outside)
        meta["preview"] = "linked.html"
        self.save(root, "reference.json", meta)
        self.call("validate", "sample-glass", ok=False)

    def test_references_symlink_rejected_before_write(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.repo / "references").symlink_to(outside, target_is_directory=True)
        self.call("new", "escape", "--title", "Escape", "--source", "source", "--platform", "web", ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_field_types_return_actionable_json(self):
        root, meta = self.ready()
        meta["platforms"] = [{}]
        self.save(root, "reference.json", meta)
        self.assertIn("platforms", self.call("validate", "sample-glass", ok=False)["error"])
        meta["platforms"] = ["web"]
        meta["verification"]["visual"]["status"] = []
        self.save(root, "reference.json", meta)
        self.assertIn("visual", self.call("validate", "sample-glass", ok=False)["error"])

    def public_ready(self):
        root, meta = self.ready()
        meta["status"] = "ready"
        meta["publication"] = {"review": "approved", "rights": "cleared", "notes": "Synthetic authored fixture", "files": ["DESIGN.md", "tokens.json", "reference.json", "index.html", "verification.md"]}
        self.save(root, "reference.json", meta)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.org", "commit", "--allow-empty", "-qm", "test fixture"], check=True)
        return root, meta

    def test_build_exports_only_reviewed_files_and_rejects_stale_output(self):
        root, meta = self.public_ready()
        (root / "private-notes.txt").write_text("Private fixture, not approved for publication")
        output = self.base / "site"
        self.assertEqual(self.call("build", "--output", str(output))["entries"], ["sample-glass"])
        self.assertFalse((output / "references/sample-glass/private-notes.txt").exists())
        before = (output / "build.json").read_bytes()
        self.call("build", "--output", str(output), ok=False)
        self.assertEqual((output / "build.json").read_bytes(), before)

    def test_repo_gallery_style_is_built_without_modifying_source(self):
        self.public_ready()
        style = self.repo / "gallery.css"
        content = ':root{--g-fg:#123456}\n'
        style.write_text(content)
        output = self.base / "styled"
        self.call("build", "--output", str(output))
        self.assertEqual((output / "gallery.css").read_text(), content)
        self.assertIn('href="gallery.css"', (output / "index.html").read_text())
        self.assertEqual(style.read_text(), content)
        self.assertIn("gallery.css", json.loads((output / "build.json").read_text())["files"])

    def test_gallery_style_rejects_private_paths_missing_assets_and_symlinks(self):
        self.public_ready()
        style = self.repo / "gallery.css"
        style.write_text('body{background:url(file:///private/example)}')
        self.call("build", "--output", str(self.base / "private"), ok=False)
        style.write_text('body{background:url(missing.jpg)}')
        self.call("build", "--output", str(self.base / "missing"), ok=False)
        style.unlink()
        outside = self.base / "external.css"
        outside.write_text('body{color:red}')
        style.symlink_to(outside)
        self.call("build", "--output", str(self.base / "symlink"), ok=False)

    def test_build_requires_explicit_public_file_list(self):
        root, meta = self.public_ready()
        del meta["publication"]["files"]
        self.save(root, "reference.json", meta)
        self.call("build", "--output", str(self.base / "site"), ok=False)
        self.assertFalse((self.base / "site").exists())

    def test_build_blocks_machine_paths_and_broken_links(self):
        root, meta = self.public_ready()
        (root / "DESIGN.md").write_text("Machine file:///private/example")
        self.call("build", "--output", str(self.base / "site"), ok=False)
        (root / "DESIGN.md").write_text("Synthetic design rules")
        (root / "index.html").write_text('<a href="missing.html">Missing</a>')
        self.call("build", "--output", str(self.base / "site"), ok=False)

    def test_build_escapes_catalog_data_and_generates_token_css(self):
        root, meta = self.public_ready()
        meta["title"] = '</script><img id="injected">'
        meta["prototype"]["token_css"] = "assets/tokens.css"
        self.save(root, "reference.json", meta)
        self.save(root, "tokens.json", {"space": {"$type": "dimension", "$value": {"value": 8, "unit": "px"}, "$extensions": {"reference-ui": {"css_name": "--space"}}}})
        (root / "index.html").write_text('<link rel="stylesheet" href="assets/tokens.css"><p>Fixture</p>')
        output = self.base / "site"
        self.call("build", "--output", str(output))
        self.assertIn("--space:8px", (output / "references/sample-glass/assets/tokens.css").read_text())
        self.assertNotIn(meta["title"], (output / "index.html").read_text())

    def test_draft_preview_is_marked_and_forbidden_in_ci(self):
        root, meta = self.public_ready()
        meta["status"] = "draft"
        meta["verification"]["new_screen"] = {"status": "not-run", "evidence": [], "reason": ""}
        meta["publication"]["review"] = "pending"
        self.save(root, "reference.json", meta)
        self.call("build", "--output", str(self.base / "public"), ok=False)
        self.call("build", "--drafts", "--output", str(self.base / "draft"))
        self.assertTrue(json.loads((self.base / "draft/build.json").read_text())["drafts"])
        self.assertIn("DRAFT", (self.base / "draft/index.html").read_text())
        import os
        env = dict(os.environ, GITHUB_ACTIONS="true")
        result = subprocess.run([sys.executable, str(SCRIPT), "--config", str(self.config), "build", "--drafts", "--output", str(self.base / "ci")], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("local-only", result.stderr)
        self.assertFalse((self.base / "ci").exists())

    def test_publish_plan_does_not_mutate_or_contact_remote(self):
        root, _ = self.public_ready()
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "https://github.com/example/reference-fixture.git"], check=True)
        before = subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"])
        result = self.call("publish", str(root), "--merge")
        self.assertEqual(result["stage"], "plan")
        self.assertEqual(before, subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"]))
        self.assertFalse((self.repo / ".reference-ui").exists())

    def test_style_publish_plan_reads_only_explicit_css_without_mutating_checkout(self):
        root, _ = self.public_ready()
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "https://github.com/example/reference-fixture.git"], check=True)
        style = self.base / "theme.css"
        style.write_text(':root{--g-fg:#123456}')
        result = self.call("publish", str(root), "--gallery-style", str(style))
        self.assertEqual(result["gallery_style"], "gallery.css")
        self.assertFalse((self.repo / "gallery.css").exists())
        style.write_text('body{background:url(file:///private/example)}')
        self.call("publish", str(root), "--gallery-style", str(style), ok=False)

    def test_bundled_builder_runs_without_installed_skill_or_user_config(self):
        root, _ = self.public_ready()
        import importlib.util
        spec = importlib.util.spec_from_file_location("reference_ui_test_api", SCRIPT)
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        gallery_spec = importlib.util.spec_from_file_location("reference_ui_test_gallery", ROOT / "scripts/gallery.py")
        gallery = importlib.util.module_from_spec(gallery_spec)
        gallery_spec.loader.exec_module(gallery)
        gallery.install_bundle(self.repo, "main", api)
        result = subprocess.run([sys.executable, str(self.repo / "scripts/gallery.py"), "build", "--output", str(self.base / "standalone")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.base / "standalone/build.json").exists())
        target = self.repo / ".reference-ui/assets/gallery.css"
        target.write_text("User-owned change")
        with self.assertRaises(api.UserError):
            gallery.install_bundle(self.repo, "main", api)
        self.assertEqual(target.read_text(), "User-owned change")

    def bundle_modules(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("project_bundle_api", SCRIPT)
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        spec = importlib.util.spec_from_file_location("project_bundle_gallery", ROOT / "scripts/gallery.py")
        gallery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gallery)
        return api, gallery

    def test_minimal_runtime_check_runs_tests_and_rejects_zero_run(self):
        self.public_ready()
        api, gallery = self.bundle_modules()
        gallery.install_bundle(self.repo, "main", api)
        runner = self.repo / "scripts/gallery.py"
        result = subprocess.run([sys.executable, str(runner), "check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["regressions"]["suite"], "token-contract")
        self.assertGreater(report["regressions"]["tests"], 0)
        self.assertTrue(report["build"]["temporary_output_removed"])
        (self.repo / ".reference-ui/tests/test_token_contract.py").write_text("# Empty damaged test bundle\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(runner), "check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertRegex(result.stderr, "zero tests|NO TESTS RAN")

    def test_exported_skill_and_bundle_share_release_version(self):
        api, gallery = self.bundle_modules()
        gallery.install_bundle(self.repo, "main", api, project_skill=True)
        manifest = json.loads((self.repo / ".reference-ui/bundle.json").read_text())
        skill = (self.repo / ".agents/skills/reference-ui-gallery/SKILL.md").read_text()
        declared = next(line.partition(":")[2].strip().strip('"') for line in skill.splitlines() if line.startswith("  version:"))
        self.assertEqual(manifest["version"], declared)

    def test_project_skill_bundle_runs_after_relocation_without_user_config(self):
        self.public_ready()
        api, gallery = self.bundle_modules()
        gallery.install_bundle(self.repo, "main", api, project_skill=True)
        skill = self.repo / ".agents/skills/reference-ui-gallery"
        self.assertIn("name: reference-ui-gallery\n", (skill / "SKILL.md").read_text())
        for relative in ("README.md", "references/extraction.md", "references/setup.md", "tests/test_reference_ui.py", "assets/config.example.json"):
            self.assertTrue((skill / relative).is_file(), relative)
        self.assertEqual(json.loads((skill / "assets/config.example.json").read_text())["workspace_path"], "")
        import shutil
        moved = self.base / "relocated"
        shutil.copytree(self.repo, moved)
        (moved / ".reference-ui/scripts").rename(self.base / "legacy-runtime")
        self.config.write_text("invalid user config")
        result = subprocess.run([sys.executable, str(moved / "scripts/gallery.py"), "--config", str(self.config), "build", "--output", str(self.base / "portable")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["entries"], ["sample-glass"])

    def test_project_skill_bundle_is_preserved_on_later_publications(self):
        self.public_ready()
        api, gallery = self.bundle_modules()
        gallery.install_bundle(self.repo, "main", api, project_skill=True)
        missing = self.repo / ".agents/skills/reference-ui-gallery/references/extraction.md"
        missing.unlink()
        managed = gallery.install_bundle(self.repo, "main", api)
        self.assertTrue(missing.is_file())
        self.assertIn(".agents/skills/reference-ui-gallery/SKILL.md", managed)
        self.assertEqual(json.loads((self.repo / ".reference-ui/bundle.json").read_text())["project_skill"], "reference-ui-gallery")

    def test_project_skill_local_edits_and_symlinks_block_before_writes(self):
        self.public_ready()
        api, gallery = self.bundle_modules()
        outside = self.base / "outside"
        outside.mkdir()
        (self.repo / ".agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(api.UserError):
            gallery.install_bundle(self.repo, "main", api, project_skill=True)
        self.assertFalse((self.repo / ".reference-ui").exists())
        self.assertEqual(list(outside.iterdir()), [])
        (self.repo / ".agents").unlink()
        gallery.install_bundle(self.repo, "main", api, project_skill=True)
        manifest = (self.repo / ".reference-ui/bundle.json").read_bytes()
        source = self.repo / ".agents/skills/reference-ui-gallery/references/setup.md"
        source.write_text("User-owned instructions")
        with self.assertRaises(api.UserError):
            gallery.install_bundle(self.repo, "main", api)
        self.assertEqual(source.read_text(), "User-owned instructions")
        self.assertEqual((self.repo / ".reference-ui/bundle.json").read_bytes(), manifest)

    def test_project_skill_plan_does_not_write_or_contact_remote(self):
        root, _ = self.public_ready()
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "https://github.com/example/reference-fixture.git"], check=True)
        result = self.call("publish", str(root), "--project-skill")
        self.assertEqual(result["project_skill"], "reference-ui-gallery")
        self.assertFalse((self.repo / ".agents").exists())

    def test_project_exception_keeps_global_installation_separate(self):
        api, _ = self.bundle_modules()
        api.SKILL_ROOT = (self.repo / "skills/shared/reference-ui").resolve()
        api.SKILL_ROOT.mkdir(parents=True)
        (api.SKILL_ROOT / "SKILL.md").write_text("Synthetic skill")
        data = api.normalize_config({"workspace_path": str(self.repo), "bootstrap_url": "", "remote_name": "origin"})
        with self.assertRaisesRegex(api.UserError, "separate"):
            api.workspace_info(data)

    def test_publish_rejects_fully_documented_draft(self):
        root, meta = self.public_ready()
        meta["status"] = "draft"
        self.save(root, "reference.json", meta)
        self.assertIn("status=ready", self.call("publish", str(root), ok=False)["error"])

    def test_bundle_rejects_manifest_and_parent_symlinks_without_writes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("reference_ui_path_api", SCRIPT)
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        spec = importlib.util.spec_from_file_location("reference_ui_path_gallery", ROOT / "scripts/gallery.py")
        gallery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gallery)
        outside = self.base / "outside"
        outside.mkdir()
        original = outside / "settings.json"
        original.write_text('{"keep": true}')
        bundle = self.repo / ".reference-ui"
        bundle.mkdir()
        (bundle / "bundle.json").symlink_to(original)
        with self.assertRaises(api.UserError):
            gallery.install_bundle(self.repo, "main", api)
        self.assertEqual(original.read_text(), '{"keep": true}')
        (bundle / "bundle.json").unlink()
        (self.repo / "scripts").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(api.UserError):
            gallery.install_bundle(self.repo, "main", api)
        self.assertFalse((outside / "gallery.py").exists())
        (self.repo / "references").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(api.UserError):
            gallery.managed_path(self.repo, "references/new-entry", api)
        self.assertFalse((outside / "new-entry").exists())

    def test_failed_command_retains_stdout_diagnostic(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("reference_ui_diagnostic_gallery", ROOT / "scripts/gallery.py")
        gallery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gallery)
        with self.assertRaisesRegex(RuntimeError, "synthetic preflight diagnostic"):
            gallery.command([sys.executable, "-c", "print('synthetic preflight diagnostic'); raise SystemExit(1)"])

    def test_nested_workspace_rejected(self):
        nested = self.repo / "nested"
        nested.mkdir()
        self.call("config", "set", "--workspace", str(nested))
        self.call("doctor", ok=False)


if __name__ == "__main__":
    unittest.main()
