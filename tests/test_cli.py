import json
import os

import pytest
from conftest import FIXTURES

from skillvet.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, main


def test_version(capsys):
    assert main(["--version"]) == EXIT_OK
    assert "skillvet" in capsys.readouterr().out


def test_list_rules(capsys):
    assert main(["--list-rules"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "SV001" in out and "SV041" in out


def test_clean_fixture_exit_ok(capsys):
    assert main([os.path.join(FIXTURES, "clean-skill")]) == EXIT_OK
    out = capsys.readouterr().out
    assert "no findings" in out
    assert "100" in out


def test_malicious_fixture_exit_findings(capsys):
    assert main([os.path.join(FIXTURES, "malicious-skill")]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "SV008" in out
    assert "FAIL" in out


def test_json_output(capsys):
    assert main([os.path.join(FIXTURES, "malicious-skill"), "--json"]) == EXIT_FINDINGS
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "skillvet"
    assert payload["findings"]
    assert payload["counts"]["critical"] >= 1


def test_sarif_output(capsys):
    assert main([os.path.join(FIXTURES, "malicious-skill"), "--sarif"]) == EXIT_FINDINGS
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "2.1.0"
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == "skillvet"
    assert run["results"]
    first = run["results"][0]
    location = first["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"]
    assert location["region"]["startLine"] >= 1
    assert first["ruleId"].startswith("SV")


def test_fail_on_critical_only_passes_medium(tmp_path, capsys):
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text("Read ~/.ssh/id_rsa\n", encoding="utf-8")
    assert main([str(tmp_path), "--fail-on", "critical"]) == EXIT_OK


def test_missing_path_is_usage_error():
    assert main(["/definitely/not/a/directory"]) == EXIT_USAGE


def test_bad_severity_is_usage_error():
    with pytest.raises(SystemExit):
        main(["--min-severity", "bogus"])
