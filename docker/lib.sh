# -----------------------------------------------------------------------------
# The common part of the HSM-ROS2 docker scripts (sourced, POSIX sh): the image
# names, the dist lookup, the toolchain .deb staging and the image build. The
# caller sets $here to the docker directory before sourcing it.
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------

UBUNTU_VERSION="24.04"
ROS_DISTRO_NAME="jazzy"
TEST_IMAGE="hsm-ros2-test:$ROS_DISTRO_NAME"
DEV_IMAGE="hsm-ros2-dev:$ROS_DISTRO_NAME"
GUI_IMAGE="hsm-ros2-gui:$ROS_DISTRO_NAME"
DOCKER=${DOCKER:-docker}

# the toolchain packages every image with the editor needs
REQUIRED_DEBS="libhtreegeom libcyberiadaml libcyberiadamlpp python3-libcyberiadamlpp cyberiada-pro"

say() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }
die() { printf '\033[1;31merror: %s\033[0m\n' "$*" >&2; exit 1; }

NL='
'

# the docker dir lives in hsm_robot_ros_api; its parent holds the ros2 repos (and
# maybe other repos, e.g. the Cyberiada ones in ~/sources)
if [ -n "${here:-}" ]; then
    API_REPO=$(cd "$here/.." && pwd)
    API_NAME=$(basename "$API_REPO")
    SRC=$(cd "$API_REPO/.." && pwd)
fi

# ros2_repos DIR: the ROS repos of DIR, one path per line: the ones named in
# ros2-repos (next to this file) and $HSM_ROS2_REPOS; nothing else is scanned. A
# missing one is reported, one with a COLCON_IGNORE is left out
ros2_repos() {
    for _n in $(sed -e 's/#.*//' "$here/ros2-repos") ${HSM_ROS2_REPOS:-}; do
        if [ ! -d "$1/$_n" ]; then
            echo "warning: no ROS repo $_n in $1" >&2
        elif [ ! -e "$1/$_n/COLCON_IGNORE" ]; then
            printf '%s\n' "$1/$_n"
        fi
    done | awk '!seen[$0]++'
}

need_docker() {
    command -v "$DOCKER" >/dev/null 2>&1 || die "docker not found"
}

need_image() {
    "$DOCKER" image inspect "$1" >/dev/null 2>&1 \
        || die "image $1 not found; build it with $here/build-images.sh"
}

# find_dist [DIR]: the toolchain build output -> $DIST. DIR (--dist) wins, then
# ~/sources/dist, ~/devel/dist, and ../dist of the ros2 repo
find_dist() {
    if [ -n "${1:-}" ]; then
        [ -d "$1" ] || die "dist dir not found: $1"
        DIST=$(cd "$1" && pwd)
        return 0
    fi
    for _d in "$HOME/sources/dist" "$HOME/devel/dist" "$API_REPO/../dist"; do
        if [ -d "$_d" ]; then
            DIST=$(cd "$_d" && pwd)
            return 0
        fi
    done
    die "no dist dir (~/sources/dist, ~/devel/dist, $API_REPO/../dist); use --dist DIR"
}

# stage_debs DIST DEST: the toolchain .debs of dist/libs, dist/ubuntu-<ver> and
# dist itself, a later dir replacing a package of the same name
stage_debs() {
    mkdir -p "$2"
    for _d in "$1/libs" "$1/ubuntu-$UBUNTU_VERSION" "$1"; do
        [ -d "$_d" ] || continue
        for _f in "$_d"/*.deb; do
            [ -f "$_f" ] || continue
            _n=${_f##*/}
            rm -f "$2/${_n%%_*}"_*.deb
            cp "$_f" "$2/"
        done
    done
    for _p in $REQUIRED_DEBS; do
        ls "$2/$_p"_*.deb >/dev/null 2>&1 || die "no $_p .deb in $1 (libs/, ubuntu-$UBUNTU_VERSION/ or flat)"
    done
}

# docker_build TAG CONTEXT [ARGS...]: BuildKit/buildx preferred (the legacy builder
# is deprecated); the default builder is needed to see the local base images
docker_build() {
    _tag=$1; _ctx=$2; shift 2
    if "$DOCKER" buildx version >/dev/null 2>&1; then
        "$DOCKER" buildx build --load "$@" -t "$_tag" "$_ctx"
    else
        DOCKER_BUILDKIT=1 "$DOCKER" build "$@" -t "$_tag" "$_ctx"
    fi
}
