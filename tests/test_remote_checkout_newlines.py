import subprocess

from patchloop import repository


def test_remote_checkout_preserves_lf_with_text_auto_and_crlf_host(tmp_path, monkeypatch):
    config = tmp_path / "global.gitconfig"
    config.write_text("[core]\n eol = crlf\n autocrlf = false\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    origin = tmp_path / "origin"
    origin.mkdir()

    def git(path, *args):
        return subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git(origin, "init", "--quiet")
    git(origin, "config", "user.email", "fixture@example.invalid")
    git(origin, "config", "user.name", "Fixture")
    (origin / ".gitattributes").write_bytes(b"* text=auto\n")
    (origin / "module.py").write_bytes(b"value = 1\nother = 2\n")
    git(origin, "add", "--all")
    git(origin, "commit", "--quiet", "-m", "Fixture")
    commit = git(origin, "rev-parse", "HEAD")
    url = origin.as_posix()
    monkeypatch.setattr(repository, "ALLOWED_REMOTE_REPOSITORIES", {url})
    manager = repository.WorkspaceManager(tmp_path / "fixtures", tmp_path / "workspaces")
    checkout = manager.create("source", url, commit)
    assert (checkout / "module.py").read_bytes() == b"value = 1\nother = 2\n"
    assert git(checkout, "status", "--porcelain") == ""
