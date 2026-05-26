#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADD_PATH=1
SHELL_RC=""
USER_BIN="$(python3 -c 'import site; print(site.USER_BASE + "/bin")')"
PATH_MARKER="# Added by offline-scripts-cli"
PATH_LINE="export PATH=\"${USER_BIN}:\$PATH\""

detect_shell_rc() {
  local shell_path=""
  if command -v dscl >/dev/null 2>&1 && [[ -n "${USER:-}" ]]; then
    shell_path="$(dscl . -read "/Users/${USER}" UserShell 2>/dev/null | awk '{print $2}')"
  fi
  if [[ -z "${shell_path}" ]]; then
    shell_path="${SHELL:-}"
  fi
  case "$(basename "${shell_path}")" in
    zsh)
      printf '%s\n' "${HOME}/.zshrc"
      ;;
    bash)
      printf '%s\n' "${HOME}/.bashrc"
      ;;
    *)
      printf '%s\n' "${HOME}/.profile"
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  arg="$1"
  case "$arg" in
    --no-path)
      ADD_PATH=0
      shift
      ;;
    --rc-file)
      [[ $# -ge 2 ]] || {
        echo "error: --rc-file requires a path" >&2
        echo "usage: ./install.sh [--no-path] [--rc-file path]" >&2
        exit 2
      }
      SHELL_RC="$2"
      shift 2
      ;;
    *)
      echo "error: unknown option: $arg" >&2
      echo "usage: ./install.sh [--no-path] [--rc-file path]" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${SHELL_RC}" ]]; then
  SHELL_RC="$(detect_shell_rc)"
fi

echo "Installing offline-scripts-cli from ${ROOT_DIR}"
mkdir -p "${USER_BIN}"
python3 -m pip install -e "${ROOT_DIR}" --user --no-build-isolation

if [[ "${ADD_PATH}" -eq 1 ]]; then
  touch "${SHELL_RC}"
  if grep -Fq "${PATH_MARKER}" "${SHELL_RC}"; then
    echo "PATH entry already managed in ${SHELL_RC}"
  elif grep -Fq "${PATH_LINE}" "${SHELL_RC}"; then
    echo "PATH entry already present in ${SHELL_RC}"
  else
    {
      printf '\n%s\n' "${PATH_MARKER}"
      printf '%s\n' "${PATH_LINE}"
    } >> "${SHELL_RC}"
    echo "Added ${USER_BIN} to PATH in ${SHELL_RC}"
  fi
fi

echo "Installed commands in ${USER_BIN}"
echo "Open a new shell or run: source ${SHELL_RC}"
