import os

from conftest import FIXTURES

from skillvet.discovery import classify, discover


def test_classify_instruction_files():
    root = "/repo"
    assert classify(root, "/repo/SKILL.md") == "instruction"
    assert classify(root, "/repo/CLAUDE.md") == "instruction"
    assert classify(root, "/repo/AGENTS.md") == "instruction"
    assert classify(root, "/repo/.cursorrules") == "instruction"
    assert classify(root, "/repo/my-skill/skills/foo.md") == "instruction"


def test_classify_configs_and_scripts():
    root = "/repo"
    assert classify(root, "/repo/.mcp.json") == "mcp-config"
    assert classify(root, "/repo/.claude/settings.json") == "hook-config"
    assert classify(root, "/repo/hooks/hooks.json") == "hook-config"
    assert classify(root, "/repo/.claude-plugin/plugin.json") == "manifest"
    assert classify(root, "/repo/skills/foo/scripts/run.sh") == "script"
    assert classify(root, "/repo/skills/foo/scripts/deploy.py") == "script"


def test_classify_unrelated_files():
    root = "/repo"
    assert classify(root, "/repo/main.py") is None
    assert classify(root, "/repo/README.md") is None
    assert classify(root, "/repo/docs/guide.md") is None


def test_discover_skips_vendor_dirs(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello", encoding="utf-8")
    vendor = tmp_path / "node_modules" / "pkg"
    vendor.mkdir(parents=True)
    (vendor / "SKILL.md").write_text("should be skipped", encoding="utf-8")

    found = discover(str(tmp_path))
    rels = sorted(f.relpath for f in found)
    assert rels == ["SKILL.md"]


def test_discover_finds_clean_fixture():
    found = discover(os.path.join(FIXTURES, "clean-skill"))
    # LICENSE is not an agent-related file type; only SKILL.md is scanned
    assert [f.relpath for f in found] == ["SKILL.md"]
    assert found[-1].kind == "instruction"
