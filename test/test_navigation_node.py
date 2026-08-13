# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 contract of the navigation module node
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

import math

import pytest

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import LaserScan

from conftest import GOAL_TOPIC, ODOMETRY_TOPIC, LASER_TOPIC, odometry
from hsm_interfaces.msg import SimpleMessage
from hsm_interfaces.srv import NavigationMoveAlongTraj, NavigationMoveToPoint, NavigationStop
from hsm_robot.navigation import ROSNavigation

MOVE_COMPLETED = SimpleMessage.MSG_NAVIGATION_MOVE_COMPLETED
POINT_PASSED = SimpleMessage.MSG_NAVIGATION_POINT_PASSED
COLLISION_WARNING = SimpleMessage.MSG_NAVIGATION_COLLISION_WARNING
COLLISION_DETECTED = SimpleMessage.MSG_NAVIGATION_COLLISION_DETECTED
RIGHT_OPEN_SPACE = SimpleMessage.MSG_NAVIGATION_RIGHT_OPEN_SPACE

pytestmark = pytest.mark.node


def scan(forward=10.0, right=10.0, other=10.0):
    # a full circle of beams, one degree apart, with the forward and the right sectors set
    # separately. The module derives the indices from the header, so the header has to be
    # consistent with the ranges
    msg = LaserScan()
    msg.angle_min = -math.pi
    msg.angle_max = math.pi
    msg.angle_increment = math.pi / 180.0
    msg.range_min = 0.05
    msg.range_max = 20.0
    count = 360
    msg.ranges = [float(other)] * count
    forward_index = int(round((0.0 - msg.angle_min) / msg.angle_increment))
    right_index = int(round((-math.pi / 2.0 - msg.angle_min) / msg.angle_increment))
    for index in range(forward_index - 10, forward_index + 11):
        msg.ranges[index] = float(forward)
    for index in range(right_index - 10, right_index + 11):
        msg.ranges[index] = float(right)
    return msg


def move_to(probe, x, y):
    request = NavigationMoveToPoint.Request()
    request.pose.pose.position.x = float(x)
    request.pose.pose.position.y = float(y)
    return probe.call('hsm_ros_navigation_move_to_point', NavigationMoveToPoint, request)


def move_along(probe, points):
    request = NavigationMoveAlongTraj.Request()
    poses = []
    for x, y in points:
        pose = PoseStamped()
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        poses.append(pose)
    request.poses = poses
    return probe.call('hsm_ros_navigation_move_along_traj', NavigationMoveAlongTraj, request)


def test_move_to_point_publishes_the_goal(node_factory):
    ctx = node_factory(ROSNavigation)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    assert move_to(ctx.probe, 2.0, 7.0).ok
    assert ctx.probe.wait_for(lambda: len(goals) == 1)
    assert (goals[0].pose.position.x, goals[0].pose.position.y) == (2.0, 7.0)


def test_stop_publishes_the_cancellation(node_factory):
    ctx = node_factory(ROSNavigation)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    assert ctx.probe.call('hsm_ros_navigation_stop', NavigationStop).ok
    assert ctx.probe.wait_for(lambda: len(goals) == 1)
    # the driver of the platform recognises the cancellation by the frame identifier
    assert goals[0].header.frame_id == ROSNavigation.STOP_MESSAGE_FRAME_ID


def test_arrival_reports_move_completed(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    move_to(ctx.probe, 1.0, 0.0)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=0.9))
    ctx.probe.wait_for_event(MOVE_COMPLETED)


def test_arrival_is_reported_once(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    move_to(ctx.probe, 1.0, 0.0)
    for _ in range(4):
        ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=1.0))
    ctx.probe.spin(0.2)
    # the goal is dropped when it is reached, so the arrival is reported once per request
    # and not on every odometry message which follows
    assert ctx.probe.count_events(MOVE_COMPLETED) == 1


def test_no_arrival_without_a_request(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=0.0))
    ctx.probe.expect_no_event(MOVE_COMPLETED)


def test_distant_odometry_reports_nothing(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.1)
    move_to(ctx.probe, 5.0, 5.0)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=0.0, y=0.0))
    ctx.probe.expect_no_event(MOVE_COMPLETED)


def test_stop_cancels_the_arrival(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    move_to(ctx.probe, 1.0, 0.0)
    ctx.probe.call('hsm_ros_navigation_stop', NavigationStop)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=1.0))
    ctx.probe.expect_no_event(MOVE_COMPLETED)


def test_a_trajectory_starts_with_its_first_point(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    assert move_along(ctx.probe, [(1.0, 0.0), (2.0, 0.0)]).ok
    # the driver of the platform always sees a single goal: the rest of the trajectory
    # stays in the module until the robot arrives
    assert ctx.probe.wait_for(lambda: len(goals) == 1)
    assert (goals[0].pose.position.x, goals[0].pose.position.y) == (1.0, 0.0)


def test_a_passed_point_publishes_the_next_goal(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    move_along(ctx.probe, [(1.0, 0.0), (2.0, 0.0)])
    assert ctx.probe.wait_for(lambda: len(goals) == 1)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=1.0))
    ctx.probe.wait_for_event(POINT_PASSED)
    assert ctx.probe.wait_for(lambda: len(goals) == 2)
    assert (goals[1].pose.position.x, goals[1].pose.position.y) == (2.0, 0.0)
    # the route is not over while a point is left
    assert ctx.probe.count_events(MOVE_COMPLETED) == 0


