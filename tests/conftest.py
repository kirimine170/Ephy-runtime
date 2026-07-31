import pytest

import packages.config_core.loader as loader_module


@pytest.fixture(autouse=True)
def isolate_local_config_overrides(monkeypatch, tmp_path_factory):
    runtime_root = tmp_path_factory.mktemp("runtime-data")
    monkeypatch.setenv("LOCAL_LLM_WORKBENCH_DISABLE_LOCAL_CONFIG", "1")
    monkeypatch.setenv("LW_DATA_ROOT", str(tmp_path_factory.mktemp("lw-data")))
    monkeypatch.setenv("LOCAL_LLM_WORKBENCH_INDEX_PATH", str(runtime_root / "local_docs.json"))
    loader_module.load_app_config.cache_clear()
    try:
        yield
    finally:
        loader_module.load_app_config.cache_clear()
