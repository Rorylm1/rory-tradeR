from pathlib import Path

from src.common import paths


def test_get_data_root_prefers_extracted_lite_when_default_has_no_dataset(tmp_path, monkeypatch):
    default_root = tmp_path / "data"
    default_root.mkdir()
    extracted_root = tmp_path / "runtime" / "quarantine" / "extracted-lite" / "data"
    (extracted_root / "kalshi").mkdir(parents=True)

    monkeypatch.delenv(paths.DATA_ROOT_ENV_VAR, raising=False)
    monkeypatch.setattr(paths, "DEFAULT_DATA_ROOT", default_root)
    monkeypatch.setattr(paths, "EXTRACTED_LITE_DATA_ROOT", extracted_root)

    assert paths.get_data_root() == extracted_root


def test_get_data_root_honors_explicit_env_override(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    configured = repo_root / "custom-data"
    configured.mkdir()

    monkeypatch.setattr(paths, "REPO_ROOT", repo_root)
    monkeypatch.setattr(paths, "DEFAULT_DATA_ROOT", repo_root / "data")
    monkeypatch.setattr(paths, "EXTRACTED_LITE_DATA_ROOT", repo_root / "runtime" / "quarantine" / "extracted-lite" / "data")
    monkeypatch.setenv(paths.DATA_ROOT_ENV_VAR, "custom-data")

    assert paths.get_data_root() == configured.resolve()
