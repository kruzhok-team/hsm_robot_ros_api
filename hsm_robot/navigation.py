# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 navigation module implementation
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

import math
import rclpy
import rclpy.node
from rclpy.executors import ExternalShutdownException

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

import hsm_robot.constants
import hsm_interfaces.msg
import hsm_interfaces.srv


class ROSNavigation(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_navigation'
    MOVE_TO_POINT_SERVICE = 'hsm_ros_navigation_move_to_point'
    STOP_SERVICE = 'hsm_ros_navigation_stop'
    NAVIGATION_MODULE_TOPIC = '/goal_pose'
    STOP_MESSAGE_FRAME_ID = '__CANCEL_NAV__'
    OBSTACLE_RANGE = 0.45
    OPEN_SPACE_RANGE = 0.5
    SCAN_WINDOW = 0.0873  # +/- 5 degrees around the inspected scan direction

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
        # the goal has to be ready before the odometry subscription is created, otherwise
        # an early /odom message reaches the callback before the attribute exists;
        # None means "no target requested", so MOVE_COMPLETED is emitted only after an
        # actual move_to_point call
        self.__goal = None
        self.__msg_publisher = self.create_publisher(hsm_interfaces.msg.SimpleMessage,
                                                     hsm_robot.constants.MESSAGES_TOPIC,
                                                     hsm_robot.constants.MSG_QUEUE_LEN)
        self.__service_move_to_point = self.create_service(hsm_interfaces.srv.NavigationMoveToPoint,
                                                           self.MOVE_TO_POINT_SERVICE,
                                                           self.on_move_to_point_call)
        self.__service_stop = self.create_service(hsm_interfaces.srv.NavigationStop,
                                                  self.STOP_SERVICE,
                                                  self.on_stop_call)
        self.__goal_publisher = self.create_publisher(PoseStamped,
                                                      self.NAVIGATION_MODULE_TOPIC,
                                                      hsm_robot.constants.MSG_QUEUE_LEN)
        self.__odom_subscriber = self.create_subscription(Odometry,
                                                          hsm_robot.constants.ODOMETRY_TOPIC,
                                                          self.odom_callback,
                                                          hsm_robot.constants.MSG_QUEUE_LEN)
        self.__scan_subscriber = self.create_subscription(LaserScan,
                                                          hsm_robot.constants.LASER_TOPIC,
                                                          self.scan_callback,
                                                          hsm_robot.constants.MSG_QUEUE_LEN)
        self.get_logger().info('ROSNavigation service node initialized')

    def __path_found(self):
        msg = hsm_interfaces.msg.SimpleMessage()
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_PATH_FOUND
        self.__msg_publisher.publish(msg)

    def odom_callback(self, msg):
        # process odometry: the target point is reached when the robot comes closer to it
        # than GOAL_TOLERANCE. The wheels module reports STOP_COMPLETED on its own, so
        # only the movement goal is tracked here
        if self.__goal is None:
            return
        goal_x, goal_y = self.__goal
        dx = goal_x - msg.pose.pose.position.x
        dy = goal_y - msg.pose.pose.position.y
        if math.sqrt(dx ** 2 + dy ** 2) > hsm_robot.constants.GOAL_TOLERANCE:
            return
        # the goal is dropped before the event is published, so the arrival is reported
        # once per move_to_point call and not on every odometry message that follows
        self.__goal = None
        event = hsm_interfaces.msg.SimpleMessage()
        event.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_MOVE_COMPLETED
        self.__msg_publisher.publish(event)
        self.get_logger().info('ROSNavigation MSG_NAVIGATION_MOVE_COMPLETED')

    def __beam_min(self, msg, angle):
        # the smallest valid range within +/- SCAN_WINDOW around the requested angle;
        # the indices are derived from the scan header instead of being hardcoded, so
        # the result does not depend on the scanner orientation
        # returns None when the sector carries no valid measurement
        if msg.angle_increment == 0.0:
            return None
        check_limits = msg.range_max > msg.range_min
        half = max(1, int(self.SCAN_WINDOW / abs(msg.angle_increment)))
        center = int(round((angle - msg.angle_min) / msg.angle_increment))
        result = None
        for i in range(center - half, center + half + 1):
            if i < 0 or i >= len(msg.ranges):
                continue
            distance = msg.ranges[i]
            # inf marks "no return" and nan marks an invalid beam: both must be dropped,
            # otherwise inf compares greater than every threshold and nan silently
            # makes each comparison false
            if not math.isfinite(distance):
                continue
            if check_limits and (distance < msg.range_min or distance > msg.range_max):
                continue
            if result is None or distance < result:
                result = distance
        return result

    def scan_callback(self, msg):
        # process laser scan
        if not msg.ranges:
            return
        center_dist = self.__beam_min(msg, 0.0)
        right_dist = self.__beam_min(msg, -math.pi / 2.0)
        self.get_logger().info('cent={} right={}'.format(center_dist, right_dist),
                               throttle_duration_sec=1.0)

        if right_dist is not None and right_dist > self.OPEN_SPACE_RANGE:
            event = hsm_interfaces.msg.SimpleMessage()
            event.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_RIGHT_OPEN_SPACE
            self.__msg_publisher.publish(event)
            self.get_logger().info('ROSNavigation MSG_NAVIGATION_RIGHT_OPEN_SPACE')

        if center_dist is None:
            return

        if center_dist < self.OBSTACLE_RANGE / 3:
            event = hsm_interfaces.msg.SimpleMessage()
            event.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_COLLISION_DETECTED
            self.__msg_publisher.publish(event)
            self.get_logger().info('ROSNavigation MSG_NAVIGATION_COLLISION_DETECTED')
        elif center_dist < self.OBSTACLE_RANGE:
            event = hsm_interfaces.msg.SimpleMessage()
            event.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_COLLISION_WARNING
            self.__msg_publisher.publish(event)
            self.get_logger().info('ROSNavigation MSG_NAVIGATION_COLLISION_WARNING')

    def on_move_to_point_call(self, request, response):
        # Navigation.move_to_point implementation
        pose = request.pose
        self.get_logger().info('Navigation.move_to_point({})'.format(pose))
        self.__goal = (pose.pose.position.x, pose.pose.position.y)
        self.__goal_publisher.publish(pose)
        response.ok = True
        return response

    def on_stop_call(self, request, response):
        # Navigation.stop implementation
        self.get_logger().info('Navigation.stop()')
        # a cancelled movement must not report MOVE_COMPLETED later, even if the robot
        # coasts into the abandoned target point
        self.__goal = None
        empty_pose = PoseStamped()
        empty_pose.header.frame_id = self.STOP_MESSAGE_FRAME_ID
        self.__goal_publisher.publish(empty_pose)
        response.ok = True
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ROSNavigation()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
