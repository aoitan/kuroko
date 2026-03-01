from kuroko.config import ProjectConfig, KurokoConfig

def test_project_config_has_repo():
    p = ProjectConfig(name="test", root="/tmp", repo="owner/repo")
    assert p.repo == "owner/repo"

def test_project_config_repo_optional():
    p = ProjectConfig(name="test", root="/tmp")
    assert p.repo is None

def test_load_config_with_repo(tmp_path):
    config_file = tmp_path / "kuroko.config.yaml"
    config_file.write_text("""
version: 1
projects:
  - name: my-project
    root: /path/to/my-project
    repo: aoitan/kuroko
""")
    from kuroko.config import load_config
    cfg = load_config(str(config_file))
    assert cfg.projects[0].repo == "aoitan/kuroko"
