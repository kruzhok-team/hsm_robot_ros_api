#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# The nodes are not renamed here: every node is called the way it names itself, so it has
# the same name whether it is started by this file or by ros2 run, and one block of the
# parameter file applies to it in both cases.
EXECUTABLES = ('debug_node', 'timer_node', 'wheels_node', 'navigation_node',
               'pump_node', 'storage_node')


def generate_launch_description():
    default_params = os.path.join(get_package_share_directory('hsm_robot'),
                                  'config', 'default_params.yaml')
    params_file = LaunchConfiguration('params_file')
    declare_params_file = DeclareLaunchArgument(
        'params_file', default_value=default_params,
        description='the parameter file of the HSM robot API nodes')

    nodes = [Node(package='hsm_robot', executable=executable, parameters=[params_file])
             for executable in EXECUTABLES]
    return LaunchDescription([declare_params_file] + nodes)
