# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 implementation constants
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
# Copyright (C) 2026 Anastasia Viktorova <viktorovaa.04@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

# the ROS2 topic for HSM messages
MESSAGES_TOPIC = '/hsm_ros_msg'
# the ROS2 topic for HSM messages with the single string argument
STR_MESSAGES_TOPIC = '/hsm_ros_str_msg'
# the ROS2 odometry topic
ODOMETRY_TOPIC = '/odom'
# the ROS2 laser scan topic
LASER_TOPIC = '/scan'
# the ROS2 pump control topic
PUMP_TOPIC = '/pump'
# the ROS2 frame for HSM messages
FRAME_ID = 'hsm_ros_api'
# the ROS2 messages queue length
MSG_QUEUE_LEN = 10
# loop timer
LOOP_TIME = 0.05
# tick event timer
TICK_LEN = 0.1
# the default timer name
DEFAULT_TIMER = 'default'
# the distance to the target point (m) which is close enough to report
# MOVE_COMPLETED; retune it for the particular robot platform
GOAL_TOLERANCE = 0.05
# the local long-term storage directory
STORAGE_PATH = '~/.hsm_robot/storage'
