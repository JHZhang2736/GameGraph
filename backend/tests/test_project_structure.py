from pathlib import Path


def test_backend_package_structure_exists() -> None:
    backend_root = Path(__file__).resolve().parents[1]

    assert (backend_root / "app").is_dir()
    assert (backend_root / "app" / "schemas").is_dir()
    assert (backend_root / "app" / "services").is_dir()
