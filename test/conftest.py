# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The fixtures of the module node tests
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
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

# The fixtures come from the test utilities of the framework, so the node tests of this
# package and the integration tests share one vocabulary. They are imported here to be
# visible to pytest.

from hsm_test_utils import (isolated_domain, node_factory,  # noqa: F401
                            storage_directory)

from nav_msgs.msg import Odometry

ODOMETRY_TOPIC = '/odom'
LASER_TOPIC = '/scan'
MESSAGES_TOPIC = '/hsm_ros_msg'
STR_MESSAGES_TOPIC = '/hsm_ros_str_msg'
VELOCITY_TOPIC = '/cmd_vel'
GOAL_TOPIC = '/goal_pose'
PUMP_TOPIC = '/pump'


def odometry(x=0.0, y=0.0, vx=0.0, wz=0.0):
    # the odometry message the modules read: the position for the navigation module and
    # the speed for the wheels module
    msg = Odometry()
    msg.pose.pose.position.x = float(x)
    msg.pose.pose.position.y = float(y)
    msg.twist.twist.linear.x = float(vx)
    msg.twist.twist.angular.z = float(wz)
    return msg
