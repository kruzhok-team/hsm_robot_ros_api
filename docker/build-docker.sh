#!/bin/sh
# -----------------------------------------------------------------------------
# Build and test the HSM-ROS2 packages in the dev image (hsm-ros2-dev:jazzy).
#
# Only the ROS repos next to hsm_robot_ros_api (a package.xml, see ros2_repos in
# lib.sh) are mounted, read-only, and copied into the container workspace, so a
# run never writes into the sources and a new ROS repo is picked up as it is. The
# dependencies of the packages missing in the image are installed by rosdep (as
# root); the build and the tests then run as the host user. The workspace is
# discarded with the container unless --out keeps it (then the next run builds
# incrementally).
# The build and the tiers run by in-container.sh; --shell opens a dev shell
# on the read-write sources instead.
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------
set -eu

here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"

TIERS="L0 L1 L2 L3 L4"
TEST=1
PACKAGES=""
JOBS=$(nproc 2>/dev/null || echo 2)
OUT=""
SHELL_MODE=0
IMAGE="$DEV_IMAGE"

usage() {
    cat <<EOF
usage: $0 [options]
  --tiers "LIST"     test tiers, of: L0 L1 L2 L3 L4 (default: "$TIERS")
  --no-test          build only
  --packages "LIST"  build these packages and their dependencies only
  --jobs N           parallel build jobs (default: $JOBS)
  --out DIR          keep the workspace (src copy, build, install, logs) in DIR
  --shell            an interactive shell in the dev image, sources read-write
  --image NAME       the dev image (default: $IMAGE)
  -h, --help         this help

The repos: $SRC. Build the image first with build-images.sh.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --tiers) TIERS="$2"; shift 2 ;;
        --no-test) TEST=0; shift ;;
        --packages) PACKAGES="$2"; shift 2 ;;
        --jobs) JOBS="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --shell) SHELL_MODE=1; shift ;;
        --image) IMAGE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

need_docker
need_image "$IMAGE"

# the ROS repos, read-only under /src (or read-write at their paths for --shell)
repos=$(ros2_repos "$SRC")
[ -n "$repos" ] || die "no ROS repos (package.xml) in $SRC"
printf '%s\n' "$repos" | sed 's|^.*/|  ros repo: |'
set --
oldifs=$IFS; IFS=$NL
for r in $repos; do
    if [ "$SHELL_MODE" -eq 1 ]; then
        set -- "$@" -v "$r:$r"
    else
        set -- "$@" -v "$r:/src/$(basename "$r"):ro"
    fi
done
IFS=$oldifs

if [ "$SHELL_MODE" -eq 1 ]; then
    say "dev shell in $IMAGE, repos in $SRC"
    exec "$DOCKER" run --rm -it --user "$(id -u):$(id -g)" -e HOME=/tmp \
        "$@" -w "$SRC" "$IMAGE" bash -l
fi

phases="apt rosdep copy build"
[ "$TEST" -eq 0 ] || phases="$phases tests"

# the kept workspace, if any
ws=/tmp/hsm-ws
if [ -n "$OUT" ]; then
    mkdir -p "$OUT"
    OUT=$(cd "$OUT" && pwd)
    set -- "$@" -v "$OUT:/ws"
    ws=/ws
fi

say "building ${PACKAGES:-all packages} of $SRC in $IMAGE${OUT:+ -> $OUT}"
# root for rosdep; HSM_OWNER: in-container.sh builds and tests as the host user
exec "$DOCKER" run --rm -e HSM_OWNER="$(id -u):$(id -g)" \
    -e HSM_PHASES="$phases" -e HSM_TIERS="$TIERS" -e HSM_JOBS="$JOBS" \
    -e HSM_PACKAGES="$PACKAGES" -e HSM_SRC=/src -e HSM_WS="$ws" \
    -v "$here":/hsm-docker:ro "$@" \
    "$IMAGE" sh /hsm-docker/in-container.sh
