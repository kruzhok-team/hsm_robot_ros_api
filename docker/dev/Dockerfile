# -----------------------------------------------------------------------------
# The HSM-ROS2 build and test image (hsm-ros2-dev:jazzy): the clean test image
# plus every build/test dependency of the HSM-ROS2 packages and the Cyberiada
# toolchain (the libraries, the python binding, CyberiadaPro). build-images.sh
# stages the toolchain .debs into debs/ of the build context.
# -----------------------------------------------------------------------------
ARG BASE_IMAGE=hsm-ros2-test:jazzy
FROM ${BASE_IMAGE}

ARG ROS_DISTRO=jazzy

COPY debs/ /tmp/hsm-debs/

# the package.xml dependencies of hsm_interfaces, hsm_robot, hsm_generator,
# turtle_driver, hsm_test_utils and hsm_tests, the debugging tools of the shell
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-ros-base \
        ros-${ROS_DISTRO}-ament-cmake \
        ros-${ROS_DISTRO}-ament-lint-auto ros-${ROS_DISTRO}-ament-lint-common \
        ros-${ROS_DISTRO}-ament-flake8 ros-${ROS_DISTRO}-ament-pep257 \
        ros-${ROS_DISTRO}-rosidl-default-generators ros-${ROS_DISTRO}-rosidl-default-runtime \
        ros-${ROS_DISTRO}-geometry-msgs ros-${ROS_DISTRO}-nav-msgs \
        ros-${ROS_DISTRO}-sensor-msgs ros-${ROS_DISTRO}-std-msgs \
        ros-${ROS_DISTRO}-launch ros-${ROS_DISTRO}-launch-ros \
        ros-${ROS_DISTRO}-launch-testing ros-${ROS_DISTRO}-launch-testing-ros \
        ros-${ROS_DISTRO}-ament-index-python \
        ros-${ROS_DISTRO}-turtlesim \
        python3-pytest python3-pytest-timeout python3-transforms3d \
        git gdb less vim-tiny \
        /tmp/hsm-debs/*.deb \
    && rm -rf /tmp/hsm-debs /var/lib/apt/lists/*

# ROS 2 and the workspace ($HSM_ROS2_WS) in every shell
COPY hsm-ros2-env.sh /etc/profile.d/hsm-ros2-env.sh
RUN echo '. /etc/profile.d/hsm-ros2-env.sh' >> /etc/bash.bashrc

CMD ["/bin/bash", "-l"]
