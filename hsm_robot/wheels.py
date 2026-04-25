# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 wheels module implementation
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

import hsm_robot.constants
import hsm_interfaces.msg
import hsm_interfaces.srv

from geometry_msgs.msg import Twist

class ROSWheels(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_wheels'
    STOP_SERVICE = 'hsm_ros_wheels_stop'
    FORWARD_SERVICE = 'hsm_ros_wheels_forward'
    BACK_SERVICE = 'hsm_ros_wheels_back'
    TURN_RIGHT_SERVICE = 'hsm_ros_wheels_turn_right'
    TURN_LEFT_SERVICE = 'hsm_ros_wheels_turn_left'
    VELOCITY_TOPIC = '/cmd_vel'

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
        self.__service_stop = self.create_service(hsm_interfaces.srv.WheelsStop,
                                                  self.STOP_SERVICE,
                                                  self.on_stop_call)
        self.__service_forward = self.create_service(hsm_interfaces.srv.WheelsForward,
                                                     self.FORWARD_SERVICE,
                                                     self.on_forward_call)
        self.__service_back = self.create_service(hsm_interfaces.srv.WheelsBack,
                                                  self.BACK_SERVICE,
                                                  self.on_back_call)
        self.__service_turn_right = self.create_service(hsm_interfaces.srv.WheelsTurnRight,
                                                        self.TURN_RIGHT_SERVICE,
                                                        self.on_turn_right_call)
        self.__service_turn_left = self.create_service(hsm_interfaces.srv.WheelsTurnLeft,
                                                       self.TURN_LEFT_SERVICE,
                                                       self.on_turn_left_call)
        self.__twist_publisher = self.create_publisher(Twist,
                                                       self.VELOCITY_TOPIC,
                                                       hsm_robot.constants.QUEUE_LEN)

        self.get_logger().info('ROSWheels service node initialized')

    def on_stop_call(self, request, response):
        # Wheels.stop implementation
        self.get_logger().info('Wheels.stop()')
        msg = Twist()
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response

    def on_forward_call(self, request, response):
        # Wheels.stop implementation
        self.get_logger().info('Wheels.forward({})'.format(request.v))
        msg = Twist()
        msg.linear.x = request.v
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response

    def on_back_call(self, request, response):
        # Wheels.back implementation
        self.get_logger().info('Wheels.back({})'.format(request.v))
        msg = Twist()
        msg.linear.x = -request.v
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response
    
    def on_turn_right_call(self, request, response):
        # Wheels.turn_right implementation
        self.get_logger().info('Wheels.turn_right({})'.format(request.w))
        msg = Twist()
        msg.angular.z = request.w
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response

    def on_turn_left_call(self, request, response):
        # Wheels.turn_left implementation
        self.get_logger().info('Wheels.turn_left({})'.format(request.w))
        msg = Twist()
        msg.angular.z = -request.w
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response

def main(args=None):
    rclpy.init(args=args)
    node = ROSWheels()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
