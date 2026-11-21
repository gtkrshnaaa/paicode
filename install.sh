#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/paicode"
VENV="$APP_DIR/venv"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/pai"
MODE="install"
DEV=0

usage() {
  cat <<'EOF'
Usage: ./install.sh [OPTIONS]

Install Paicode into ~/.local/bin/pai with an isolated environment in
~/.local/share/paicode/venv. The launcher works from any directory.

Options:
  --dev          Prepare the repository .venv and install Paicode in editable mode.
  --uninstall    Remove the launcher and the isolated environment.
  --help, -h     Show this help.
EOF
}

log() {
  printf '%s\n' "$*"
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev)
      DEV=1
      shift
      ;;
    --uninstall)
      MODE="uninstall"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die "python3 is required."

bootstrap_pip() {
  local target_venv="$1"
  command -v curl >/dev/null 2>&1 || die "curl is required to bootstrap pip."
  local script
  script="$(mktemp)"
  log "Bootstrapping pip for $target_venv"
  curl --proto '=https' --tlsv1.2 -fsSL https://bootstrap.pypa.io/get-pip.py -o "$script"
  "$target_venv/bin/python" "$script" --no-cache-dir
  rm -f "$script"
}

create_venv() {
  local target_venv="$1"
  if [[ -x "$target_venv/bin/python" ]] && "$target_venv/bin/python" -m pip --version >/dev/null 2>&1; then
    return
  fi
  mkdir -p "$(dirname "$target_venv")"
  if ! python3 -m venv "$target_venv" >/dev/null 2>&1; then
    python3 -m venv --without-pip "$target_venv"
    bootstrap_pip "$target_venv"
  fi
  if ! "$target_venv/bin/python" -m pip --version >/dev/null 2>&1; then
    bootstrap_pip "$target_venv"
  fi
}

install_environment() {
  local target_venv="$1"
  local editable="$2"
  create_venv "$target_venv"
  "$target_venv/bin/python" -m pip install --no-cache-dir --upgrade pip setuptools wheel
  "$target_venv/bin/python" -m pip install --no-cache-dir -r "$ROOT/requirements.txt"
  if [[ "$editable" == "1" ]]; then
    "$target_venv/bin/python" -m pip install --no-cache-dir -r "$ROOT/requirements-dev.txt"
    "$target_venv/bin/python" -m pip install --no-cache-dir --no-deps -e "$ROOT"
  else
    "$target_venv/bin/python" -m pip install --no-cache-dir --no-deps "$ROOT"
  fi
}

if [[ "$MODE" == "uninstall" ]]; then
  rm -f "$LAUNCHER"
  rm -rf "$APP_DIR"
  log "Removed $LAUNCHER and $APP_DIR. Provider configuration in ~/.config/paicode was kept."
  exit 0
fi

if [[ "$DEV" == "1" ]]; then
  install_environment "$ROOT/.venv" 1
  log "Development environment ready."
  log "Run: $ROOT/.venv/bin/pai"
  exit 0
fi

install_environment "$VENV" 0
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/pai" "\$@"
EOF
chmod 755 "$LAUNCHER"

log "Installed $LAUNCHER"
log "Paicode is available as: pai"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  log "Add this to your shell profile:"
  log "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
