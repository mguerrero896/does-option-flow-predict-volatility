#!/usr/bin/env bash
# shellcheck disable=SC2016 # PowerShell, jq, and awk programs are intentionally literal.
set -Eeuo pipefail
IFS=$'\n\t'

die() {
  printf 'VIDEO_SCRIPT_FAILED: %s\n' "$*" >&2
  exit 1
}

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

[[ -n ${WT_SESSION:-} ]] || die "RUN_INSIDE_WINDOWS_TERMINAL"
[[ -z $(git status --porcelain=v1 --untracked-files=all) ]] || die "WORKTREE_NOT_CLEAN"
git merge-base --is-ancestor 506f61b9dc85b3fc2cc721986bbbd2fc4db4f27a HEAD ||
  die "README_FIX_PR57_NOT_IN_HEAD"
[[ $(git config --get core.hooksPath) == scripts/hooks ]] ||
  die "VERSIONED_HOOK_NOT_ACTIVE"

for command in ffmpeg ffprobe wt.exe bat jq uv git gh rg awk sha256sum pwsh.exe cygpath; do
  command -v "$command" >/dev/null || die "COMMAND_MISSING:$command"
done
pwsh.exe -NoLogo -NoProfile -NonInteractive -Command \
  'if (Get-Process LogonUI -ErrorAction SilentlyContinue) { exit 1 }' ||
  die "WINDOWS_SESSION_LOCKED"

EDGE_EXE='/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
[[ -x $EDGE_EXE ]] || die "MICROSOFT_EDGE_NOT_FOUND"

OUTPUT_DIR=${VIDEO_OUTPUT_DIR:-"$(cd "$ROOT/.." && pwd)/MDS650-progress-video"}
mkdir -p "$OUTPUT_DIR"
VIDEO="$OUTPUT_DIR/VIDEO.mp4"
CH="$OUTPUT_DIR/VIDEO.chapters"
GATE_LOG="$OUTPUT_DIR/local-evidence-gates.log"
STATE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mds650-video.XXXXXX")
: >"$CH"
: >"$GATE_LOG"

T0_MS=0
CODE_ZOOM_ACTIVE=0
now_ms() { date +%s%3N; }

