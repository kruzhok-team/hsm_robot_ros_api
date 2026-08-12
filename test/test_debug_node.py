# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 contract of the debug module node
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

from hsm_interfaces.srv import DebugPrint
from hsm_robot.debug import ROSDebug

pytestmark = pytest.mark.node


def print_message(probe, text):
    request = DebugPrint.Request()
    request.s = text
    return probe.call('hsm_ros_debug_print', DebugPrint, request)


def test_the_message_is_accepted(node_factory):
    ctx = node_factory(ROSDebug)
    assert print_message(ctx.probe, 'hello from the diagram').ok


def test_the_module_reports_no_events(node_factory):
    ctx = node_factory(ROSDebug)
    print_message(ctx.probe, 'quiet')
    ctx.probe.spin(0.2)
    assert ctx.probe.event_codes() == []


def test_the_level_is_the_default_one(node_factory):
    ctx = node_factory(ROSDebug)
    assert ctx.node.get_parameter('log_level').value == 'info'


def test_the_level_is_a_parameter(node_factory):
    ctx = node_factory(ROSDebug, log_level='debug')
    # the diagram writes at the level it is given, so its tracing can be separated from
    # the messages of the framework itself
    assert ctx.node.get_parameter('log_level').value == 'debug'
    assert print_message(ctx.probe, 'traced').ok


def test_an_unknown_level_falls_back(node_factory):
    ctx = node_factory(ROSDebug, log_level='nonsense')
    # a diagram is not stopped by a bad configuration: the node reports the value and
    # keeps writing at the default level
    assert print_message(ctx.probe, 'still printed').ok
