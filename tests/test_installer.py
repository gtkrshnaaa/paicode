import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"


def test_installer_help_documents_remote_and_local_modes():
    result = subprocess.run(
        ["bash", str(INSTALLER), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "curl -fsSL" in result.stdout
    assert "--remote" in result.stdout
    assert "--ref" in result.stdout
    assert "--dev" in result.stdout
    assert "--quiet" in result.stdout
    assert "PAICODE_SHA256" in result.stdout


def test_installer_contains_no_credentials():
    text = INSTALLER.read_text(encoding="utf-8")
    assert "sk-" not in text
    assert "DEEPSEEK_API_KEY" not in text
