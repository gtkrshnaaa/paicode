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
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/paicode"

MODE="install"
DEV=0
FORCE_REMOTE=0
QUIET=0
LOCAL_ROOT=""
SOURCE_DIR=""
TARGET_VENV=""
TEMP_DIR="$(mktemp -d)"
TOTAL_START=$SECONDS
STEP_TOTAL=6
STEP_INDEX=0

if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
  BOLD=$'\033[1m'
  DIM=$'\033[2m'
  RESET=$'\033[0m'
  INTERACTIVE=1
else
  BOLD=""
  DIM=""
  RESET=""
  INTERACTIVE=0
fi

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
  --quiet, -q    Disable the animated spinner. Step lines still print.
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
  rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

phase_bar() {
  local current="$1"
  local total="$2"
  local width=12
  local filled=$((current * width / total))
  local empty=$((width - filled))
  printf '%s%s' \
    "$(printf '%*s' "$filled" '' | tr ' ' '#')" \
    "$(printf '%*s' "$empty" '' | tr ' ' '-')"
}

spinner() {
  local pid="$1"
  local prefix="$2"
  local frames='|/-\'
  local index=0
  local start=$SECONDS
  while kill -0 "$pid" 2>/dev/null; do
    printf '\r%s %s %02ds' "$prefix" "${frames:index:1}" "$((SECONDS - start))"
    index=$(((index + 1) % ${#frames}))
    sleep 0.15
  done
}

fail_step() {
  local log_file="$1"
  printf '\n%sInstallation failed%s\n' "$BOLD" "$RESET" >&2
  printf 'Last 40 lines of the step log:\n' >&2
  tail -n 40 "$log_file" >&2 || true
  mkdir -p "$APP_DIR" 2>/dev/null || true
  cp "$log_file" "$APP_DIR/install.log" 2>/dev/null || true
  printf 'Full log: %s\n' "$APP_DIR/install.log" >&2
  exit 1
}

run_step() {
  local title="$1"
  shift
  STEP_INDEX=$((STEP_INDEX + 1))
  local bar
  bar="$(phase_bar "$STEP_INDEX" "$STEP_TOTAL")"
  local prefix
  prefix="$(printf '[%s] %d/%d %-32s' "$bar" "$STEP_INDEX" "$STEP_TOTAL" "$title")"
  local log_file="$TEMP_DIR/step-${STEP_INDEX}.log"

  if [[ "$INTERACTIVE" != "1" || "$QUIET" == "1" ]]; then
    printf '%s' "$prefix"
    if "$@" >"$log_file" 2>&1; then
      printf ' %s[ok]%s\n' "$BOLD" "$RESET"
    else
      printf ' %s[failed]%s\n' "$BOLD" "$RESET"
      fail_step "$log_file"
    fi
    return 0
  fi

  printf '%s' "$prefix"
  "$@" >"$log_file" 2>&1 &
  local command_pid=$!
  spinner "$command_pid" "$prefix" &
  local spinner_pid=$!
  local status=0
  wait "$command_pid" || status=$?
  kill "$spinner_pid" 2>/dev/null || true
  wait "$spinner_pid" 2>/dev/null || true
  if [[ "$status" -ne 0 ]]; then
    printf '\r%s %s[failed]%s\n' "$prefix" "$BOLD" "$RESET"
    fail_step "$log_file"
  fi
  printf '\r%s %s[ok]%s\n' "$prefix" "$BOLD" "$RESET"
}

step_check() {
  command -v python3 >/dev/null 2>&1 || die "python3 is required."
  if [[ -z "$LOCAL_ROOT" ]] || ! python3 -m pip --version >/dev/null 2>&1; then
    command -v curl >/dev/null 2>&1 || die "curl is required for remote installation or pip bootstrap."
  fi
  if [[ -z "$LOCAL_ROOT" ]]; then
    command -v tar >/dev/null 2>&1 || die "tar is required for remote installation."
  fi
}

step_prepare_source() {
  if [[ -n "$LOCAL_ROOT" ]]; then
    printf '%s\n' "$LOCAL_ROOT" >"$TEMP_DIR/source-dir"
    return 0
  fi

  local source_url
  if [[ -n "$SOURCE_URL_OVERRIDE" ]]; then
    source_url="$SOURCE_URL_OVERRIDE"
  else
    source_url="https://codeload.github.com/$REPO_OWNER/$REPO_NAME/tar.gz/$REF"
  fi

  local archive="$TEMP_DIR/paicode.tar.gz"
  if [[ "$source_url" == https://* ]]; then
    curl --proto '=https' --tlsv1.2 -fsSL "$source_url" -o "$archive"
  else
    curl -fsSL "$source_url" -o "$archive"
  fi
  tar -xzf "$archive" -C "$TEMP_DIR"

  local candidate
  for candidate in "$TEMP_DIR"/*; do
    if [[ -d "$candidate" && -f "$candidate/setup.cfg" ]]; then
      printf '%s\n' "$candidate" >"$TEMP_DIR/source-dir"
      return 0
    fi
  done
  die "Downloaded archive does not contain a Paicode source tree."
}

step_create_environment() {
  create_venv "$TARGET_VENV"
}

step_install_dependencies() {
  "$TARGET_VENV/bin/python" -m pip install --no-cache-dir --upgrade pip setuptools wheel
  "$TARGET_VENV/bin/python" -m pip install --no-cache-dir -r "$SOURCE_DIR/requirements.txt"
  if [[ "$DEV" == "1" ]]; then
    "$TARGET_VENV/bin/python" -m pip install --no-cache-dir -r "$SOURCE_DIR/requirements-dev.txt"
  fi
}

step_install_package() {
  if [[ "$DEV" == "1" ]]; then
    "$TARGET_VENV/bin/python" -m pip install --no-cache-dir --no-deps -e "$SOURCE_DIR"
  else
    "$TARGET_VENV/bin/python" -m pip install --no-cache-dir --no-deps "$SOURCE_DIR"
  fi
}

step_create_launcher() {
  mkdir -p "$BIN_DIR"
  cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$TARGET_VENV/bin/pai" "\$@"
EOF
  chmod 755 "$LAUNCHER"
  "$TARGET_VENV/bin/pai" --version >"$TEMP_DIR/version.txt" 2>&1
}

step_verify() {
  "$TARGET_VENV/bin/pai" --version >"$TEMP_DIR/version.txt" 2>&1
}

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
    --quiet|-q)
      QUIET=1
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

[[ "$DEV" == "0" || "$FORCE_REMOTE" == "0" ]] || die "--dev cannot be combined with --remote or --ref."

if [[ "$MODE" == "uninstall" ]]; then
  printf '\n%sPaicode uninstall%s\n' "$BOLD" "$RESET"
  printf '%s\n' "------------------------------------------------------------"
  rm -f "$LAUNCHER"
  rm -rf "$APP_DIR"
  printf '%-14s %s\n' "Removed" "$LAUNCHER"
  printf '%-14s %s\n' "Removed" "$APP_DIR"
  printf '%-14s %s\n' "Kept" "$CONFIG_DIR"
  printf '%s\n\n' "------------------------------------------------------------"
  exit 0
fi

command -v python3 >/dev/null 2>&1 || die "python3 is required."

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
  TARGET_VENV="$LOCAL_ROOT/.venv"
  SOURCE_DIR="$LOCAL_ROOT"
  STEP_TOTAL=5
  MODE_LABEL="development"
  SOURCE_LABEL="local checkout"
  INSTALL_ROOT="$TARGET_VENV"
  LAUNCHER_LABEL="not installed (dev)"
else
  TARGET_VENV="$VENV"
  STEP_TOTAL=6
  if [[ -n "$LOCAL_ROOT" ]]; then
    MODE_LABEL="install (local)"
    SOURCE_LABEL="local checkout"
  else
    MODE_LABEL="install (remote)"
    if [[ -n "$SOURCE_URL_OVERRIDE" ]]; then
      SOURCE_LABEL="custom archive"
    else
      SOURCE_LABEL="GitHub $REF"
    fi
  fi
  INSTALL_ROOT="$APP_DIR"
  LAUNCHER_LABEL="$LAUNCHER"
fi

PY_VERSION="$(python3 --version 2>&1 | awk '{print $2}')"
PLATFORM="$(uname -srm 2>/dev/null || echo unknown)"

printf '\n%sPaicode installer%s\n' "$BOLD" "$RESET"
printf '%s\n' "------------------------------------------------------------"
printf '%s%-14s%s %s\n' "$DIM" "Mode" "$RESET" "$MODE_LABEL"
printf '%s%-14s%s %s\n' "$DIM" "Platform" "$RESET" "$PLATFORM"
printf '%s%-14s%s %s\n' "$DIM" "Python" "$RESET" "$PY_VERSION"
printf '%s%-14s%s %s\n' "$DIM" "Install root" "$RESET" "$INSTALL_ROOT"
printf '%s%-14s%s %s\n' "$DIM" "Launcher" "$RESET" "$LAUNCHER_LABEL"
printf '%s%-14s%s %s\n' "$DIM" "Source" "$RESET" "$SOURCE_LABEL"
printf '%s\n\n' "------------------------------------------------------------"

run_step "Check prerequisites" step_check
if [[ "$DEV" == "0" ]]; then
  run_step "Prepare source" step_prepare_source
  SOURCE_DIR="$(cat "$TEMP_DIR/source-dir")"
  [[ -n "$SOURCE_DIR" ]] || die "Source directory was not prepared."
fi
run_step "Create environment" step_create_environment
run_step "Install dependencies" step_install_dependencies
run_step "Install Paicode" step_install_package
if [[ "$DEV" == "1" ]]; then
  run_step "Verify environment" step_verify
else
  run_step "Create launcher" step_create_launcher
fi

VERSION="$(cat "$TEMP_DIR/version.txt" 2>/dev/null || echo unknown)"
printf '\n%sInstallation complete%s\n' "$BOLD" "$RESET"
printf '%s\n' "------------------------------------------------------------"
printf '%s%-14s%s %s\n' "$DIM" "Version" "$RESET" "$VERSION"
if [[ "$DEV" == "1" ]]; then
  printf '%s%-14s%s %s\n' "$DIM" "Environment" "$RESET" "$TARGET_VENV"
  printf '%s%-14s%s %s\n' "$DIM" "Run" "$RESET" "$TARGET_VENV/bin/pai"
else
  printf '%s%-14s%s %s\n' "$DIM" "Launcher" "$RESET" "$LAUNCHER"
  printf '%s%-14s%s %s\n' "$DIM" "Config" "$RESET" "$CONFIG_DIR/config.json"
  printf '%s%-14s%s %s\n' "$DIM" "Next" "$RESET" "pai"
fi
printf '%s%-14s%s %s\n' "$DIM" "Elapsed" "$RESET" "$((SECONDS - TOTAL_START))s"
printf '%s\n\n' "------------------------------------------------------------"

if [[ "$DEV" == "0" && ":$PATH:" != *":$BIN_DIR:"* ]]; then
  printf '%sNote:%s Add this to your shell profile:\n' "$BOLD" "$RESET"
  printf '  export PATH="$HOME/.local/bin:$PATH"\n\n'
fi
