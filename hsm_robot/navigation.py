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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

import math
import rclpy
import rclpy.node

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
    LINEAR_SPEED_THRESHOLD = 0.001
    ANGULAR_SPEED_THRESHOLD = 0.001

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
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
        self.__stopped = False

    def __path_found(self):
        msg = hsm_interfaces.msg.SimpleMessage()
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_PATH_FOUND
        self.__msg_publisher.publish(msg)

    def odom_callback(self, msg):
        # process odometry
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        vth = msg.twist.twist.linear.z
        wx = msg.twist.twist.angular.x
        wy = msg.twist.twist.angular.y
        wz = msg.twist.twist.angular.z
        # self.get_logger().info(f"vx={vx:.2f} vy={vy:.2f} vth={vth:.2f} wx={wx:.2f} wy={wy:.2f} wz={wz:.2f}")
        v = math.sqrt(vx ** vx + vy ** vy + vth ** vth)
        w = math.sqrt(wx ** wx + wy ** wy + wz ** wz)
        if abs(v) < self.LINEAR_SPEED_THRESHOLD and abs(w) < self.ANGULAR_SPEED_THRESHOLD:
            if not self.__stopped:
                msg = hsm_interfaces.msg.SimpleMessage()
                msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_STOP_COMPLETED
                self.__msg_publisher.publish(msg)
                self.get_logger().info('ROSNavigation MSG_NAVIGATION_STOP_COMPLETED')
                self.__stopped = True
        else:
            self.__stopped = False

    def scan_callback(self, msg):
        # process laser scan
        size = len(msg.ranges)
        center_dist = msg.ranges[size // 2]
        right_dist = msg.ranges[0]
        self.get_logger().info(f"cent={center_dist:.2f} right={right_dist:.2f}")

        if right_dist > self.OPEN_SPACE_RANGE:
            msg = hsm_interfaces.msg.SimpleMessage()
            msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_RIGHT_OPEN_SPACE
            self.__msg_publisher.publish(msg)
            self.get_logger().info('ROSNavigation MSG_NAVIGATION_RIGHT_OPEN_SPACE')

        if center_dist < self.OBSTACLE_RANGE / 3:
            msg = hsm_interfaces.msg.SimpleMessage()
            msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_COLLISION_DETECTED
            self.__msg_publisher.publish(msg)
            self.get_logger().info('ROSNavigation MSG_NAVIGATION_COLLISION_DETECTED')
        elif center_dist < self.OBSTACLE_RANGE:
            msg = hsm_interfaces.msg.SimpleMessage()
            msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_COLLISION_WARNING
            self.__msg_publisher.publish(msg)
            self.get_logger().info('ROSNavigation MSG_NAVIGATION_COLLISION_WARNING')

    def on_move_to_point_call(self, request, response):
        # Navigation.move_to_point implementation
        pose = request.pose
        self.get_logger().info('Navigation.move_to_point({})'.format(pose))
        self.__goal_publisher.publish(pose)
        response.ok = True
        return response

    def on_stop_call(self, request, response):
        # Navigation.stop implementation
        self.get_logger().info('Navigation.stop()')
        empty_pose = PoseStamped()
        empty_pose.header.frame_id = self.STOP_MESSAGE_FRAME_ID
        self.__goal_publisher.publish(empty_pose)
        response.ok = True
        return response

def main(args=None):
    rclpy.init(args=args)
    node = ROSNavigation()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
