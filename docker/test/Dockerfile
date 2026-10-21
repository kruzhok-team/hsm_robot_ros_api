# -----------------------------------------------------------------------------
# The clean HSM-ROS2 test image (hsm-ros2-test:jazzy) and the base of the dev
# image: Ubuntu 24.04 with the ROS 2 Jazzy core, colcon and rosdep only. The
# package dependencies and the toolchain .debs are installed per run by
# test-docker.sh, so a dependency missing in a package.xml fails the test.
#
#   docker build -t hsm-ros2-test:jazzy docker/test    (see build-images.sh)
#
# The network steps survive a flaky network: each is retried (retry, apt
# retries), each is a layer of its own (a rebuild continues after the last good
# one) and the downloaded .debs stay in the BuildKit apt cache between attempts.
# -----------------------------------------------------------------------------
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION}

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC LANG=C.UTF-8

# the country apt mirror (only the host is swapped; "" keeps the stock sources)
ARG APT_MIRROR_HOST=ru.archive.ubuntu.com
ARG ROS_DISTRO=jazzy
ARG ROS_APT_SOURCE_VERSION=1.1.0

COPY retry /usr/local/bin/retry

# apt retries with timeouts, fails an update on any unreachable index (so retry
# repeats it) and keeps the .debs for the cache mounts (no docker-clean)
RUN if [ -n "${APT_MIRROR_HOST}" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do \
            if [ -f "$f" ]; then \
                sed -i -E "s@https?://(archive|security|ports)\.ubuntu\.com@http://${APT_MIRROR_HOST}@g" "$f"; \
            fi; \
        done; \
    fi \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && printf '%s\n' \
        'Acquire::Retries "10";' \
        'Acquire::http::Timeout "30";' \
        'Acquire::https::Timeout "30";' \
        'APT::Update::Error-Mode "any";' \
        'Binary::apt::APT::Keep-Downloaded-Packages "true";' \
        > /etc/apt/apt.conf.d/80-hsm-network

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    retry sh -c "apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl locales tzdata"

# the ROS 2 apt repository comes with the ros2-apt-source package (key + source)
RUN codename=$(. /etc/os-release && echo "$VERSION_CODENAME") \
    && retry curl -fsSL --connect-timeout 30 -o /tmp/ros2-apt-source.deb \
        "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${codename}_all.deb" \
    && dpkg -i /tmp/ros2-apt-source.deb \
    && rm -f /tmp/ros2-apt-source.deb

# ros-dev-tools gives colcon, rosdep, vcstool and the compiler
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    retry sh -c "apt-get update && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-ros-core ros-dev-tools"

# ru_RU.UTF-8 for the editor's locale-dependent output
RUN sed -i -E '/(en_US|ru_RU)\.UTF-8/s/^# //' /etc/locale.gen && locale-gen

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then retry rosdep init; fi \
    && retry rosdep update --rosdistro "${ROS_DISTRO}"

# the tests (the editor, turtlesim) run headless
ENV ROS_DISTRO=${ROS_DISTRO} QT_QPA_PLATFORM=offscreen

CMD ["/bin/bash"]
