# -----------------------------------------------------------------------------
# The clean HSM-ROS2 test image (hsm-ros2-test:jazzy) and the base of the dev
# image: Ubuntu 24.04 with the ROS 2 Jazzy core, colcon and rosdep only. The
# package dependencies and the toolchain .debs are installed per run by
# test-docker.sh, so a dependency missing in a package.xml fails the test.
#
#   docker build -t hsm-ros2-test:jazzy docker/test    (see build-images.sh)
# -----------------------------------------------------------------------------
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION}

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC LANG=C.UTF-8

# the country apt mirror (only the host is swapped; "" keeps the stock sources)
ARG APT_MIRROR_HOST=ru.archive.ubuntu.com
ARG ROS_DISTRO=jazzy
ARG ROS_APT_SOURCE_VERSION=1.1.0

# the ROS 2 apt repository comes with the ros2-apt-source package (key + source);
# ros-dev-tools gives colcon, rosdep, vcstool and the compiler; ru_RU.UTF-8 is
# generated for the editor's locale-dependent output
RUN if [ -n "${APT_MIRROR_HOST}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do \
            if [ -f "$f" ]; then \
                sed -i -E "s@https?://(archive|security|ports)\.ubuntu\.com@http://${APT_MIRROR_HOST}@g" "$f"; \
            fi; \
        done; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl locales tzdata \
    && codename=$(. /etc/os-release && echo "$VERSION_CODENAME") \
    && curl -fsSL -o /tmp/ros2-apt-source.deb \
        "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${codename}_all.deb" \
    && apt-get install -y /tmp/ros2-apt-source.deb \
    && rm -f /tmp/ros2-apt-source.deb \
    && apt-get update && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-ros-core ros-dev-tools \
    && sed -i -E '/(en_US|ru_RU)\.UTF-8/s/^# //' /etc/locale.gen \
    && locale-gen \
    && rosdep init && rosdep update --rosdistro "${ROS_DISTRO}" \
    && rm -rf /var/lib/apt/lists/*

# the tests (the editor, turtlesim) run headless
ENV ROS_DISTRO=${ROS_DISTRO} QT_QPA_PLATFORM=offscreen

CMD ["/bin/bash"]
