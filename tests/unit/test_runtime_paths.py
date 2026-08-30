from pathlib import Path

from scholarai.infrastructure.config.settings import _find_project_root


def test_find_project_root_prefers_runtime_working_directory(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'runtime-test'\n")
    (tmp_path / "data").mkdir()

    assert _find_project_root(tmp_path) == tmp_path
