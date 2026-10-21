# -----------------------------------------------------------------------------
# ROS 2 and the HSM-ROS2 workspace ($HSM_ROS2_WS) in every shell of the images
# (/etc/profile.d and /etc/bash.bashrc).
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License, version 3 or later.
# -----------------------------------------------------------------------------

if [ -z "${_HSM_ROS2_ENV:-}" ] && [ -n "${ROS_DISTRO:-}" ]; then
    _HSM_ROS2_ENV=1
    if [ -n "${BASH_VERSION:-}" ]; then _hsm_ext=bash; else _hsm_ext=sh; fi
    if [ -f "/opt/ros/$ROS_DISTRO/setup.$_hsm_ext" ]; then
        . "/opt/ros/$ROS_DISTRO/setup.$_hsm_ext"
    fi
    if [ -n "${HSM_ROS2_WS:-}" ] && [ -f "$HSM_ROS2_WS/install/setup.$_hsm_ext" ]; then
        . "$HSM_ROS2_WS/install/setup.$_hsm_ext"
    fi
    unset _hsm_ext
fi