mark() {
  local kind=$1 label=$2 elapsed
  elapsed=$(( $(now_ms) - T0_MS ))
  label=${label//$'\t'/ }
  label=${label//$'\n'/ }
  printf '%d\t%s\t%s\n' "$elapsed" "$kind" "$label" >>"$CH"
}

type_command() {
  local value=$1 i
  printf '\033[1;32m$ \033[0m'
  for ((i = 0; i < ${#value}; i++)); do
    printf '%s' "${value:i:1}"
    sleep 0.01
  done
  printf '\n'
}

run() {
  local shown=$1
  shift
  printf '\033[2J\033[H'
  type_command "$shown"
  "$@"
  mark CMD "$shown"
  sleep 6
}

run_shell() {
  local command=$1
  run "$command" bash -o pipefail -c "$command"
}

FAIL_NO=0
expect_fail() {
  local needle=$1 shown=$2 rc log
  shift 2
  log="$STATE_DIR/expected-$((++FAIL_NO)).log"
  printf '\033[2J\033[H'
  type_command "$shown"
  set +e
  "$@" >"$log" 2>&1
  rc=$?
  set -e
  ((rc != 0)) || die "EXPECTED_FAILURE_DID_NOT_FAIL:$shown"
  grep -Fq -- "$needle" "$log" || die "EXPECTED_FAILURE_WRONG_REASON:$needle"
  printf '\033[2J\033[H'
  printf '\033[1;33m# DELIBERATELY INJECTED FAULT\033[0m\n\n'
  printf 'COMMAND: %s\n' "$shown"
  printf 'EXPECTED_REASON_MATCHED: %s\n' "$needle"
  printf '\033[1;33mEXPECTED_FAILURE_VERIFIED (exit %d)\033[0m\n' "$rc"
  mark CMD "$shown"
  sleep 6
}

act() {
  local number=$1 title=$2
  printf '\033[2J\033[H'
  printf '\n\033[1;33m════════════════════════════════════════════════════════════\n'
  printf '  ACT %s · %s\n' "$number" "$title"
  printf '════════════════════════════════════════════════════════════\033[0m\n\n'
  mark ACT "$number | $title"
  sleep 4
}

say() {
  printf '\n\033[1;36m# %s\033[0m\n' "$1"
  mark SAY "$1"
  sleep 4
}

terminal_code_zoom_on() {
  pwsh.exe -NoLogo -NoProfile -NonInteractive -Command '
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait("^0")
    1..6 | ForEach-Object { [System.Windows.Forms.SendKeys]::SendWait("^{ADD}") }
  '
  CODE_ZOOM_ACTIVE=1
}

terminal_code_zoom_off() {
  ((CODE_ZOOM_ACTIVE)) || return 0
  pwsh.exe -NoLogo -NoProfile -NonInteractive -Command '
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait("^0")
  '
  CODE_ZOOM_ACTIVE=0
}

symbol_bounds() {
  local file=$1 symbol=$2 bounds
  bounds=$(uv run python -c '
import ast
import sys
from pathlib import Path

tree = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
matches = [
    node
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name == sys.argv[2]
]
if len(matches) != 1:
    raise SystemExit(2)
node = matches[0]
print(f"{node.lineno}:{node.end_lineno}")
' "$file" "$symbol") || die "FUNCTION_NOT_FOUND:$symbol"
  printf '%s\n' "$bounds"
}

show_code() {
  local file=$1 start=$2 end=$3 label=$4 page_start page_end page pages
  [[ -f $file ]] || die "CODE_FILE_NOT_FOUND:$file"
  [[ $start =~ ^[0-9]+$ && $end =~ ^[0-9]+$ && $start -le $end ]] ||
    die "CODE_RANGE_INVALID:$file:$start:$end"
  pages=$(( (end - start + 18) / 18 ))
  page=0
  terminal_code_zoom_on
  for ((page_start = start; page_start <= end; page_start += 18)); do
    page=$((page + 1))
    page_end=$((page_start + 17))
    ((page_end <= end)) || page_end=$end
    printf '\033[2J\033[H'
    printf '\033[1;35m# CODE · %s · %s:%d-%d · page %d/%d\033[0m\n\n' \
      "$label" "$file" "$page_start" "$page_end" "$page" "$pages"
    type_command "bat --line-range ${page_start}:${page_end} $file"
    bat --color=always --style=numbers --paging=never \
      --line-range "${page_start}:${page_end}" "$file"
    mark CODE "$label | $file:$page_start-$page_end | page $page/$pages"
    sleep 5
  done
  terminal_code_zoom_off
}

show_def() {
  local file=$1 symbol=$2 bounds start end
  bounds=$(symbol_bounds "$file" "$symbol")
  IFS=: read -r start end <<<"$bounds"
  show_code "$file" "$start" "$end" "complete function $symbol"
}

show_range() {
  show_code "$1" "$2" "$3" "critical excerpt: $4"
}

verify_sha256() {
  local expected=$1 file=$2 actual
  actual=$(sha256sum "$file" | awk '{print $1}')
  [[ $actual == "$expected" ]] || die "SHA256_MISMATCH:$file"
  printf 'SHA256_MATCH  %s  %s\n' "$actual" "$file"
}

close_edge_profile() {
  local profile=$1
  VIDEO_EDGE_PROFILE="$profile" pwsh.exe -NoLogo -NoProfile -NonInteractive -Command '
      function Get-ProfileProcesses {
        @(Get-CimInstance Win32_Process |
          Where-Object {
            $_.Name -eq "msedge.exe" -and $_.CommandLine -and
            $_.CommandLine.Contains($env:VIDEO_EDGE_PROFILE)
          } |
          ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue })
      }
      Get-ProfileProcesses |
        Where-Object MainWindowHandle -ne 0 |
        ForEach-Object { [void] $_.CloseMainWindow() }
      $deadline = (Get-Date).AddSeconds(10)
      while ((Get-ProfileProcesses).Count -gt 0 -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 200
      }
      if ((Get-ProfileProcesses).Count -gt 0) {
        throw "EDGE_FIGURE_CLOSE_TIMEOUT"
      }
      if (Test-Path -LiteralPath $env:VIDEO_EDGE_PROFILE) {
        Remove-Item -LiteralPath $env:VIDEO_EDGE_PROFILE -Recurse -Force -ErrorAction Stop
      }
    '
}

VISUAL_NO=0
ACTIVE_EDGE_PROFILE=''
show_svg() {
  local file=$1 title=$2 profile marker wrapper
  [[ -f $file ]] || die "FIGURE_NOT_FOUND:$file"
  VISUAL_NO=$((VISUAL_NO + 1))
  profile=$(cygpath -aw "$STATE_DIR/edge-$VISUAL_NO")
  ACTIVE_EDGE_PROFILE=$profile
  marker=$(cygpath -aw "$STATE_DIR/edge-$VISUAL_NO.open")
  wrapper=$(cygpath -aw "$STATE_DIR/edge-$VISUAL_NO.html")
  printf '\n\033[1;35m# FIGURE · %s\033[0m\n' "$title"
  VIDEO_EDGE_EXE=$(cygpath -aw "$EDGE_EXE") \
  VIDEO_SVG=$(cygpath -aw "$file") \
  VIDEO_EDGE_PROFILE="$profile" \
  VIDEO_EDGE_MARKER="$marker" \
  VIDEO_EDGE_WRAPPER="$wrapper" \
    pwsh.exe -NoLogo -NoProfile -NonInteractive -Command '
      function Get-ProfileProcesses {
        Get-CimInstance Win32_Process |
          Where-Object {
            $_.Name -eq "msedge.exe" -and $_.CommandLine -and
            $_.CommandLine.Contains($env:VIDEO_EDGE_PROFILE)
          } |
          ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
      }
      $svgUrl = "file:///" + ($env:VIDEO_SVG -replace "\\", "/")
      $wrapperUrl = "file:///" + ($env:VIDEO_EDGE_WRAPPER -replace "\\", "/")
      $escapedSvgUrl = [Net.WebUtility]::HtmlEncode($svgUrl)
      $html = @"
<!doctype html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: white; }
img { display: block; width: 100vw; height: 100vh; object-fit: contain; }
</style></head><body><img src="$escapedSvgUrl" alt=""></body></html>
"@
      [IO.File]::WriteAllText(
        $env:VIDEO_EDGE_WRAPPER,
        $html,
        [Text.UTF8Encoding]::new($false)
      )
      $args = @(
        "--user-data-dir=$($env:VIDEO_EDGE_PROFILE)",
        "--app=$wrapperUrl",
        "--guest",
        "--disable-sync",
        "--no-default-browser-check",
        "--lang=en-US",
        "--window-position=3840,0",
        "--window-size=2560,1440",
        "--no-first-run",
        "--disable-background-mode",
        "--disable-features=msEdgeFirstRunExperience"
      )
      try {
        Start-Process -FilePath $env:VIDEO_EDGE_EXE -ArgumentList $args | Out-Null
        $deadline = (Get-Date).AddSeconds(10)
        do {
          $window = Get-ProfileProcesses |
            Where-Object MainWindowHandle -ne 0 |
            Select-Object -First 1
          if (-not $window) { Start-Sleep -Milliseconds 200 }
        } until ($window -or (Get-Date) -ge $deadline)
        if (-not $window) { throw "EDGE_FIGURE_WINDOW_NOT_FOUND" }
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class VideoEdgeWindow {
  public const uint SWP_NOACTIVATE = 0x0010;
  public const uint SWP_SHOWWINDOW = 0x0040;
  [StructLayout(LayoutKind.Sequential)] public struct RECT {
    public int Left, Top, Right, Bottom;
  }
  [StructLayout(LayoutKind.Sequential)] public struct MONITORINFO {
    public int cbSize;
    public RECT rcMonitor, rcWork;
    public uint dwFlags;
  }
  [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int value);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int width, int height, uint flags);
  [DllImport("user32.dll", EntryPoint="GetWindowLongW")] public static extern int GetWindowLong(IntPtr hWnd, int index);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr hWnd, uint flags);
  [DllImport("user32.dll")] public static extern bool GetMonitorInfo(IntPtr monitor, ref MONITORINFO info);
  [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr hWnd);
}
"@
        try { [void] [VideoEdgeWindow]::SetProcessDpiAwareness(2) } catch {}
        $handle = [IntPtr] $window.MainWindowHandle
        [void] [VideoEdgeWindow]::ShowWindow($handle, 9)
        Start-Sleep -Milliseconds 200
        $noActivateAndShow = [VideoEdgeWindow]::SWP_NOACTIVATE -bor [VideoEdgeWindow]::SWP_SHOWWINDOW
        if (-not [VideoEdgeWindow]::SetWindowPos($handle, [IntPtr](-1), 3840, 0, 2560, 1440, $noActivateAndShow)) {
          throw "EDGE_FIGURE_POSITION_FAILED"
        }
        Start-Sleep -Milliseconds 200
        [void] [VideoEdgeWindow]::ShowWindow($handle, 3)
        if (-not [VideoEdgeWindow]::SetWindowPos($handle, [IntPtr](-1), 0, 0, 0, 0, ($noActivateAndShow -bor 0x0003))) {
          throw "EDGE_FIGURE_TOPMOST_FAILED"
        }
        if (([VideoEdgeWindow]::GetWindowLong($handle, -20) -band 0x00000008) -eq 0) {
          throw "EDGE_FIGURE_TOPMOST_NOT_VERIFIED"
        }
        $geometryOk = $false
        $deadline = (Get-Date).AddSeconds(5)
        do {
          $monitor = [VideoEdgeWindow]::MonitorFromWindow($handle, 0)
          if ($monitor -ne [IntPtr]::Zero) {
            $info = [VideoEdgeWindow+MONITORINFO]::new()
            $info.cbSize = [Runtime.InteropServices.Marshal]::SizeOf($info)
            if ([VideoEdgeWindow]::GetMonitorInfo($monitor, [ref] $info)) {
              $rect = $info.rcMonitor
              $geometryOk = [VideoEdgeWindow]::IsZoomed($handle) -and
                $rect.Left -eq 3840 -and $rect.Top -eq 0 -and
                $rect.Right -eq 6400 -and $rect.Bottom -eq 1440
            }
          }
          if (-not $geometryOk) { Start-Sleep -Milliseconds 100 }
        } until ($geometryOk -or (Get-Date) -ge $deadline)
        if (-not $geometryOk) { throw "EDGE_FIGURE_GEOMETRY_NOT_VERIFIED" }
        [IO.File]::WriteAllText(
          $env:VIDEO_EDGE_MARKER,
          "OPEN`tmonitor=3840,0,6400,1440`tmaximized=true`ttopmost=true`tfit=contain"
        )
      } catch {
        $failure = $_
        Get-ProfileProcesses |
          Where-Object MainWindowHandle -ne 0 |
          ForEach-Object { [void] $_.CloseMainWindow() }
        $deadline = (Get-Date).AddSeconds(10)
        while ((Get-ProfileProcesses).Count -gt 0 -and (Get-Date) -lt $deadline) {
          Start-Sleep -Milliseconds 200
        }
        if ((Get-ProfileProcesses).Count -gt 0) {
          throw "EDGE_FIGURE_OPEN_CLEANUP_TIMEOUT:$failure"
        }
        throw $failure
      }
    '
  [[ -s $(cygpath -au "$marker") ]] || die "EDGE_FIGURE_WINDOW_NOT_FOUND"
  sleep 8
  mark VISUAL "$file"
  sleep 10
  close_edge_profile "$profile"
  ACTIVE_EDGE_PROFILE=''
  sleep 2
}

FROZEN='artifacts/gate1_inference/results.json'
README='README.md'
FREEZE='artifacts/target_blind_v22/successor_method_freeze_v1.json'
DEMO_FILES=("$FROZEN" "$README" "$FREEZE")
BACKUPS=()
ATTRS=()
HASHES=()
DIRTY=(0 0 0)

get_attrs() {
  VIDEO_FILE_PATH=$(cygpath -aw "$1") pwsh.exe -NoLogo -NoProfile -NonInteractive \
    -Command '[int][IO.File]::GetAttributes($env:VIDEO_FILE_PATH)'
}

set_attrs() {
  VIDEO_FILE_PATH=$(cygpath -aw "$1") VIDEO_FILE_ATTRS=$2 \
    pwsh.exe -NoLogo -NoProfile -NonInteractive -Command \
    '[IO.File]::SetAttributes($env:VIDEO_FILE_PATH, [IO.FileAttributes][int]$env:VIDEO_FILE_ATTRS)'
}

clear_attrs() {
  VIDEO_FILE_PATH=$(cygpath -aw "$1") pwsh.exe -NoLogo -NoProfile -NonInteractive \
    -Command '[IO.File]::SetAttributes($env:VIDEO_FILE_PATH, [IO.FileAttributes]::Normal)'
}

for i in "${!DEMO_FILES[@]}"; do
  BACKUPS[i]="$STATE_DIR/demo-$i.original"
  cp -- "${DEMO_FILES[i]}" "${BACKUPS[i]}"
  ATTRS[i]=$(get_attrs "${DEMO_FILES[i]}")
  HASHES[i]=$(sha256sum "${DEMO_FILES[i]}" | awk '{print $1}')
done

arm() { DIRTY[$1]=1; }

restore_idx() {
  local i=$1 path=${DEMO_FILES[$1]}
  ((DIRTY[i])) || return 0
  clear_attrs "$path" || return 1
  cp -f -- "${BACKUPS[$i]}" "$path" || return 1
  set_attrs "$path" "${ATTRS[$i]}" || return 1
  [[ $(sha256sum "$path" | awk '{print $1}') == "${HASHES[$i]}" ]] || return 1
  [[ $(get_attrs "$path") == "${ATTRS[$i]}" ]] || return 1
  DIRTY[i]=0
}

REC_RUNNING=0
REC_PID=''
REC_IN_FD=''
FF_LOG="$STATE_DIR/ffmpeg.log"
FF_PROGRESS="$STATE_DIR/ffmpeg.progress"

start_recorder() {
  coproc RECORDER {
    ffmpeg -hide_banner -loglevel warning -stats_period 0.5 \
      -progress "$FF_PROGRESS" \
      -f lavfi -i 'gfxcapture=monitor_idx=1:max_framerate=15:capture_cursor=0' \
      -vf 'hwdownload,format=bgra,format=yuv420p' -r 15 \
      -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
      -y "$VIDEO" >"$FF_LOG" 2>&1
  }
  REC_PID=$RECORDER_PID
  REC_IN_FD=${RECORDER[1]}
  local rec_out_fd=${RECORDER[0]}
  exec {rec_out_fd}<&-
  REC_RUNNING=1

  local deadline=$((SECONDS + 20)) out_us wall_ms tick=0
  until awk -F= '$1=="out_time_us" && $2+0>0 {ok=1} END {exit !ok}' \
      "$FF_PROGRESS" 2>/dev/null; do
    ps -p "$REC_PID" >/dev/null 2>&1 || {
      sed -n '1,120p' "$FF_LOG" >&2
      die "FFMPEG_START_FAILED"
    }
    ((SECONDS < deadline)) || die "FFMPEG_NO_FRAME_TIMEOUT"
    printf '\r\033[2KRECORDER_PREFLIGHT %03d' "$tick"
    tick=$((tick + 1))
    sleep 0.1
  done
  printf '\r\033[2K'

  out_us=$(awk -F= '$1=="out_time_us"{value=$2} END{print value+0}' "$FF_PROGRESS")
  wall_ms=$(now_ms)
  T0_MS=$((wall_ms - out_us / 1000))
}

stop_recorder() {
  ((REC_RUNNING)) || return 0
  local rc=0
  printf 'q' 1>&"$REC_IN_FD" 2>/dev/null || true
  exec {REC_IN_FD}>&- 2>/dev/null || true
  wait "$REC_PID" || rc=$?
  REC_RUNNING=0
  return "$rc"
}

GATE_HELPER="$STATE_DIR/gate-tab.sh"
GATE_STARTED="$STATE_DIR/gate.started"
GATE_DONE="$STATE_DIR/gate.done"
GATE_SHOW="$STATE_DIR/gate.show"
GATE_READY="$STATE_DIR/gate.ready"
GATE_RELEASE="$STATE_DIR/gate.release"
GATE_EXITED="$STATE_DIR/gate.exited"
GATE_TAB_STARTED=0
NORMAL_EXIT=0

cleanup() {
  local rc=$? cleanup_rc i
  trap - EXIT INT TERM
  set +e
  cleanup_rc=$rc
  ((NORMAL_EXIT)) || ((cleanup_rc != 0)) || cleanup_rc=130
  for ((i = ${#DEMO_FILES[@]} - 1; i >= 0; i--)); do
    restore_idx "$i" || cleanup_rc=90
  done
  if [[ -n $ACTIVE_EDGE_PROFILE ]]; then
    close_edge_profile "$ACTIVE_EDGE_PROFILE" || cleanup_rc=94
    ACTIVE_EDGE_PROFILE=''
  fi
  terminal_code_zoom_off || cleanup_rc=95
  ((GATE_TAB_STARTED)) && : >"$GATE_RELEASE"
  stop_recorder || { ((cleanup_rc != 0)) || cleanup_rc=91; }
  if ((cleanup_rc == 0 && NORMAL_EXIT)); then
    [[ -e $GATE_EXITED ]] || cleanup_rc=92
    if ((cleanup_rc == 0)); then
      rm -r -- "$STATE_DIR" || cleanup_rc=93
    fi
  fi
  if ((cleanup_rc != 0)); then
    printf 'VIDEO_RECOVERY_STATE_RETAINED: %s\n' "$STATE_DIR" >&2
  fi
  exit "$cleanup_rc"
}
trap cleanup EXIT INT TERM

start_gate_tab() {
  local expected_head root_win bash_win helper_win deadline
  expected_head=$(git rev-parse HEAD)
  cat >"$GATE_HELPER" <<'GATE'
#!/usr/bin/env bash
set -uo pipefail
: "${VIDEO_GATE_ROOT:?}" "${VIDEO_GATE_HEAD:?}" "${VIDEO_GATE_STARTED:?}"
: "${VIDEO_GATE_DONE:?}" "${VIDEO_GATE_SHOW:?}" "${VIDEO_GATE_READY:?}"
: "${VIDEO_GATE_RELEASE:?}" "${VIDEO_GATE_EXITED:?}" "${VIDEO_GATE_LOG:?}"

atomic() {
  printf '%s\n' "$2" >"$1.tmp"
  mv -f -- "$1.tmp" "$1"
}

cd "$VIDEO_GATE_ROOT" || { atomic "$VIDEO_GATE_DONE" 96; exit 96; }
actual=$(git rev-parse HEAD 2>/dev/null) || { atomic "$VIDEO_GATE_DONE" 97; exit 97; }
[[ $actual == "$VIDEO_GATE_HEAD" ]] || {
  printf 'LOCAL_GATE_HEAD_MISMATCH\n' >&2
  atomic "$VIDEO_GATE_DONE" 98
  exit 98
}

printf '\nLOCAL_EVIDENCE_GATE_STARTED %s\n' "$actual"
atomic "$VIDEO_GATE_STARTED" "$actual"
set +e
uv run python scripts/run_local_evidence_gates.py 2>&1 | tee "$VIDEO_GATE_LOG"
rc=${PIPESTATUS[0]}
set -e
printf '\nLOCAL_EVIDENCE_GATE_FINISHED rc=%d\n' "$rc"
atomic "$VIDEO_GATE_DONE" "$rc"
while [[ ! -e $VIDEO_GATE_SHOW ]]; do sleep 0.1; done
printf '\nLOCAL_EVIDENCE_GATE_READY rc=%d\n' "$rc"
atomic "$VIDEO_GATE_READY" "$rc"
while [[ ! -e $VIDEO_GATE_RELEASE ]]; do sleep 0.1; done
atomic "$VIDEO_GATE_EXITED" "$rc"
exit "$rc"
GATE
  chmod 700 "$GATE_HELPER"

  export VIDEO_GATE_ROOT="$ROOT"
  export VIDEO_GATE_HEAD="$expected_head"
  export VIDEO_GATE_STARTED="$GATE_STARTED"
  export VIDEO_GATE_DONE="$GATE_DONE"
  export VIDEO_GATE_SHOW="$GATE_SHOW"
  export VIDEO_GATE_READY="$GATE_READY"
  export VIDEO_GATE_RELEASE="$GATE_RELEASE"
  export VIDEO_GATE_EXITED="$GATE_EXITED"
  export VIDEO_GATE_LOG="$GATE_LOG"
  root_win=$(cygpath -aw "$ROOT")
  bash_win=$(cygpath -aw "$(command -v bash)")
  helper_win=$(cygpath -aw "$GATE_HELPER")

  wt.exe -w "${VIDEO_WT_WINDOW:-0}" new-tab \
    --title "MDS650 local evidence gate" \
    --startingDirectory "$root_win" \
    --inheritEnvironment \
    "$bash_win" --noprofile --norc "$helper_win"

  deadline=$((SECONDS + 20))
  until [[ -s $GATE_STARTED ]]; do
    ((SECONDS < deadline)) || die "WT_GATE_TAB_NOT_STARTED"
    sleep 0.1
  done
  GATE_TAB_STARTED=1
  wt.exe -w "${VIDEO_WT_WINDOW:-0}" focus-tab --target 0
}

show_gate_result() {
  local deadline gate_rc
  mark WAIT "local evidence gate completion"
  printf 'LOCAL_EVIDENCE_GATE_RUNNING_IN_BACKGROUND'
  deadline=$((SECONDS + 900))
  until [[ -s $GATE_DONE ]]; do
    ((SECONDS < deadline)) || die "LOCAL_GATE_TIMEOUT"
    printf '.'
    sleep 2
  done
  printf '\n'
  gate_rc=$(<"$GATE_DONE")
  [[ $gate_rc =~ ^[0-9]+$ ]] || die "LOCAL_GATE_RESULT_INVALID"
  : >"$GATE_SHOW"
  deadline=$((SECONDS + 10))
  until [[ -s $GATE_READY ]]; do
    ((SECONDS < deadline)) || die "LOCAL_GATE_READY_TIMEOUT"
    sleep 0.1
  done

  wt.exe -w "${VIDEO_WT_WINDOW:-0}" focus-tab --target 1
  sleep 5
  mark VISUAL "completed seven-gate summary in the evidence terminal"
  sleep 12
  wt.exe -w "${VIDEO_WT_WINDOW:-0}" focus-tab --target 0
  sleep 1
  : >"$GATE_RELEASE"
  deadline=$((SECONDS + 10))
  until [[ -e $GATE_EXITED ]]; do
    ((SECONDS < deadline)) || die "LOCAL_GATE_EXIT_TIMEOUT"
    sleep 0.1
  done
  ((gate_rc == 0)) || die "LOCAL_EVIDENCE_GATE_FAILED:$gate_rc"
}

show_clean() {
  run_shell 'git status --short; test -z "$(git status --porcelain=v1 --untracked-files=all)" && printf "WORKTREE_CLEAN\n"'
}

contrast_table() {
  local role=$1 contrast=$2
  jq -r --arg role "$role" --arg contrast "$contrast" '
    .models[] as $model |
    (if $contrast == "both" then ["b1_over_b0", "b2_over_b1"]
     else [$contrast] end)[] as $layer |
    .[$role].nested_tests[$model][$layer] as $x |
    [$model, $layer, $x.estimate, $x.ci_low, $x.ci_high,
     $x.p_value, $x.mde,
     (if ($x.estimate|abs) >= $x.mde then "CLEARS" else "BELOW" end)] | @tsv
  ' "$INFERENCE" |
    awk -F'\t' '
      BEGIN { printf "%-17s %-11s %-10s %-24s %-10s %-11s %s\n",
                     "MODEL", "LAYER", "ESTIMATE", "95% INTERVAL", "P", "MDE", "RESULT" }
      { printf "%-17s %-11s %+0.5f    [%+0.5f,%+0.5f]    %.4f     %.5f     %s\n",
               $1, $2, $3, $4, $5, $6, $7, $8 }
    '
}

threshold_counts() {
  jq '
    [.D, .V] as $roles |
    [$roles[] | .nested_tests | to_entries[] |
      .value.b1_over_b0, .value.b2_over_b1] as $cells |
    [$roles[] | .nested_tests | to_entries[] | .value.b2_over_b1] as $flow |
    {comparisons: ($cells|length),
     clear_own_mde: ([$cells[] | select((.estimate|abs) >= .mde)]|length),
     flow_clear_own_mde: ([$flow[] | select((.estimate|abs) >= .mde)]|length)}
  ' "$INFERENCE"
}

validate_chapters() {
  local duration_ms=$1
  [[ $duration_ms =~ ^[0-9]+$ && -s $CH ]] || die "CHAPTER_LEDGER_INVALID"
  awk -F'\t' -v duration_ms="$duration_ms" '
    BEGIN { expected_act = 1 }
    {
      if (NF != 3 || $1 !~ /^[0-9]+$/) bad = 1
      timestamp = $1 + 0
      if (NR > 1 && timestamp < previous) bad = 1
      if ($2 == "ACT") {
        prefix = expected_act " | "
        if (index($3, prefix) != 1) bad = 1
        expected_act++
      }
      if ($2 == "END") {
        end_count++
        end_ms = timestamp
      }
      previous = timestamp
    }
    END {
      if (NR == 0 || bad || expected_act != 6 || end_count != 1 ||
          end_ms > duration_ms || previous > duration_ms) exit 1
    }
  ' "$CH" || die "CHAPTER_LEDGER_INVALID"
}

MANIFEST=$(jq -er '.scientific_bundle.manifest.path' data/CANONICAL_STATE.json)
INFERENCE="${MANIFEST%/*}/rp2_block10_inference/inference.json"
[[ -f $MANIFEST && -f $INFERENCE ]] || die "CANONICAL_BUNDLE_MISSING"

printf '\033[2J\033[H\033]0;MDS650 progress evidence\007'
start_recorder

act 1 "THE QUESTION"
say "A forecast question, stated before any result"
show_range README.md 1 37 "registered question, boundary, and evidence contract"
show_svg docs/figures/evidence.svg "Twelve contrasts against their registered thresholds"

act 2 "THE MACHINE"
say "The full local evidence gate starts now in a second terminal"
start_gate_tab
say "FMP normalizes observed one-minute bars and rejects malformed rows"
show_def src/mds650/providers/fmp.py parse_minute_payload
say "Massive preserves directed bid and ask quotes, including empty windows"
show_def src/mds650/providers/massive.py parse_directed_quotes
say "Unusual Whales parses aggregate alerts without inventing trade intent"
show_def src/mds650/providers/unusual_whales.py parse_flow_alert_payload

say "The information clock is an engineered object"
say "This function rejects unresolved timestamps and forecast origins outside their XNYS session"
show_def src/mds650/provider_timing_v21.py audit_forecast_origin_session_bounds
say "This wrapper selects the final quote in the supplied cache at or before the cutoff"
show_def src/mds650/provider_timing_v21.py reselect_last_quote_asof
say "These helpers validate, deduplicate, sort, and bisect the supplied quote cache"
show_def src/mds650/provider_timing_v21.py _prepare_quotes
show_def src/mds650/provider_timing_v21.py _select_prepared_quote
say "This audit reports provider identity, reselection coverage, and monotonicity as separate facts"
show_def src/mds650/provider_timing_v21.py audit_massive_reselection
say "This audit classifies B2 coding and preserves the source incident and file hash"
show_def src/mds650/provider_timing_v21.py audit_b2_canonical_traceability

say "One canonical thirteen-step pipeline"
show_range src/mds650/rp2/run_manifest.py 54 121 \
  "thirteen declared steps and their required outputs"
show_range scripts/run_rp2_v3_pipeline.py 290 339 \
  "step execution, exit checks, and output digests"
show_range scripts/run_rp2_v3_pipeline.py 907 953 \
  "input and registered-artifact revalidation"
show_range scripts/run_rp2_v3_pipeline.py 1336 1399 \
  "verify-before-manifest closeout"
show_range src/mds650/rp2/run_manifest.py 333 388 \
  "stable digest rules for JSON and byte-preserved formats"

say "Econometrics, power, and dependent-data inference"
run "rg -n '^def (session_block_bootstrap|wild_cluster_bootstrap|stationary_bootstrap_indices|newey_west_variance|newey_west_p_value|giacomini_white|session_giacomini_white|hansen_spa|minimum_detectable_effect|minimum_detectable_effect_from_long_run_variance|clark_west_terms|clustered_mean_test|session_contrast)' src/mds650/rp2/inference.py" \
  rg -n '^def (session_block_bootstrap|wild_cluster_bootstrap|stationary_bootstrap_indices|newey_west_variance|newey_west_p_value|giacomini_white|session_giacomini_white|hansen_spa|minimum_detectable_effect|minimum_detectable_effect_from_long_run_variance|clark_west_terms|clustered_mean_test|session_contrast)' \
  src/mds650/rp2/inference.py
say "This complete function converts long-run variance and the prospective session count into the MDE"
show_def src/mds650/rp2/inference.py minimum_detectable_effect_from_long_run_variance

say "A canonical recorded estimate traced through checked SHA-256 links"
run "jq '{run_id:.scientific_bundle.run_id, manifest:.scientific_bundle.manifest}' data/CANONICAL_STATE.json" \
  jq '{run_id:.scientific_bundle.run_id, manifest:.scientific_bundle.manifest}' \
  data/CANONICAL_STATE.json
run "verify canonical manifest SHA-256" verify_sha256 \
  "$(jq -er '.scientific_bundle.manifest.sha256' data/CANONICAL_STATE.json)" "$MANIFEST"
run "jq '.steps[] | select(.name == \"run-incremental-inference\") | {name, artifacts, content}' $MANIFEST" \
  jq '.steps[] | select(.name == "run-incremental-inference") | {name, artifacts, content}' \
  "$MANIFEST"
run "verify manifest-recorded inference SHA-256" verify_sha256 \
  "$(jq -er '.steps[] | select(.name == "run-incremental-inference") | .artifacts["rp2_block10_inference/inference.json"]' "$MANIFEST")" \
  "$INFERENCE"
run "jq '.D.nested_tests.gamma_glm.b1_over_b0 | {estimate, ci_low, ci_high, p_value, mde}' $INFERENCE" \
  jq '.D.nested_tests.gamma_glm.b1_over_b0 | {estimate, ci_low, ci_high, p_value, mde}' \
  "$INFERENCE"

act 3 "WHAT IT MEASURED"
say "Model development: option state over the price-only baseline"
run "contrast_table D b1_over_b0 $INFERENCE" contrast_table D b1_over_b0

say "Model development: recent flow over option state"
run "contrast_table D b2_over_b1 $INFERENCE" contrast_table D b2_over_b1

say "Held-out check: all six state and flow contrasts"
run "contrast_table V both $INFERENCE" contrast_table V both
run "threshold_counts $INFERENCE" threshold_counts
show_svg docs/figures/cumulative-loss-difference.svg "Cumulative loss differences by information layer"

act 4 "BREAK IT LIVE"
say "E: the complete local evidence gate"
show_gate_result
show_clean

say "D: one frozen result, three enforcement layers"
arm 0
set_attrs "$FROZEN" "$((ATTRS[0] | 1))"
run "pwsh: (Get-Item $FROZEN).IsReadOnly" \
  pwsh.exe -NoLogo -NoProfile -NonInteractive -Command \
  "(Get-Item -LiteralPath '$(cygpath -aw "$FROZEN")').IsReadOnly"
expect_fail "PermissionError" \
  "uv run python -c '<append to read-only frozen result>'" \
  uv run python -c \
  'from pathlib import Path; import sys; p=Path(sys.argv[1]); assert not (p.stat().st_mode & 0o200), "READ_ONLY_ATTRIBUTE_MISSING"; p.open("ab").write(b"x")' \
  "$FROZEN"
clear_attrs "$FROZEN"
show_range src/mds650/storage.py 178 199 \
  "shared immutable-file guard"
expect_fail "FROZEN_ARTIFACT_WRITE_REJECTED" \
  "uv run python -c '<writer guard against frozen result>'" \
  uv run python -c \
  'from pathlib import Path; from mds650.storage import assert_outside_frozen; assert_outside_frozen(Path("artifacts/gate1_inference/results.json"))'
run "jq '.entries | length' data/FROZEN_ARTIFACTS.json" \
  jq '.entries | length' data/FROZEN_ARTIFACTS.json
printf '\n' >>"$FROZEN"
expect_fail "MUTATED artifacts/gate1_inference/results.json" \
  "uv run pytest tests/contract/test_frozen_artifacts_registry.py::test_every_frozen_artifact_is_physically_intact -q" \
  uv run pytest \
  tests/contract/test_frozen_artifacts_registry.py::test_every_frozen_artifact_is_physically_intact -q
restore_idx 0
run "uv run pytest tests/contract/test_frozen_artifacts_registry.py -q" \
  uv run pytest tests/contract/test_frozen_artifacts_registry.py -q
show_clean

say "A: the versioned push hook rejects every licensed path"
HOOK_COMMIT=6d11962e804009cdc798dac8a3b0bdd141135d89
hook_probe() {
  printf 'refs/heads/video-demo %s refs/heads/video-demo %040d\n' \
    "$HOOK_COMMIT" 0 | scripts/hooks/pre-push origin unused
}
expect_fail "PRE_PUSH_GATED_PATH_REJECTED: refs/heads/video-demo" \
  "feed archive/local-main-20260822 to scripts/hooks/pre-push" \
  hook_probe
run "uv run python scripts/scan_public_secrets.py --check-hook" \
  uv run python scripts/scan_public_secrets.py --check-hook
show_clean

say "C: one false public sentence breaks the publication contract"
PHASE8_RESULT='artifacts/phase8_bridge/result_20260830_v1.json'
sessions=$(jq -er '.store_preflight.sessions' "$PHASE8_RESULT")
run "jq '{sessions:.store_preflight.sessions, reads:.sealed_cohorts_read}' $PHASE8_RESULT" \
  jq '{sessions:.store_preflight.sessions, reads:.sealed_cohorts_read}' "$PHASE8_RESULT"
((sessions > 0)) || die "PHASE8_SESSION_COUNT_INVALID"
arm 1
printf '\nPhase 8 acquired %d of %d sessions.\n' "$((sessions - 1))" "$sessions" >>"$README"
expect_fail "sessions=29 of 30" \
  "uv run pytest tests/contract/test_sealed_cohort_publication_claims.py -q" \
  uv run pytest tests/contract/test_sealed_cohort_publication_claims.py -q
restore_idx 1
run "uv run pytest tests/contract/test_sealed_cohort_publication_claims.py -q" \
  uv run pytest tests/contract/test_sealed_cohort_publication_claims.py -q
show_clean

say "B: changing one signed method field invalidates authorization"
share=$(jq -er '.temporal_train_validation_holdout_definition.train_share' "$FREEZE")
altered=0.7
[[ $share == 0.7 ]] && altered=0.6
run "jq '<train_share and contract_sha256>' successor freeze + authorization" \
  jq -n --argjson train_share "$share" \
  --arg contract_sha256 "$(jq -er '.contract_sha256' artifacts/target_blind_v22/successor_owner_authorization_v1.json)" \
  '{train_share:$train_share, contract_sha256:$contract_sha256}'
arm 2
clear_attrs "$FREEZE"
jq --argjson value "$altered" \
  '.temporal_train_validation_holdout_definition.train_share = $value' \
  "$FREEZE" >"$STATE_DIR/freeze-mutated.json"
cp -f -- "$STATE_DIR/freeze-mutated.json" "$FREEZE"
expect_fail "the authorization points at a different freeze" \
  "uv run pytest tests/contract/test_pit_v22_successor_freeze.py -q" \
  uv run pytest tests/contract/test_pit_v22_successor_freeze.py -q
restore_idx 2
run "uv run pytest tests/contract/test_pit_v22_successor_freeze.py -q" \
  uv run pytest tests/contract/test_pit_v22_successor_freeze.py -q
show_clean

act 5 "SCALE AND THE FINAL POSITION"
say "Every scale figure is computed at the recorded commit"
run "git rev-list --count HEAD" git rev-list --count HEAD
run_shell 'gh pr list --state merged --limit 1000 --json number | jq length'
run_shell 'git ls-files ":(glob)**/*.py" | wc -l'
run_shell 'rg -o -g "*.py" "def test_[A-Za-z0-9_]+" tests | wc -l'
run_shell 'uv run pytest --collect-only -q | tr -d "\r" | awk -F": " "NF==2 && \$2 ~ /^[0-9]+$/ {n+=\$2} END {print n+0}"'
run_shell 'git ls-files ":(glob)tests/contract/test_*.py" | wc -l'
run_shell 'uv run pytest tests/contract --collect-only -q | tr -d "\r" | awk -F": " "NF==2 && \$2 ~ /^[0-9]+$/ {n+=\$2} END {print n+0}"'
run_shell 'git ls-files ":(glob)docs/**/*.md" | wc -l'
run_shell 'git ls-files ":(glob)reports/**/*.md" | wc -l'
run "jq '{entry_count:(.entries|length), note}' data/FROZEN_ARTIFACTS.json" \
  jq '{entry_count:(.entries|length), note}' data/FROZEN_ARTIFACTS.json
run "rg -c '^[0-9]+\\. \\*\\*' docs/methodology_decisions.md" \
  rg -c '^[0-9]+\. \*\*' docs/methodology_decisions.md
run "rg -c '\\S' scripts/_gated_exclude_list.txt" \
  rg -c '\S' scripts/_gated_exclude_list.txt
run "git log --oneline -8" git log --oneline -8

say "Phase Eight A: one read spent, exploratory only"
run "jq '<Phase 8A custody and post-hoc fields>' data/CANONICAL_STATE.json" \
  jq '
    .active_protocols[] | select(.id == "phase8-prospective-bridge") |
    {state, sealed_cohorts_read,
     result:(.result|{overall_classification, claim_classification,
                      confirmatory_promotion_allowed}),
     posthoc:(.posthoc_materialized_remediation|
       {new_sessions_collected, sealed_cohorts_read, sealed_store_reopened,
        overall_classification:.result.overall_classification,
        claim_classification:.result.claim_classification})}
  ' data/CANONICAL_STATE.json

say "Validation A and B are permanently closed unread"
run "rg -n -C 2 'Validation A .*CLOSED_UNREAD_20260817' docs/methodology_decisions.md" \
  rg -n -C 2 'Validation A .*CLOSED_UNREAD_20260817' docs/methodology_decisions.md

say "RP Three remains sealed for one future read"
run "rg -n 'Preregistration status|Primary read size|Estimated read date|Confirmatory reads so far' docs/rp3/PREREGISTRATION.md" \
  rg -n 'Preregistration status|Primary read size|Estimated read date|Confirmatory reads so far' \
  docs/rp3/PREREGISTRATION.md
run_shell 'git show HEAD:docs/rp3/PREREGISTRATION.md | sha256sum'
run "jq '{confirmatory_reads}' artifacts/rp3/look_counter.json" \
  jq '{confirmatory_reads}' artifacts/rp3/look_counter.json
run "jq '{n_primary, primary_target, window_opens:.session_bank.window_opens, estimated_read_date:.session_bank.read_date}' artifacts/rp3/sizing.json" \
  jq '{n_primary, primary_target, window_opens:.session_bank.window_opens, estimated_read_date:.session_bank.read_date}' \
  artifacts/rp3/sizing.json

say "Phase Nine is collecting toward an endpoint, not reporting progress"
run "jq '{status, endpoint, read_gate, academic_submission_waits_for_phase9:.decision.academic_submission_waits_for_phase9, recommended_academic_use:.decision.recommended_academic_use}' artifacts/phase9/power_deadline_audit_v1.json" \
  jq '{status, endpoint, read_gate, academic_submission_waits_for_phase9:.decision.academic_submission_waits_for_phase9, recommended_academic_use:.decision.recommended_academic_use}' \
  artifacts/phase9/power_deadline_audit_v1.json

say "UW latency: a fixed twelve-session cohort with seven canonical reconciliations"
UW_STATE=$(jq -er '.uw_latency_campaign.state_artifact' data/CANONICAL_STATE.json)
UW_AGGREGATE=$(jq -er '.uw_latency_campaign.aggregate_artifact' data/CANONICAL_STATE.json)
[[ -f $UW_STATE && -f $UW_AGGREGATE ]] || die "UW_LATENCY_AUTHORITY_MISSING"
show_def scripts/uw_latency_reconcile.py main
show_def src/mds650/uw_latency_campaign.py _validated_reconciliation_age
run "jq '{as_of_date, counts, claim_classification}' $UW_STATE" \
  jq '{as_of_date, counts, claim_classification}' "$UW_STATE"
run "jq '<session, plus-seven date, maturity status>' $UW_STATE" \
  jq -r '
    .as_of_date as $as_of_date |
    ["session", "eligible_NY_date", "status"],
    (.session_inventory[] |
      (((.session + "T00:00:00Z") | fromdateiso8601) + 604800 |
        strftime("%Y-%m-%d")) as $eligible_date |
      [
        .session,
        $eligible_date,
        (if .reconciliation_present then
           "RECONCILED"
         elif $eligible_date <= $as_of_date then
           "ELIGIBLE_AWAITING_RECONCILIATION"
         else
           "PENDING_MATURITY"
         end)
      ]) |
    @tsv
  ' "$UW_STATE"
run "jq '{contract_window_support, backfill, revision}' $UW_AGGREGATE" \
  jq '{contract_window_support, backfill, revision}' "$UW_AGGREGATE"

say "The PIT v2.2 successor attempt was consumed and failed closed before any OOS read"
run "sha256sum artifacts/target_blind_v22/successor_method_freeze_v1.json artifacts/target_blind_v22/successor_owner_authorization_v1.json" \
  sha256sum artifacts/target_blind_v22/successor_method_freeze_v1.json \
  artifacts/target_blind_v22/successor_owner_authorization_v1.json
run "jq '.pit_v22_successor_evaluation | {status, evaluation_attempt_count, oos_read_count, results_inspected, rerun_allowed, failure_code, development_mde_estimated, confirmatory_contrasts_evaluated, scientific_result, edge_claim_eligible, capital_eligible, capital_go, research_only}' data/CANONICAL_STATE.json" \
  jq '.pit_v22_successor_evaluation | {status, evaluation_attempt_count, oos_read_count, results_inspected, rerun_allowed, failure_code, development_mde_estimated, confirmatory_contrasts_evaluated, scientific_result, edge_claim_eligible, capital_eligible, capital_go, research_only}' \
  data/CANONICAL_STATE.json

say "The canonical position: no eligible headline result"
run "jq '{canonical_results, eligibility:.scientific_bundle.eligibility}' data/CANONICAL_STATE.json" \
  jq '{canonical_results, eligibility:.scientific_bundle.eligibility}' \
  data/CANONICAL_STATE.json
show_svg docs/figures/eligibility-gates.svg "Eligibility is a state machine, not an editorial choice"
show_clean

mark END "Recording complete"
sleep 5
stop_recorder || die "FFMPEG_EXIT_FAILED"

[[ -s $VIDEO ]] || die "VIDEO_EMPTY"
ffprobe -v error -show_streams -show_format -of json "$VIDEO" >"$STATE_DIR/video-probe.json"
jq -e '
  ([.streams[] | select(.codec_type == "video" and .codec_name == "h264" and
    .width == 2560 and .height == 1440)] | length) == 1 and
  ((.format.duration | tonumber) > 0)
' "$STATE_DIR/video-probe.json" >/dev/null || die "VIDEO_PROBE_FAILED"
VIDEO_DURATION_MS=$(jq -er '((.format.duration | tonumber) * 1000 | floor)' \
  "$STATE_DIR/video-probe.json")
validate_chapters "$VIDEO_DURATION_MS"
[[ -z $(git status --porcelain=v1 --untracked-files=all) ]] || die "FINAL_WORKTREE_NOT_CLEAN"

NORMAL_EXIT=1
printf 'VIDEO_CAPTURE_VERIFIED\nCHAPTER_LEDGER_VERIFIED\nVIDEO=%s\nCHAPTERS=%s\n' \
  "$VIDEO" "$CH"
