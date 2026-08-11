# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 storage module implementation
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

import json
import os

import rclpy
import rclpy.node
from rclpy.executors import ExternalShutdownException

import hsm_robot.constants
import hsm_interfaces.srv


class ROSStorage(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_storage'
    NEW_SERVICE = 'hsm_ros_storage_new'
    ADD_SERVICE = 'hsm_ros_storage_add'
    LOAD_SERVICE = 'hsm_ros_storage_load'
    STORAGE_SUFFIX = '.json'

    def __init__(self):
        rclpy.node.Node.__init__(self, self.OBJECT_NAME)
        self.__service_new = self.create_service(hsm_interfaces.srv.StorageNew,
                                                 self.NEW_SERVICE,
                                                 self.on_new_call)
        self.__service_add = self.create_service(hsm_interfaces.srv.StorageAdd,
                                                 self.ADD_SERVICE,
                                                 self.on_add_call)
        self.__service_load = self.create_service(hsm_interfaces.srv.StorageLoad,
                                                  self.LOAD_SERVICE,
                                                  self.on_load_call)
        self.__storage_path = os.path.expanduser(hsm_robot.constants.STORAGE_PATH)
        # the storages already written to the disk are picked up lazily by load(), so
        # the node keeps in memory only what the current diagram has touched
        self.__storages = {}
        self.get_logger().info('ROSStorage service node initialized ({})'.format(self.__storage_path))

    def __storage_file(self, name):
        # the storage name comes from the diagram and is used as a file name, so anything
        # that could walk out of the storage directory has to be rejected rather than
        # sanitized silently - a renamed storage would read back as empty
        if not name or name != os.path.basename(name) or name in ('.', '..'):
            raise ValueError('bad storage name "{}"'.format(name))
        return os.path.join(self.__storage_path, name + self.STORAGE_SUFFIX)

    def __write_storage(self, name):
        path = self.__storage_file(name)
        os.makedirs(self.__storage_path, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.__storages[name], f)

    def __read_storage(self, name):
        path = self.__storage_file(name)
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def on_new_call(self, request, response):
        # Storage.new implementation
        name = request.name
        array = list(request.array)
        self.get_logger().info('Storage.new({}, {})'.format(name, array))
        try:
            self.__storages[name] = [array]
            self.__write_storage(name)
            response.ok = True
        except (ValueError, OSError) as e:
            # a service callback that raises kills the executor, so storage problems are
            # reported back through the ok flag instead
            self.get_logger().error('Storage.new({}) failed: {}'.format(name, e))
            self.__storages.pop(name, None)
            response.ok = False
        return response

    def on_add_call(self, request, response):
        # Storage.add implementation
        name = request.name
        point = list(request.point)
        self.get_logger().info('Storage.add({}, {})'.format(name, point))
        try:
            if name not in self.__storages:
                # adding to a storage this node has not seen yet appends to whatever is
                # already on the disk instead of dropping it
                self.__storages[name] = self.__read_storage(name)
            self.__storages[name].append(point)
            self.__write_storage(name)
            response.ok = True
        except (ValueError, OSError, json.JSONDecodeError) as e:
            self.get_logger().error('Storage.add({}) failed: {}'.format(name, e))
            response.ok = False
        return response

    def on_load_call(self, request, response):
        # Storage.load implementation
        name = request.name
        self.get_logger().info('Storage.load({})'.format(name))
        try:
            arrays = self.__read_storage(name)
            self.__storages[name] = arrays
            data = []
            lengths = []
            for array in arrays:
                data.extend([float(value) for value in array])
                lengths.append(len(array))
            response.data = data
            response.lengths = lengths
            response.ok = True
        except (ValueError, OSError, TypeError, json.JSONDecodeError) as e:
            self.get_logger().error('Storage.load({}) failed: {}'.format(name, e))
            response.data = []
            response.lengths = []
            response.ok = False
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ROSStorage()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