def test_the_last_point_completes_the_movement(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    move_along(ctx.probe, [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])
    for point in range(1, 4):
        assert ctx.probe.wait_for(lambda expected=point: len(goals) == expected)
        ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=float(point)))
        assert ctx.probe.wait_for(
            lambda expected=point: ctx.probe.count_events(POINT_PASSED) == expected)
    ctx.probe.wait_for_event(MOVE_COMPLETED)
    # every point of the route is reported, and the completion once after the last one
    assert ctx.probe.count_events(POINT_PASSED) == 3
    assert ctx.probe.count_events(MOVE_COMPLETED) == 1
    assert len(goals) == 3


def test_move_to_point_reports_no_passed_point(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    move_to(ctx.probe, 1.0, 0.0)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=1.0))
    ctx.probe.wait_for_event(MOVE_COMPLETED)
    # a passed point belongs to a trajectory: a single movement is completed, not passed
    assert ctx.probe.count_events(POINT_PASSED) == 0


def test_stop_cancels_the_rest_of_the_trajectory(node_factory):
    ctx = node_factory(ROSNavigation, goal_tolerance=0.5)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    move_along(ctx.probe, [(1.0, 0.0), (2.0, 0.0)])
    assert ctx.probe.wait_for(lambda: len(goals) == 1)
    ctx.probe.call('hsm_ros_navigation_stop', NavigationStop)
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=1.0))
    ctx.probe.publish(ODOMETRY_TOPIC, odometry(x=2.0))
    ctx.probe.expect_no_event(POINT_PASSED)
    assert ctx.probe.count_events(MOVE_COMPLETED) == 0


def test_an_empty_trajectory_completes_at_once(node_factory):
    ctx = node_factory(ROSNavigation)
    goals = ctx.probe.record(GOAL_TOPIC, PoseStamped)
    assert move_along(ctx.probe, []).ok
    # there is nothing to travel, and a diagram waiting for the completion has to be
    # released instead of waiting for an event which can never arrive
    ctx.probe.wait_for_event(MOVE_COMPLETED)
    assert ctx.probe.count_events(POINT_PASSED) == 0
    assert goals == []


def test_close_obstacle_reports_a_collision(node_factory):
    ctx = node_factory(ROSNavigation, collision_range=0.15, obstacle_range=0.45)
    ctx.probe.publish(LASER_TOPIC, scan(forward=0.1))
    ctx.probe.wait_for_event(COLLISION_DETECTED)


def test_near_obstacle_reports_a_warning(node_factory):
    ctx = node_factory(ROSNavigation, collision_range=0.15, obstacle_range=0.45)
    ctx.probe.publish(LASER_TOPIC, scan(forward=0.3))
    ctx.probe.wait_for_event(COLLISION_WARNING)
    # the collision is reported instead of the warning and not in addition to it
    assert ctx.probe.count_events(COLLISION_DETECTED) == 0


def test_free_space_reports_neither(node_factory):
    ctx = node_factory(ROSNavigation, obstacle_range=0.45, open_space_range=100.0)
    ctx.probe.publish(LASER_TOPIC, scan(forward=5.0))
    ctx.probe.expect_no_event(COLLISION_WARNING)
    assert ctx.probe.count_events(COLLISION_DETECTED) == 0


def test_free_space_on_the_right_is_reported(node_factory):
    ctx = node_factory(ROSNavigation, open_space_range=0.5)
    ctx.probe.publish(LASER_TOPIC, scan(right=3.0))
    ctx.probe.wait_for_event(RIGHT_OPEN_SPACE)


def test_the_scan_events_are_reported_for_every_scan(node_factory):
    ctx = node_factory(ROSNavigation, collision_range=0.15)
    for _ in range(3):
        ctx.probe.publish(LASER_TOPIC, scan(forward=0.1))
    ctx.probe.spin(0.2)
    # the obstacle events report the state of the scan and are not latched: an obstacle
    # which does not move is reported by every scan message
    assert ctx.probe.count_events(COLLISION_DETECTED) == 3


def test_an_empty_scan_reports_nothing(node_factory):
    ctx = node_factory(ROSNavigation)
    empty = scan()
    empty.ranges = []
    ctx.probe.publish(LASER_TOPIC, empty)
    ctx.probe.expect_no_event(COLLISION_DETECTED)
    assert ctx.probe.event_codes() == []


def test_invalid_beams_are_ignored(node_factory):
    ctx = node_factory(ROSNavigation, collision_range=0.15, obstacle_range=0.45)
    # a beam without a return is infinite and an invalid one is not a number: taken as
    # distances they would be closer than every threshold or silently disable the checks
    invalid = scan(forward=float('inf'))
    invalid.ranges[180] = float('nan')
    ctx.probe.publish(LASER_TOPIC, invalid)
    ctx.probe.expect_no_event(COLLISION_DETECTED)


def test_the_ranges_are_parameters(node_factory):
    ctx = node_factory(ROSNavigation, collision_range=2.0, obstacle_range=3.0)
    # a distance which is free with the defaults is a collision with these ranges
    ctx.probe.publish(LASER_TOPIC, scan(forward=1.0))
    ctx.probe.wait_for_event(COLLISION_DETECTED)
