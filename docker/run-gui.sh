#!/bin/sh
# -----------------------------------------------------------------------------
# The everyday HSM-ROS2 container: a persistent, named container of the gui image
# (hsm-ros2-gui:jazzy) with CyberiadaPro, rviz2, rqt and turtlesim on the host
# display (X11, XWayland, or Wayland with --wayland).
#
# Created on the first run, then started and entered: a login shell, or the given
# command (rviz2, rqt, CyberiadaPro with --editor ...). Nothing is copied: the
# repos dir is bind-mounted read-write at its host path, so git, the editor and
# the plugin see the same paths inside and outside:
#
#   the repos dir (--src)              the parent of hsm_robot_ros_api, wherever it
#                                      is (~/ros2_ws/src, ~/sources)
#   the colcon workspace               ~/ros2_ws in the <name>-ws volume, or a host
#                                      dir (--ws); hsm-ros2-init links the ROS repos
#                                      of the repos dir (a package.xml) into its src/
#                                      and builds them, the others are left out
#   the Cyberiada sources (--sources)  only when asked
#   extra dirs (--mount DIR)           e.g. the diagrams
#
# A ROS repo cloned later into the repos dir needs only hsm-ros2-init again.
#
# The rest of the home dir (the editor settings, the installed plugin, history)
# is the <name>-home volume. The mounts, the network and the devices are fixed when
# the container is created: change them with --recreate (the volumes stay).
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------
set -eu

here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"

NAME="hsm-ros2"
IMAGE="$GUI_IMAGE"
SRC_DIR="$SRC"
WS=""
SOURCES=""
MOUNTS=""
WAYLAND=0
NVIDIA=0
ISOLATED=0
SOFTGL=0
EDITOR=0
DETACH=0
ACTION="run"

usage() {
    cat <<EOF
usage: $0 [options] [--] [command [args...]]
  --name NAME      the container (default: $NAME; volumes NAME-home, NAME-ws)
  --image NAME     the gui image (default: $IMAGE)
  --src DIR        the repos dir (default: $SRC)
  --ws DIR         the colcon workspace on the host (default: ~/ros2_ws in the
                   NAME-ws volume)
  --sources DIR    also mount the Cyberiada sources (e.g. ~/sources)
  --mount DIR      also mount DIR at its path (repeatable)
  --wayland        native Wayland Qt (rviz2 still needs QT_QPA_PLATFORM=xcb)
  --nvidia         the NVIDIA GPU (needs the nvidia container toolkit)
  --isolated       own network, not the host one (no DDS with the host nodes)
  --software-gl    software OpenGL (no GPU, or a broken driver)
  --editor         run CyberiadaPro
  -d, --detach     run the command in the background
  --status         show the container and its mounts
  --stop           stop the container
  --rm             remove the container (the volumes stay)
  --recreate       remove and create the container again (new mounts/options)
  -h, --help       this help

Examples:
  $0                       a shell; first time: hsm-ros2-init builds the workspace
  $0 --editor -d           CyberiadaPro
  $0 rviz2                 rviz2 (also: rqt, ros2 run turtlesim turtlesim_node)
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --name) NAME="$2"; shift 2 ;;
        --image) IMAGE="$2"; shift 2 ;;
        --src) SRC_DIR="$2"; shift 2 ;;
        --ws) WS="$2"; shift 2 ;;
        --sources) SOURCES="$2"; shift 2 ;;
        --mount) MOUNTS="$MOUNTS${MOUNTS:+
}$2"; shift 2 ;;
        --wayland) WAYLAND=1; shift ;;
        --nvidia) NVIDIA=1; shift ;;
        --isolated) ISOLATED=1; shift ;;
        --software-gl) SOFTGL=1; shift ;;
        --editor) EDITOR=1; shift ;;
        -d|--detach) DETACH=1; shift ;;
        --status) ACTION=status; shift ;;
        --stop) ACTION=stop; shift ;;
        --rm) ACTION=rm; shift ;;
        --recreate) ACTION=recreate; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) echo "unknown option: $1" >&2; usage; exit 2 ;;
        *) break ;;
    esac
done

need_docker
# the host dir of the X cookie, outside the home volume (/run/hsm-ros2 inside)
CACHE="$HOME/.cache/hsm-ros2/$NAME"
XAUTH_FILE="$CACHE/Xauthority"

