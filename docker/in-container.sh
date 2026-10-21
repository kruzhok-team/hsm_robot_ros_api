#!/bin/sh
# -----------------------------------------------------------------------------
# Build and test the HSM-ROS2 packages inside a container. Run by build-docker.sh
# (the dev image, as the host user) and test-docker.sh (the clean test image, as
# root), never on a host: the test phases install packages.
#
# Phases (HSM_PHASES):
#   apt      apt-get update                                       (root)
#   debs     install the toolchain .debs of $HSM_DIST              (root)
#   copy     copy the read-only repos $HSM_SRC to $HSM_WS/src, without the VCS,
#            the build output and the caches
#   rosdep   install the package.xml dependencies                  (root)
#   build    colcon build
#   tests    the test tiers $HSM_TIERS (L0 linter, L1 unit, L2 node,
#            L3 integration, L4 system)
#   plugin   the CyberiadaPro hsm-ros2 plugin: found by the editor, installed
#
# Every check prints PASS/FAIL/SKIP; the last line is
#   RESULT jazzy PASS|FAIL|ERROR pass=N fail=N skip=N failed=...
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------
set -eu

here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"

PHASES=${HSM_PHASES:-copy build tests}
TIERS=${HSM_TIERS:-L0 L1 L2 L3 L4}
SRC=${HSM_SRC:-/src}
WS=${HSM_WS:-/tmp/hsm-ws}
DIST=${HSM_DIST:-/dist}
LOGS=${HSM_LOGS:-$WS/logs}
JOBS=${HSM_JOBS:-$(nproc 2>/dev/null || echo 2)}
PACKAGES=${HSM_PACKAGES:-}
DISTRO=${ROS_DISTRO:-$ROS_DISTRO_NAME}

# headless, and the tests talk to their own nodes only
export PYTHONDONTWRITEBYTECODE=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST QT_QPA_PLATFORM=offscreen
export ROS_LOG_DIR="$WS/ros-log"

npass=0; nfail=0; nskip=0; failed=""; finished=0

pass() { npass=$((npass + 1)); echo "PASS  $1"; }
skip() { nskip=$((nskip + 1)); echo "SKIP  $1 ($2)"; }
fail() {
    nfail=$((nfail + 1)); failed="$failed${failed:+,}$1"
    echo "FAIL  $1${2:+ ($2)}"
    if [ -n "${3:-}" ] && [ -s "$3" ]; then tail -n 60 "$3" | sed 's/^/      /'; fi
}
phase() { case " $PHASES " in *" $1 "*) return 0 ;; esac; return 1; }
failed_check() { case ",$failed," in *",$1,"*) return 0 ;; esac; return 1; }

# the logs belong to the host user (test-docker.sh runs as root)
own_logs() { [ -z "${HSM_OWNER:-}" ] || chown -R "$HSM_OWNER" "$LOGS" 2>/dev/null || true; }

# an abort (set -e, die) still ends with a RESULT line
finish() {
    rc=$?
    if [ "$finished" -eq 0 ]; then
        echo "RESULT $DISTRO ERROR pass=$npass fail=$nfail skip=$nskip failed=${failed:--} aborted=$rc"
    fi
    own_logs
}
trap finish EXIT

# check NAME CMD...: run CMD (a function of this script, too) into NAME.log; the
# subshell is not a condition, so set -e stops it at the first failing step
check() {
    name=$1; shift
    say "$name"
    set +e
    ( set -e; "$@" ) >"$LOGS/$name.log" 2>&1
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        pass "$name"
    else
        fail "$name" "exit $rc" "$LOGS/$name.log"
    fi
}

ros_env() {
    set +u
    . "/opt/ros/$DISTRO/setup.sh"
    if [ -f "$WS/install/setup.sh" ]; then . "$WS/install/setup.sh"; fi
    set -u
}

