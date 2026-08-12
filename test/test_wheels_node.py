# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 contract of the wheels module node
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

import pytest

from geometry_msgs.msg import Twist

from conftest import ODOMETRY_TOPIC, VELOCITY_TOPIC, odometry
from hsm_interfaces.msg import SimpleMessage
from hsm_interfaces.srv import (WheelsBack, WheelsForward, WheelsStop, WheelsTurnLeft,
                                WheelsTurnRight)
from hsm_robot.wheels import ROSWheels

STOP_COMPLETED = SimpleMessage.MSG_WHEELS_STOP_COMPLETED

pytestmark = pytest.mark.node


def drive(probe, service, service_type, **fields):
    request = service_type.Request()
    for name, value in fields.items():
        setattr(request, name, float(value))
    return probe.call(service, service_type, request)


def test_forward_drives_ahead(node_factory):
    ctx = node_factory(ROSWheels)
    twists = ctx.probe.record(VELOCITY_TOPIC, Twist)
    assert drive(ctx.probe, 'hsm_ros_wheels_forward', WheelsForward, v=0.7).ok
    assert ctx.probe.wait_for(lambda: len(twists) == 1)
    assert twists[0].linear.x == pytest.approx(0.7)


def test_back_drives_backwards(node_factory):
    ctx = node_factory(ROSWheels)
    twists = ctx.probe.record(VELOCITY_TOPIC, Twist)
    assert drive(ctx.probe, 'hsm_ros_wheels_back', WheelsBack, v=0.7).ok
    assert ctx.probe.wait_for(lambda: len(twists) == 1)
    # the speed of the request is positive and the module turns it into the direction
    assert twists[0].linear.x == pytest.approx(-0.7)


def test_turn_right_is_clockwise(node_factory):
    ctx = node_factory(ROSWheels)
    twists = ctx.probe.record(VELOCITY_TOPIC, Twist)
    assert drive(ctx.probe, 'hsm_ros_wheels_turn_right', WheelsTurnRight, w=1.5).ok
    assert ctx.probe.wait_for(lambda: len(twists) == 1)
    assert twists[0].angular.z == pytest.approx(-1.5)


def test_turn_left_is_counter_clockwise(node_factory):
    ctx = node_factory(ROSWheels)
    twists = ctx.probe.record(VELOCITY_TOPIC, Twist)
    assert drive(ctx.probe, 'hsm_ros_wheels_turn_left', WheelsTurnLeft, w=1.5).ok
    assert ctx.probe.wait_for(lambda: len(twists) == 1)
    assert twists[0].angular.z == pytest.approx(1.5)


def test_stop_commands_no_speed(node_factory):
    ctx = node_factory(ROSWheels)
    twists = ctx.probe.record(VELOCITY_TOPIC, Twist)
    assert ctx.probe.call('hsm_ros_wheels_stop', WheelsStop).ok
    assert ctx.probe.wait_for(lambda: len(twists) == 1)
    assert twists[0] == Twist()


def test_stopping_is_reported(node_factory):
    ctx = node_factory(ROSWheels)
    # the module reports the stopping and not the state of being stopped, so the robot
    # has to be seen moving first
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.5))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.0))
    ctx.probe.wait_for_event(STOP_COMPLETED)


def test_stopping_is_reported_once(node_factory):
    ctx = node_factory(ROSWheels)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.5))
    for _ in range(4):
        ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.0))
    ctx.probe.spin(0.2)
    assert ctx.probe.count_events(STOP_COMPLETED) == 1


def test_a_robot_which_never_moved_reports_nothing(node_factory):
    ctx = node_factory(ROSWheels)
    # the module starts latched, so a robot standing still from the beginning does not
    # report a stop it never made
    for _ in range(3):
        ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.0))
    ctx.probe.expect_no_event(STOP_COMPLETED)


def test_moving_again_arms_the_report(node_factory):
    ctx = node_factory(ROSWheels)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.5))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.0))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.5))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.0))
    ctx.probe.spin(0.2)
    assert ctx.probe.count_events(STOP_COMPLETED) == 2


def test_turning_counts_as_moving(node_factory):
    ctx = node_factory(ROSWheels)
    # the robot which only turns is moving as well, so stopping the turn is reported
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(wz=0.8))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(wz=0.0))
    ctx.probe.wait_for_event(STOP_COMPLETED)


def test_the_speed_threshold_is_a_parameter(node_factory):
    ctx = node_factory(ROSWheels, linear_speed_threshold=1.0)
    # with this threshold the robot counts as stopped while it still moves slowly
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=2.0))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(vx=0.5))
    ctx.probe.wait_for_event(STOP_COMPLETED)
