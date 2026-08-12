# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 pump module implementation
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

import rclpy
import rclpy.node
from rclpy.executors import ExternalShutdownException

import hsm_robot.constants
from hsm_robot.parameters import declare
import hsm_interfaces.srv

from std_msgs.msg import Bool


class ROSPump(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_pump'
    TURN_ON_SERVICE = 'hsm_ros_pump_turn_on'
    TURN_OFF_SERVICE = 'hsm_ros_pump_turn_off'

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
        queue_length = declare(
            self, 'message_queue_length', hsm_robot.constants.MSG_QUEUE_LEN,
            'the length of the ROS2 message queues')
        self.__service_turn_on = self.create_service(hsm_interfaces.srv.PumpTurnOn,
                                                     self.TURN_ON_SERVICE,
                                                     self.on_turn_on_call)
        self.__service_turn_off = self.create_service(hsm_interfaces.srv.PumpTurnOff,
                                                      self.TURN_OFF_SERVICE,
                                                      self.on_turn_off_call)
        self.__pump_publisher = self.create_publisher(Bool,
                                                      hsm_robot.constants.PUMP_TOPIC,
                                                      queue_length)

        self.get_logger().info('ROSPump service node initialized')

    def __publish_pump_state(self, state):
        msg = Bool()
        msg.data = state
        self.__pump_publisher.publish(msg)

    def on_turn_on_call(self, request, response):
        # Pump.turn_on implementation
        self.get_logger().info('Pump.turn_on()')
        self.__publish_pump_state(True)
        response.ok = True
        return response

    def on_turn_off_call(self, request, response):
        # Pump.turn_off implementation
        self.get_logger().info('Pump.turn_off()')
        self.__publish_pump_state(False)
        response.ok = True
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ROSPump()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