do_debs() {
    stage_debs "$DIST" /tmp/hsm-debs
    apt-get install -y --no-install-recommends /tmp/hsm-debs/*.deb
}

# copy_tree SRC DST: a source tree without its VCS, build output and caches (the
# generator repo may carry a stray build/ and install/ of its own)
do_copy() {
    rm -rf "$WS/src"
    python3 -c "import shutil, sys
shutil.copytree(sys.argv[1], sys.argv[2], symlinks=True, ignore=shutil.ignore_patterns(
    '.git', 'build', 'install', 'log', '__pycache__', '*.egg-info', '.pytest_cache'))" \
        "$SRC" "$WS/src"
}

do_rosdep() {
    rosdep install --from-paths "$WS/src" --ignore-src -y --rosdistro "$DISTRO"
}

do_build() {
    cd "$WS"
    # shellcheck disable=SC2086
    colcon build --base-paths src --parallel-workers "$JOBS" \
        --event-handlers console_cohesion+ ${PACKAGES:+--packages-up-to $PACKAGES}
}

# tier_spec TIER: "packages|pytest marker" of a test tier (docs/hsm_robot_testing.md)
tier_spec() {
    case "$1" in
        L0) echo "|linter" ;;
        L1) echo "hsm_generator|unit" ;;
        L2) echo "hsm_robot turtle_driver|node" ;;
        L3) echo "hsm_tests|integration" ;;
        L4) echo "hsm_tests|system" ;;
        *) return 1 ;;
    esac
}

# do_tier TIER: the tier's tests one package at a time (the nodes of parallel
# packages would see each other), then the summary of its results
do_tier() {
    spec=$(tier_spec "$1")
    pkgs=${spec%%|*}; mark=${spec#*|}
    res="$WS/build/test-results-$1"
    rm -rf "$res"
    cd "$WS"
    rc=0
    # shellcheck disable=SC2086
    colcon test --executor sequential --return-code-on-test-failure \
        --test-result-base "$res" --event-handlers console_cohesion+ \
        ${pkgs:+--packages-select $pkgs} --pytest-args -m "$mark" || rc=$?
    colcon test-result --test-result-base "$res" --verbose || true
    return "$rc"
}

# the editor finds the plugin of the install tree, and its installer puts it into
# the user plugin folder, where the editor finds it too
do_plugin() {
    command -v CyberiadaPro >/dev/null || { echo "CyberiadaPro not installed"; return 1; }
    # --plugin-path is the folder holding the plugin folders
    plugins="$WS/install/hsm_generator/share/hsm_generator"
    [ -f "$plugins/editor-plugin/plugin.json" ] || { echo "no plugin in $plugins"; return 1; }
    CyberiadaPro --batch --list-plugins --plugin-path "$plugins" | tee /tmp/hsm-plugins.txt
    grep -q 'hsm-ros2' /tmp/hsm-plugins.txt
    data=$(mktemp -d)
    XDG_DATA_HOME="$data" ros2 run hsm_generator hsm_generator --install-editor-plugin
    XDG_DATA_HOME="$data" CyberiadaPro --batch --list-plugins | tee /tmp/hsm-plugins.txt
    grep -q 'hsm-ros2' /tmp/hsm-plugins.txt
    rm -rf "$data"
}

mkdir -p "$WS" "$LOGS"
say "HSM-ROS2 on ROS 2 $DISTRO: $PHASES (workspace $WS)"

if phase apt; then check apt apt-get update; fi
if phase debs; then check debs do_debs; fi
if phase copy; then check copy do_copy; fi
if phase rosdep; then check rosdep do_rosdep; fi

ros_env
if phase build; then check build do_build; fi
ros_env

for t in $TIERS; do
    phase tests || break
    tier_spec "$t" >/dev/null || { fail "$t" "unknown tier"; continue; }
    if failed_check build || failed_check copy; then skip "$t" "no build"; continue; fi
    check "$t" do_tier "$t"
done

if phase plugin; then
    if failed_check build; then skip plugin "no build"; else check plugin do_plugin; fi
fi

finished=1
status=PASS
[ "$nfail" -eq 0 ] || status=FAIL
echo "RESULT $DISTRO $status pass=$npass fail=$nfail skip=$nskip failed=${failed:--}"
[ "$status" = PASS ]
