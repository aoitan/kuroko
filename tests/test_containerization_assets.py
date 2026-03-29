from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_containerization_files_exist():
    assert (REPO_ROOT / "Dockerfile.dev").exists()
    assert (REPO_ROOT / "Dockerfile").exists()
    assert (REPO_ROOT / "compose.yaml").exists()
    assert (REPO_ROOT / ".dockerignore").exists()


def test_compose_supports_disposable_worktree_flow():
    compose_path = REPO_ROOT / "compose.yaml"
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    assert "services" in data
    assert "volumes" in data

    dev = data["services"]["dev"]
    app = data["services"]["app"]
    kanpe = data["services"]["kanpe"]

    assert dev["working_dir"] == "/workspace"
    assert app["working_dir"] == "/workspace"
    assert kanpe["working_dir"] == "/workspace"

    workspace_mounts = {".:/workspace", "./.data:/workspace/.data"}
    for service in (dev, app, kanpe):
        assert workspace_mounts.issubset(set(service["volumes"]))
        assert service["user"] == "${UID:-1000}:${GID:-1000}"
        assert service["environment"]["UV_PROJECT_ENVIRONMENT"] == "/var/cache/uv/project-env"

    assert app["entrypoint"] == ["uv", "run", "--directory", "/workspace"]
    assert kanpe["entrypoint"] == ["uv", "run", "--directory", "/workspace"]
    assert kanpe["command"][:2] == ["kanpe", "view"]
    assert "--host" in kanpe["command"]
    assert "0.0.0.0" in kanpe["command"]
    assert kanpe["ports"] == ["127.0.0.1:8765:8765"]
    assert "uv-cache" in data["volumes"]


def test_dockerignore_excludes_local_artifacts():
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")

    for entry in (".git", ".venv", ".pytest_cache", "__pycache__", ".data", "checkpoint/*.md"):
        assert entry in dockerignore


def test_readme_documents_container_workflow():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docker compose run --rm dev uv run pytest" in readme
    assert "docker compose run --rm app kuroko --config /workspace/.data/config.yaml collect memo" in readme
    assert "docker compose up kanpe" in readme
    assert "/workspace" in readme
    assert ".data/config.yaml" in readme
    assert "壊れたらコンテナを破棄して再作成" in readme
    assert "docker compose down -v" in readme
