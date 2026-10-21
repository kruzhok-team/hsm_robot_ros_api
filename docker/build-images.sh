#!/bin/sh
# -----------------------------------------------------------------------------
# Build the HSM-ROS2 images (Ubuntu 24.04, ROS 2 Jazzy), each on the previous one:
#
#   hsm-ros2-test:jazzy  the clean test base: ROS core, colcon, rosdep (test-docker.sh)
#   hsm-ros2-dev:jazzy   + the build/test dependencies and the Cyberiada toolchain
#                        .debs of the dist dir (build-docker.sh)
#   hsm-ros2-gui:jazzy   + the ROS desktop (rviz2, rqt), OpenGL and the host user
#                        (run-gui.sh)
#
# The images are stable: build them once, rebuild when the toolchain changes.
# A build broken by the network is retried (--retries): Docker continues from the
# last finished layer and the apt cache keeps the downloaded .debs.
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------
set -eu

here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"

IMAGES="test dev gui"
DIST_ARG=""
MIRROR="ru.archive.ubuntu.com"
REBUILD=0
RETRIES=3
NETWORK=""

usage() {
    cat <<EOF
usage: $0 [options]
  --images "LIST"  images to build, of: test dev gui (default: "$IMAGES")
  --dist DIR       the toolchain .debs (default: ~/sources/dist, ~/devel/dist, ../dist)
  --mirror HOST    apt mirror host baked into the images (default: "$MIRROR"; "" stock)
  --rebuild        rebuild an image even if it already exists
  --retries N      attempts per image on a failure, e.g. the network (default: $RETRIES)
  --host-network   build with the host network (its DNS, proxy, VPN)
  -h, --help       this help

Builds $TEST_IMAGE, $DEV_IMAGE (with the toolchain of the dist dir) and
$GUI_IMAGE (for the user $(id -un)). Rebuild dev and gui after a toolchain update.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --images) IMAGES="$2"; shift 2 ;;
        --dist) DIST_ARG="$2"; shift 2 ;;
        --mirror) MIRROR="$2"; shift 2 ;;
        --rebuild) REBUILD=1; shift ;;
        --retries) RETRIES="$2"; shift 2 ;;
        --host-network) NETWORK="--network host"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

need_docker
wanted() { case " $IMAGES " in *" $1 "*) return 0 ;; esac; return 1; }
for i in $IMAGES; do
    case "$i" in test|dev|gui) ;; *) die "unknown image: $i" ;; esac
done

ctx=$(mktemp -d)
trap 'rm -rf "$ctx"' EXIT INT TERM

# skip an existing image unless --rebuild
fresh() {
    if [ "$REBUILD" -eq 0 ] && "$DOCKER" image inspect "$1" >/dev/null 2>&1; then
        say "image $1 already exists (use --rebuild to force)"
        return 1
    fi
    say "building $1"
}

common="--build-arg ROS_DISTRO=$ROS_DISTRO_NAME $NETWORK"

# build_image TAG CONTEXT [ARGS...]: docker_build, repeated after a failure; each
# attempt continues from the cached layers
build_image() {
    attempt=1
    until docker_build "$@"; do
        [ "$attempt" -lt "$RETRIES" ] || die "image $1 failed after $RETRIES attempts"
        wait=$((30 * attempt))
        say "image $1: attempt $attempt/$RETRIES failed, again in ${wait}s (cached layers are kept)"
        sleep "$wait"
        attempt=$((attempt + 1))
    done
}

if wanted test && fresh "$TEST_IMAGE"; then
    mkdir -p "$ctx/test"
    cp "$here/test/Dockerfile" "$here/retry" "$ctx/test/"
    # shellcheck disable=SC2086
    build_image "$TEST_IMAGE" "$ctx/test" $common \
        --build-arg "UBUNTU_VERSION=$UBUNTU_VERSION" --build-arg "APT_MIRROR_HOST=$MIRROR"
fi

if wanted dev && fresh "$DEV_IMAGE"; then
    need_image "$TEST_IMAGE"
    find_dist "$DIST_ARG"
    say "toolchain .debs from $DIST"
    mkdir -p "$ctx/dev"
    cp "$here/dev/Dockerfile" "$here/hsm-ros2-env.sh" "$ctx/dev/"
    stage_debs "$DIST" "$ctx/dev/debs"
    ls "$ctx/dev/debs"
    # shellcheck disable=SC2086
    build_image "$DEV_IMAGE" "$ctx/dev" $common --build-arg "BASE_IMAGE=$TEST_IMAGE"
fi

if wanted gui && fresh "$GUI_IMAGE"; then
    need_image "$DEV_IMAGE"
    [ "$(id -u)" -ne 0 ] || die "build the gui image as the everyday user, not root"
    mkdir -p "$ctx/gui"
    cp "$here/gui/Dockerfile" "$here/hsm-ros2-init" "$ctx/gui/"
    # shellcheck disable=SC2086
    build_image "$GUI_IMAGE" "$ctx/gui" $common --build-arg "BASE_IMAGE=$DEV_IMAGE" \
        --build-arg "USERNAME=$(id -un)" --build-arg "USER_UID=$(id -u)" \
        --build-arg "USER_GID=$(id -g)" --build-arg "USER_HOME=$HOME"
fi

say "images ready"
