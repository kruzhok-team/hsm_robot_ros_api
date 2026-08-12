# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 contract of the pump module node
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

from std_msgs.msg import Bool

from conftest import PUMP_TOPIC
from hsm_interfaces.srv import PumpTurnOff, PumpTurnOn
from hsm_robot.pump import ROSPump

pytestmark = pytest.mark.node


def test_turn_on_switches_the_pump_on(node_factory):
    ctx = node_factory(ROSPump)
    states = ctx.probe.record(PUMP_TOPIC, Bool)
    assert ctx.probe.call('hsm_ros_pump_turn_on', PumpTurnOn).ok
    assert ctx.probe.wait_for(lambda: len(states) == 1)
    assert states[0].data is True


def test_turn_off_switches_the_pump_off(node_factory):
    ctx = node_factory(ROSPump)
    states = ctx.probe.record(PUMP_TOPIC, Bool)
    assert ctx.probe.call('hsm_ros_pump_turn_off', PumpTurnOff).ok
    assert ctx.probe.wait_for(lambda: len(states) == 1)
    assert states[0].data is False


def test_every_call_is_published(node_factory):
    ctx = node_factory(ROSPump)
    states = ctx.probe.record(PUMP_TOPIC, Bool)
    ctx.probe.call('hsm_ros_pump_turn_on', PumpTurnOn)
    ctx.probe.call('hsm_ros_pump_turn_on', PumpTurnOn)
    ctx.probe.call('hsm_ros_pump_turn_off', PumpTurnOff)
    assert ctx.probe.wait_for(lambda: len(states) == 3)
    assert [s.data for s in states] == [True, True, False]


def test_the_pump_reports_no_events(node_factory):
    ctx = node_factory(ROSPump)
    ctx.probe.call('hsm_ros_pump_turn_on', PumpTurnOn)
    # the module has no events of its own: the diagram drives it and does not wait for it
    ctx.probe.spin(0.2)
    assert ctx.probe.event_codes() == []
