#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="gtkrshnaaa"
REPO_NAME="paicode"
DEFAULT_REF="main"
REF="${PAICODE_REF:-$DEFAULT_REF}"
SOURCE_URL_OVERRIDE="${PAICODE_SOURCE_URL:-}"

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/paicode"
VENV="$APP_DIR/venv"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/pai"

MODE="install"
DEV=0
FORCE_REMOTE=0
LOCAL_ROOT=""
SOURCE_DIR=""
TEMP_DIR=""

usage() {
  cat <<'EOF'
Usage: ./install.sh [OPTIONS]

Install Paicode into ~/.local/bin/pai with an isolated environment in
~/.local/share/paicode/venv. The launcher works from any directory.

Local checkout:
  ./install.sh
  ./install.sh --dev

Remote install:
  curl -fsSL https://raw.githubusercontent.com/gtkrshnaaa/paicode/main/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/gtkrshnaaa/paicode/main/install.sh | bash -s -- --ref <tag>

Options:
  --dev          Prepare the repository .venv and install Paicode in editable mode.
  --remote       Force a source download even when run inside a checkout.
  --ref <ref>    Branch, tag, or commit to download. Default: main.
  --uninstall    Remove the launcher and the isolated environment.
  --help, -h     Show this help.

Environment:
  PAICODE_REF          Default ref for remote installs.
  PAICODE_SOURCE_URL   Override the source archive URL, for mirrors or tests.
EOF
}

log() {
  printf '%s\n' "$*"
}

warn() {
  printf '[!] %s\n' "$*" >&2
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}

trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dev)
      DEV=1
      shift
      ;;
    --remote)
      FORCE_REMOTE=1
      shift
      ;;
    --ref)
      [[ $# -ge 2 && -n "${2:-}" ]] || die "--ref requires a branch, tag, or commit."
      REF="$2"
      FORCE_REMOTE=1
      shift 2
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

[[ "$DEV" == "0" || "$FORCE_REMOTE" == "0" ]] || die "--dev cannot be combined with --remote or --ref."

if [[ "$MODE" == "uninstall" ]]; then
  rm -f "$LAUNCHER"
  rm -rf "$APP_DIR"
  log "Removed $LAUNCHER and $APP_DIR. Provider configuration in ~/.config/paicode was kept."
  exit 0
fi

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
  local source_dir="$3"
  create_venv "$target_venv"
  "$target_venv/bin/python" -m pip install --no-cache-dir --upgrade pip setuptools wheel
  "$target_venv/bin/python" -m pip install --no-cache-dir -r "$source_dir/requirements.txt"
  if [[ "$editable" == "1" ]]; then
    "$target_venv/bin/python" -m pip install --no-cache-dir -r "$source_dir/requirements-dev.txt"
    "$target_venv/bin/python" -m pip install --no-cache-dir --no-deps -e "$source_dir"
  else
    "$target_venv/bin/python" -m pip install --no-cache-dir --no-deps "$source_dir"
  fi
}

if [[ "$FORCE_REMOTE" == "0" ]]; then
  script_path="${BASH_SOURCE[0]:-}"
  if [[ -n "$script_path" && -f "$script_path" ]]; then
    candidate="$(cd "$(dirname "$script_path")" && pwd)"
    if [[ -f "$candidate/setup.cfg" && -d "$candidate/paicode" ]]; then
      LOCAL_ROOT="$candidate"
    fi
  fi
fi

if [[ "$DEV" == "1" ]]; then
  [[ -n "$LOCAL_ROOT" ]] || die "--dev requires a repository checkout."
  install_environment "$LOCAL_ROOT/.venv" 1 "$LOCAL_ROOT"
  log "Development environment ready."
  log "Run: $LOCAL_ROOT/.venv/bin/pai"
  exit 0
fi

if [[ -n "$LOCAL_ROOT" ]]; then
  SOURCE_DIR="$LOCAL_ROOT"
  log "Installing from local checkout: $SOURCE_DIR"
else
  command -v curl >/dev/null 2>&1 || die "curl is required for remote installation."
  command -v tar >/dev/null 2>&1 || die "tar is required for remote installation."

  if [[ -n "$SOURCE_URL_OVERRIDE" ]]; then
    SOURCE_URL="$SOURCE_URL_OVERRIDE"
  else
    SOURCE_URL="https://codeload.github.com/$REPO_OWNER/$REPO_NAME/tar.gz/$REF"
  fi

  TEMP_DIR="$(mktemp -d)"
  ARCHIVE="$TEMP_DIR/paicode.tar.gz"
  log "Downloading Paicode $REF"
  if [[ "$SOURCE_URL" == https://* ]]; then
    curl --proto '=https' --tlsv1.2 -fsSL "$SOURCE_URL" -o "$ARCHIVE"
  else
    curl -fsSL "$SOURCE_URL" -o "$ARCHIVE"
  fi
  tar -xzf "$ARCHIVE" -C "$TEMP_DIR"

  for candidate in "$TEMP_DIR"/*; do
    if [[ -d "$candidate" && -f "$candidate/setup.cfg" ]]; then
      SOURCE_DIR="$candidate"
      break
    fi
  done
  [[ -n "$SOURCE_DIR" ]] || die "Downloaded archive does not contain a Paicode source tree."
fi

install_environment "$VENV" 0 "$SOURCE_DIR"
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/pai" "\$@"
EOF
chmod 755 "$LAUNCHER"

log "Installed $LAUNCHER"
log "Paicode is available as: pai"
if [[ -x "$VENV/bin/pai" ]]; then
  log "Version: $("$VENV/bin/pai" --version)"
fi
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  log "Add this to your shell profile:"
  log "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
