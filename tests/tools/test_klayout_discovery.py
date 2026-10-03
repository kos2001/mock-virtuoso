from toolkit import verification_service as service


def test_local_macos_app_is_discovered(tmp_path, monkeypatch):
    monkeypatch.delenv("KLAYOUT_EXE", raising=False)
    monkeypatch.setattr(service.shutil, "which", lambda _: None)
    monkeypatch.setattr(service, "ROOT", tmp_path)
    binary = tmp_path / ".tools/klayout/klayout.app/Contents/MacOS/klayout"
    binary.parent.mkdir(parents=True)
    binary.touch()
    assert service.find_klayout() == str(binary)


def test_explicit_engine_takes_precedence(monkeypatch):
    monkeypatch.setenv("KLAYOUT_EXE", "/custom/klayout")
    monkeypatch.setattr(service.shutil, "which", lambda _: "/path/klayout")
    assert service.find_klayout() == "/custom/klayout"


def test_path_engine_is_preserved(monkeypatch):
    monkeypatch.delenv("KLAYOUT_EXE", raising=False)
    monkeypatch.setattr(service.shutil, "which", lambda _: "/path/klayout")
    assert service.find_klayout() == "/path/klayout"
