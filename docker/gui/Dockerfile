# -----------------------------------------------------------------------------
# The everyday HSM-ROS2 image (hsm-ros2-gui:jazzy): the dev image plus the ROS 2
# desktop (rviz2, rqt and its plugins, turtlesim), OpenGL/Mesa and the X11/Wayland
# Qt platforms. It is per user: the host user (name, uid, gid, home) is created
# inside, so the bind-mounted sources keep their owner and paths. Run it as a
# persistent container with run-gui.sh.
# -----------------------------------------------------------------------------
ARG BASE_IMAGE=hsm-ros2-dev:jazzy
FROM ${BASE_IMAGE}

ARG ROS_DISTRO=jazzy
ARG USERNAME=hsm
ARG USER_UID=1000
ARG USER_GID=1000
ARG USER_HOME=/home/hsm

# the desktop is the largest download: retried, and the .debs of a failed attempt
# stay in the apt cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    retry sh -c "apt-get update && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-desktop \
        mesa-utils libgl1-mesa-dri libglx-mesa0 libegl1 \
        qtwayland5 libxcb-cursor0 xauth x11-xserver-utils \
        fonts-dejavu-core fonts-liberation fonts-noto-core \
        sudo bash-completion nano vim openssh-client"

# the host user replaces a stock one of the same uid/gid (ubuntu, 1000)
RUN old=$(getent passwd "${USER_UID}" | cut -d: -f1); \
    if [ -n "$old" ]; then userdel -r "$old" 2>/dev/null || userdel "$old"; fi; \
    old=$(getent group "${USER_GID}" | cut -d: -f1); \
    if [ -n "$old" ]; then groupdel "$old"; fi; \
    groupadd -g "${USER_GID}" "${USERNAME}" \
    && useradd -m -d "${USER_HOME}" -u "${USER_UID}" -g "${USER_GID}" \
        -G sudo,video -s /bin/bash "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/hsm-ros2 \
    && chmod 0440 /etc/sudoers.d/hsm-ros2

COPY hsm-ros2-init /usr/local/bin/hsm-ros2-init

# rviz2 (Ogre) needs xcb; run-gui.sh --wayland switches the rest to wayland
ENV QT_QPA_PLATFORM=xcb

USER ${USERNAME}
WORKDIR ${USER_HOME}

# the persistent container idles; run-gui.sh execs the shells and the GUIs
CMD ["sleep", "infinity"]
