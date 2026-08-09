# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 wheels module implementation
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

import hsm_robot.constants
import hsm_interfaces.msg
import hsm_interfaces.srv

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

class ROSWheels(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_wheels'
    STOP_SERVICE = 'hsm_ros_wheels_stop'
    FORWARD_SERVICE = 'hsm_ros_wheels_forward'
    BACK_SERVICE = 'hsm_ros_wheels_back'
    TURN_RIGHT_SERVICE = 'hsm_ros_wheels_turn_right'
    TURN_LEFT_SERVICE = 'hsm_ros_wheels_turn_left'
    VELOCITY_TOPIC = '/cmd_vel'
    LINEAR_SPEED_THRESHOLD = 0.001
    ANGULAR_SPEED_THRESHOLD = 0.001

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
        # the stop latch has to be ready before the odometry subscription is created,
        # otherwise an early /odom message reaches the callback before the attribute
        # exists; True means "no motion seen yet", so no STOP_COMPLETED is emitted
        # until the robot has actually moved
        self.__stopped = True
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
                                                       hsm_robot.constants.MSG_QUEUE_LEN)
        self.__msg_publisher = self.create_publisher(hsm_interfaces.msg.SimpleMessage,
                                                     hsm_robot.constants.MESSAGES_TOPIC,
                                                     hsm_robot.constants.MSG_QUEUE_LEN)
        self.__odom_subscriber = self.create_subscription(Odometry,
                                                          hsm_robot.constants.ODOMETRY_TOPIC,
                                                          self.odom_callback,
                                                          hsm_robot.constants.MSG_QUEUE_LEN)

        self.get_logger().info('ROSWheels service node initialized')

    def odom_callback(self, msg):
        # process odometry: the wheels module owns STOP_COMPLETED because the event
        # reports the state of the wheels, not of the navigation process
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        vz = msg.twist.twist.linear.z
        wx = msg.twist.twist.angular.x
        wy = msg.twist.twist.angular.y
        wz = msg.twist.twist.angular.z
        v = math.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
        if (abs(v) < self.LINEAR_SPEED_THRESHOLD and
            abs(wx) < self.ANGULAR_SPEED_THRESHOLD and
            abs(wy) < self.ANGULAR_SPEED_THRESHOLD and
            abs(wz) < self.ANGULAR_SPEED_THRESHOLD):
            if not self.__stopped:
                event = hsm_interfaces.msg.SimpleMessage()
                event.code = hsm_interfaces.msg.SimpleMessage.MSG_WHEELS_STOP_COMPLETED
                self.__msg_publisher.publish(event)
                self.get_logger().info('ROSWheels MSG_WHEELS_STOP_COMPLETED')
                self.__stopped = True
        else:
            self.__stopped = False

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
        msg.angular.z = -request.w
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response

    def on_turn_left_call(self, request, response):
        # Wheels.turn_left implementation
        self.get_logger().info('Wheels.turn_left({})'.format(request.w))
        msg = Twist()
        msg.angular.z = request.w
        self.__twist_publisher.publish(msg)
        response.ok = True
        return response

def main(args=None):
    rclpy.init(args=args)
    node = ROSWheels()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == "__main__":
    main()
