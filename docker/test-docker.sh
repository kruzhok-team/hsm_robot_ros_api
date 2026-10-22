#!/bin/sh
# -----------------------------------------------------------------------------
# Test the HSM-ROS2 packages from scratch in the clean test image
# (hsm-ros2-test:jazzy, ROS core + colcon + rosdep only). A disposable container
# installs the toolchain .debs of the dist dir and the package.xml dependencies
# (rosdep), builds the read-only repos, runs the test tiers and checks the
# CyberiadaPro plugin (see in-container.sh). An undeclared dependency fails here,
# while the dev image would hide it.
#
# --debs install-tests the bloom .debs of build-docker.sh --package instead: no
# sources, the ros-jazzy-*.debs installed with their declared Depends only, then
# the packages, the generator and the plugin checked.
#
# The console log and the per-check logs go to <log-dir>; the exit code is 0
# only when the RESULT is PASS.
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------
set -eu

here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"

DIST_ARG=""
TIERS="L0 L1 L2 L3 L4"
LOG_DIR=""
DEBS=0
DEBS_DIR=""
IMAGE="$TEST_IMAGE"

usage() {
    cat <<EOF
usage: $0 [options]
  --dist DIR        the toolchain .debs (default: ~/sources/dist, ~/devel/dist, ../dist)
  --tiers "LIST"    test tiers, of: L0 L1 L2 L3 L4 (default: "$TIERS")
  --log-dir DIR     the logs (default: <dist>/test-logs/ros2-$ROS_DISTRO_NAME)
  --debs            install-test the .debs of build-docker.sh --package
  --debs-dir DIR    those .debs (default: <dist>/ros2-$ROS_DISTRO_NAME)
  --image NAME      the test image (default: $IMAGE)
  -h, --help        this help

The repos: $SRC. Build the image first with build-images.sh.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dist) DIST_ARG="$2"; shift 2 ;;
        --tiers) TIERS="$2"; shift 2 ;;
        --log-dir) LOG_DIR="$2"; shift 2 ;;
        --debs) DEBS=1; shift ;;
        --debs-dir) DEBS_DIR="$2"; shift 2 ;;
        --image) IMAGE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

need_docker
need_image "$IMAGE"
find_dist "$DIST_ARG"
if [ "$DEBS" -eq 1 ]; then
    DEBS_DIR=${DEBS_DIR:-$DIST/ros2-$ROS_DISTRO_NAME}
    ls "$DEBS_DIR"/ros-"$ROS_DISTRO_NAME"-*.deb >/dev/null 2>&1 \
        || die "no ros-$ROS_DISTRO_NAME-*.deb in $DEBS_DIR; build them with build-docker.sh --package"
    LOG_DIR=${LOG_DIR:-$DIST/test-logs/ros2-$ROS_DISTRO_NAME-debs}
else
    LOG_DIR=${LOG_DIR:-$DIST/test-logs/ros2-$ROS_DISTRO_NAME}
fi
mkdir -p "$LOG_DIR"
LOG_DIR=$(cd "$LOG_DIR" && pwd)
log="$LOG_DIR/console.log"
rcf="$LOG_DIR/.rc"
name="hsm-ros2-test-run"
rev=$(git -C "$API_REPO" describe --always --dirty 2>/dev/null || echo unknown)

set --
if [ "$DEBS" -eq 1 ]; then
    # the .debs only, no sources: an undeclared Depends fails the install or the checks
    DEBS_DIR=$(cd "$DEBS_DIR" && pwd)
    phases="apt debs rosdep-local install smoke plugin"
    set -- -v "$DEBS_DIR:/debs:ro"
else
    # only the ROS repos (the ros2-repos list and $HSM_ROS2_REPOS), read-only under /src
    repos=$(ros2_repos "$SRC")
    [ -n "$repos" ] || die "no ROS repos of $here/ros2-repos in $SRC"
    phases="apt debs rosdep-local rosdep copy build tests plugin"
    oldifs=$IFS; IFS=$NL
    for r in $repos; do set -- "$@" -v "$r:/src/$(basename "$r"):ro"; done
    IFS=$oldifs
fi

trap '"$DOCKER" rm -f "$name" >/dev/null 2>&1; exit 130' INT TERM
"$DOCKER" rm -f "$name" >/dev/null 2>&1 || true
rm -f "$rcf"

say "testing $SRC with the toolchain of $DIST in $IMAGE -> $LOG_DIR"
# dash has no pipefail: the exit code of docker run comes back through a file
{ "$DOCKER" run --rm --name "$name" \
      -e HSM_PHASES="$phases" -e HSM_TIERS="$TIERS" \
      -e HSM_SRC=/src -e HSM_DIST=/dist -e HSM_LOGS=/logs -e HSM_DEBS=/debs \
      -e HSM_OWNER="$(id -u):$(id -g)" \
      "$@" -v "$here":/hsm-docker:ro -v "$DIST":/dist:ro -v "$LOG_DIR":/logs \
      "$IMAGE" sh /hsm-docker/in-container.sh || echo $? >"$rcf"; } 2>&1 | tee "$log"
rc=0
[ ! -f "$rcf" ] || rc=$(cat "$rcf")
rm -f "$rcf"

result=$(grep '^RESULT ' "$log" | tail -n 1 || true)
say "summary (api $rev, logs in $LOG_DIR)"
[ -n "$result" ] || die "no RESULT line (docker exit $rc)"
echo "  $result"
case "$result" in
    "RESULT $ROS_DISTRO_NAME PASS "*) say "done — the clean build and tests pass" ;;
    *) die "the clean test failed; see the FAIL lines above and $LOG_DIR" ;;
esac
