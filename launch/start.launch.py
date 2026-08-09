#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    debug_node = Node(
        package='hsm_robot',
        executable='debug_node',
        name='debug_node'
    )
    timer_node = Node(
        package='hsm_robot',
        executable='timer_node',
        name='timer_node'
    )
    wheels_node = Node(
        package='hsm_robot',
        executable='wheels_node',
        name='wheels_node'
    )
    navigation_node = Node(
        package='hsm_robot',
        executable='navigation_node',
        name='navigation_node'
    )
    pump_node = Node(
        package='hsm_robot',
        executable='pump_node',
        name='pump_node'
    )
    storage_node = Node(
        package='hsm_robot',
        executable='storage_node',
        name='storage_node'
    )

    return LaunchDescription([
        debug_node, timer_node, wheels_node, navigation_node,
        pump_node, storage_node
    ])