exists() { "$DOCKER" container inspect "$NAME" >/dev/null 2>&1; }
running() { [ "$("$DOCKER" container inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" = true ]; }
abspath() { [ -d "$1" ] || die "directory not found: $1"; (cd "$1" && pwd); }
# inside A B: A is B or below it
inside() { [ "$1" = "$2" ] && return 0; case "$1" in "$2"/*) return 0 ;; esac; return 1; }

case "$ACTION" in
    status)
        exists || die "no container $NAME; create it with $0"
        "$DOCKER" ps -a --filter "name=^$NAME\$" --format '{{.Names}}  {{.Image}}  {{.Status}}'
        "$DOCKER" container inspect -f \
            '{{range .Mounts}}  {{if .Name}}{{.Name}}{{else}}{{.Source}}{{end}} -> {{.Destination}}{{"\n"}}{{end}}' "$NAME"
        exit 0 ;;
    stop) if exists; then "$DOCKER" stop "$NAME" >/dev/null; fi; say "$NAME stopped"; exit 0 ;;
    rm) "$DOCKER" rm -f "$NAME" >/dev/null 2>&1 || true
        say "$NAME removed (the volumes $NAME-home, $NAME-ws stay; docker volume rm to drop)"; exit 0 ;;
    recreate) "$DOCKER" rm -f "$NAME" >/dev/null 2>&1 || true ;;
esac

# --- the mounts --------------------------------------------------------------
SRC_DIR=$(abspath "$SRC_DIR")
if [ -z "$WS" ]; then
    WS="$HOME/ros2_ws"; WS_VOLUME=1
else
    mkdir -p "$WS"
    WS=$(abspath "$WS"); WS_VOLUME=0
fi
[ -z "$SOURCES" ] || SOURCES=$(abspath "$SOURCES")

# the repos dir, whose ROS repos hsm-ros2-init links and builds, and this docker
# dir (hsm-ros2-init runs from here)
REPOS=$(ros2_repos "$SRC_DIR")
[ -n "$REPOS" ] || echo "warning: no ROS repos (package.xml) in $SRC_DIR yet" >&2
binds="$SRC_DIR$NL$API_REPO"

# the bind-mounted dirs, without the ones another one already holds
[ "$WS_VOLUME" -eq 1 ] || binds="$binds$NL$WS"
[ -z "$SOURCES" ] || binds="$binds$NL$SOURCES"
oldifs=$IFS; IFS=$NL; set -f
for m in $MOUNTS; do binds="$binds$NL$(abspath "$m")"; done
BINDS=""
for d in $binds; do
    case "$HOME/" in "$d"/*) die "$d holds the home dir; it cannot be mounted over the home volume" ;; esac
    keep=1
    for e in $binds; do
        if [ "$d" != "$e" ] && inside "$d" "$e"; then keep=0; fi
    done
    case "$NL$BINDS$NL" in *"$NL$d$NL"*) keep=0 ;; esac
    [ "$keep" -eq 0 ] || BINDS="$BINDS${BINDS:+$NL}$d"
done
IFS=$oldifs; set +f

create() {
    set -- --name "$NAME" --init --ipc host
    if [ "$ISOLATED" -eq 1 ]; then set -- "$@" --hostname "$NAME"; else set -- "$@" --network host; fi
    set -- "$@" -v "$NAME-home:$HOME" -v "$CACHE:/run/hsm-ros2"
    oldifs=$IFS; IFS=$NL; set -f
    for d in $BINDS; do set -- "$@" -v "$d:$d"; done
    IFS=$oldifs; set +f
    if [ "$WS_VOLUME" -eq 1 ]; then set -- "$@" -v "$NAME-ws:$WS"; fi
    if [ -d /tmp/.X11-unix ]; then set -- "$@" -v /tmp/.X11-unix:/tmp/.X11-unix:ro; fi
    if [ -d /dev/dri ]; then
        set -- "$@" --device /dev/dri
        for g in $(stat -c %g /dev/dri/* 2>/dev/null | sort -u); do set -- "$@" --group-add "$g"; done
    fi
    if [ "$WAYLAND" -eq 1 ] && [ -n "${XDG_RUNTIME_DIR:-}" ]; then
        set -- "$@" -v "$XDG_RUNTIME_DIR:$XDG_RUNTIME_DIR"
    fi
    if [ "$NVIDIA" -eq 1 ]; then set -- "$@" --gpus all -e NVIDIA_DRIVER_CAPABILITIES=all; fi
    set -- "$@" -e HSM_ROS2_WS="$WS" -e HSM_ROS2_SRC="$SRC_DIR" -e HSM_ROS2_DOCKER="$here"
    "$DOCKER" create "$@" "$IMAGE" >/dev/null
}

# docker makes the mount points in the home volume (and the ws volume itself) as
# root: hand them, up to the home dir, to the user
fix_owners() {
    set -- "$HOME"
    [ "$WS_VOLUME" -eq 0 ] || set -- "$@" "$WS"
    oldifs=$IFS; IFS=$NL; set -f
    for d in $BINDS $WS; do
        p=$(dirname "$d")
        while [ "$p" != "$HOME" ] && inside "$p" "$HOME"; do set -- "$@" "$p"; p=$(dirname "$p"); done
    done
    IFS=$oldifs; set +f
    "$DOCKER" exec -u 0 "$NAME" chown "$(id -u):$(id -g)" "$@"
}

# the X cookie of the current session, with any hostname (it changes with --isolated)
refresh_xauth() {
    rm -f "$XAUTH_FILE.new"
    if [ -n "${DISPLAY:-}" ] && command -v xauth >/dev/null 2>&1; then
        xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' \
            | xauth -f "$XAUTH_FILE.new" nmerge - 2>/dev/null || true
    fi
    if [ ! -s "$XAUTH_FILE.new" ] && [ -f "${XAUTHORITY:-$HOME/.Xauthority}" ]; then
        cp "${XAUTHORITY:-$HOME/.Xauthority}" "$XAUTH_FILE.new"
    fi
    if [ -f "$XAUTH_FILE.new" ]; then chmod 600 "$XAUTH_FILE.new"; mv "$XAUTH_FILE.new" "$XAUTH_FILE"; fi
}

mkdir -p "$CACHE"
if ! exists; then
    need_image "$IMAGE"
    user=$("$DOCKER" image inspect -f '{{.Config.User}}' "$IMAGE" 2>/dev/null || true)
    [ "$user" = "$(id -un)" ] || echo "warning: $IMAGE was built for '$user', not $(id -un); rebuild it" >&2
    say "creating $NAME: workspace $WS$([ "$WS_VOLUME" -eq 0 ] || echo " (volume $NAME-ws)")"
    printf '%s\n' "$BINDS" | sed 's/^/  mount: /'
    [ -z "$REPOS" ] || printf '%s\n' "$REPOS" | sed 's|^.*/|  ros repo: |'
    create
    "$DOCKER" start "$NAME" >/dev/null
    fix_owners
    echo "  first time: run hsm-ros2-init inside to build the workspace and install the plugin"
    echo "  no X access? on the host: xhost +SI:localuser:$(id -un)"
fi
if ! running; then "$DOCKER" start "$NAME" >/dev/null; fi
refresh_xauth

# --- the command: a login shell sources ROS 2 and the workspace ---------------
if [ "$EDITOR" -eq 1 ]; then set -- CyberiadaPro "$@"; fi
if [ $# -eq 0 ]; then
    set -- bash -l
else
    set -- bash -lc 'exec "$@"' hsm-ros2 "$@"
fi
set -- "$NAME" "$@"

# the current dir when the container has it, else the home dir
wd=$HOME
oldifs=$IFS; IFS=$NL; set -f
for d in $BINDS $WS; do
    if inside "$PWD" "$d"; then wd=$PWD; fi
done
IFS=$oldifs; set +f
set -- -w "$wd" "$@"

[ -z "${DISPLAY:-}" ] || set -- -e "DISPLAY=$DISPLAY" -e XAUTHORITY=/run/hsm-ros2/Xauthority "$@"
[ -z "${ROS_DOMAIN_ID:-}" ] || set -- -e "ROS_DOMAIN_ID=$ROS_DOMAIN_ID" "$@"
[ "$SOFTGL" -eq 0 ] || set -- -e LIBGL_ALWAYS_SOFTWARE=1 "$@"
if [ "$WAYLAND" -eq 1 ] && [ -n "${WAYLAND_DISPLAY:-}" ]; then
    set -- -e QT_QPA_PLATFORM=wayland -e "WAYLAND_DISPLAY=$WAYLAND_DISPLAY" \
        -e "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-}" "$@"
fi
if [ "$DETACH" -eq 1 ]; then
    set -- -d "$@"
elif [ -t 0 ] && [ -t 1 ]; then
    set -- -it "$@"
else
    set -- -i "$@"
fi
exec "$DOCKER" exec "$@"
