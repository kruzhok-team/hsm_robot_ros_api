# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 timer module implementation
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

class ROSTimer(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_timer'
    TICK_SERVICE = 'hsm_ros_timer_init_ticks'
    START_SERVICE = 'hsm_ros_timer_start'
    STOP_SERVICE = 'hsm_ros_timer_stop'

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
        self.__msg_publisher = self.create_publisher(hsm_interfaces.msg.SimpleMessage,
                                                     hsm_robot.constants.MESSAGES_TOPIC,
                                                     hsm_robot.constants.MSG_QUEUE_LEN)
        self.__service_tick = self.create_service(hsm_interfaces.srv.TimerTicks,
                                                  self.TICK_SERVICE,
                                                  self.on_init_ticks_call)
        self.__service_start = self.create_service(hsm_interfaces.srv.TimerStart,
                                                   self.START_SERVICE,
                                                   self.on_start_call)
        self.__service_stop = self.create_service(hsm_interfaces.srv.TimerStop,
                                                  self.STOP_SERVICE,
                                                  self.on_stop_call)
        self._timer_repetable = False
        self.get_logger().info('ROSTimer service node initialized')

    def __tick_timer_callback(self):
        msg = hsm_interfaces.msg.SimpleMessage()
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_TIMER_TICK
        self.__msg_publisher.publish(msg)

    def __second_timer_callback(self):
        msg = hsm_interfaces.msg.SimpleMessage()
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_TIMER_TICK_1S
        self.__msg_publisher.publish(msg)

    def __minute_timer_callback(self):
        msg = hsm_interfaces.msg.SimpleMessage()        
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_TIMER_TICK_1M
        self.__msg_publisher.publish(msg)

    def __timer_elapsed(self):
        msg = hsm_interfaces.msg.SimpleMessage()        
        msg.code = hsm_interfaces.msg.SimpleMessage.MSG_TIMER_ELAPSED
        self.__msg_publisher.publish(msg)

        if(self._timer_repetable == False):
            self.destroy_timer(self._timer)

    def on_init_ticks_call(self, request, response):
        # Start standard timers
        if request.run_ticks:
            self.__tick_timer = self.create_timer(hsm_robot.constants.TICK_LEN, self.__tick_timer_callback)
        if request.run_ticks_1sec:
            self.__second_timer = self.create_timer(1.0, self.__second_timer_callback)
        if request.run_ticks_1min:
            self.__minute_timer = self.create_timer(60.0, self.__minute_timer_callback)
        response.ok = True
        return response

    def on_start_call(self, request, response):
        # Timer.start implementation
        period = request.timeout
        repeat = request.repeat
        self.get_logger().info('Timer.start({}, {})'.format(period, repeat))
        self._timer_repetable = repeat
        self._timer = self.create_timer(period, self.__timer_elapsed)
        response.ok = True
        return response

    def on_stop_call(self, request, response):
        # Timer.stop implementation
        self.get_logger().info('Timer.stop()')
        self._timer_repetable = False
        self.destroy_timer(self._timer)
        response.ok = True
        return response

def main(args=None):
    rclpy.init(args=args)
    node = ROSTimer()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
