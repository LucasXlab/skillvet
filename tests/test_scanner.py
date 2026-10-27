import os

from conftest import FIXTURES

from skillvet.model import Severity
from skillvet.scanner import Scanner


def test_clean_fixture_has_no_findings():
    result = Scanner(os.path.join(FIXTURES, "clean-skill")).scan()
    assert result.findings == []
    assert result.files_scanned == 1
    assert result.trust_score() == 100


def test_malicious_fixture_triggers_expected_rules():
    result = Scanner(os.path.join(FIXTURES, "malicious-skill")).scan()
    found = {f.rule_id for f in result.findings}
    expected = {
        "SV001",
        "SV002",
        "SV004",
        "SV005",
        "SV006",
        "SV007",
        "SV008",
        "SV020",
        "SV021",
        "SV022",
        "SV023",
        "SV030",
        "SV031",
        "SV041",
    }
    assert expected <= found, f"missing: {expected - found}"
    assert result.max_severity() == Severity.CRITICAL
    assert result.trust_score() < 20


def test_findings_sorted_by_severity():
    result = Scanner(os.path.join(FIXTURES, "malicious-skill")).scan()
    severities = [f.severity for f in result.findings]
    assert severities == sorted(severities, reverse=True)


def test_min_severity_filter():
    result = Scanner(os.path.join(FIXTURES, "malicious-skill"), min_severity=Severity.HIGH).scan()
    assert all(f.severity >= Severity.HIGH for f in result.findings)
    assert any(f.severity == Severity.CRITICAL for f in result.findings)


def test_inline_suppression(tmp_path):
    skill = tmp_path / "s"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "Read ~/.ssh/id_rsa here <!-- skillvet:ignore SV006 -->\n",
        encoding="utf-8",
    )
    result = Scanner(str(tmp_path)).scan()
    assert "SV006" not in {f.rule_id for f in result.findings}


def test_skillvetignore_file(tmp_path):
    skill = tmp_path / "skills" / "a"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Read ~/.ssh/id_rsa\n", encoding="utf-8")
    (tmp_path / ".skillvetignore").write_text("skills/a/*\n", encoding="utf-8")
    result = Scanner(str(tmp_path)).scan()
    assert result.files_scanned == 0


def test_extra_ignore_glob(tmp_path):
    skill = tmp_path / "skills" / "a"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("Read ~/.ssh/id_rsa\n", encoding="utf-8")
    result = Scanner(str(tmp_path), extra_ignores=["**/SKILL.md"]).scan()
    assert result.findings == []


def test_result_dict_shape():
    result = Scanner(os.path.join(FIXTURES, "malicious-skill")).scan()
    data = result.to_dict()
    assert data["tool"] == "skillvet"
    assert data["trust_score"] == result.trust_score()
    assert set(data["counts"]) == {"info", "low", "medium", "high", "critical"}
    assert all({"rule_id", "severity", "path", "line"} <= set(f) for f in data["findings"])
