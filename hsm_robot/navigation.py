# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 navigation module implementation
#
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

import rclpy
import rclpy.node

from geometry_msgs.msg import PoseStamped, Odometry

import hsm_robot.constants
import hsm_interfaces.msg
import hsm_interfaces.srv

class ROSNavigation(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_navigation'
    MOVE_TO_POINT_SERVICE = 'hsm_ros_navigation_move_to_point'
    STOP_SERVICE = 'hsm_ros_navigation_stop'
    NAVIGATION_MODULE_TOPIC = '/goal_pose'
    STOP_MESSAGE_FRAME_ID = '__CANCEL_NAV__'

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
                                                      hsm_robot.constants.QUEUE_LEN)
        self.__odom_subscriber = self.create_subscription(Odometry,
                                                          hsm_robot.constants.ODOMETRY_TOPIC,
                                                          self.odom_callback,
                                                          MSG_QUEUE_LEN)
        self.get_logger().info('ROSNavigation service node initialized')

    def __path_found(self):
        msg = hsm_interfaces.msg.SimpleMessage()        
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_NAVIGATION_PATH_FOUND
        self.__msg_publisher.publish(msg)

    def odom_callback(self, msg):
        # process odometry
        pass

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
