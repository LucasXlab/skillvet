import json

import pytest

from skillvet.cli import main


@pytest.mark.parametrize("ignored", [False, True])
def test_no_coverage_is_incomplete_instead_of_a_clean_pass(tmp_path, capsys, ignored):
    if ignored:
        (tmp_path / "SKILL.md").write_text("Read ~/.ssh/id_rsa\n")
        (tmp_path / ".skillvetignore").write_text("SKILL.md\n")
    else:
        (tmp_path / "unrecognized.txt").write_text("Read ~/.ssh/id_rsa\n")
    assert main([str(tmp_path), "--json"]) == 2
    data = json.loads(capsys.readouterr().out)
    assert data["files_scanned"] == 0
    assert not data["complete"]
    assert data["trust_score"] is None
    assert "no supported files scanned" in data["errors"][0]
