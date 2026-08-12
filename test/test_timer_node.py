# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 contract of the timer module node
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

# The periods of the ticks are the parameters of the node, so the tests shrink them
# instead of driving a simulated clock: a minute tick is checked in a few milliseconds.

import pytest

from hsm_interfaces.msg import SimpleMessage, StringArgMessage
from hsm_interfaces.srv import TimerStart, TimerStop, TimerTicks
from hsm_robot.timer import ROSTimer

TICK = SimpleMessage.MSG_TIMER_TICK
TICK_1S = SimpleMessage.MSG_TIMER_TICK_1S
TICK_1M = SimpleMessage.MSG_TIMER_TICK_1M
ELAPSED = StringArgMessage.MSG_TIMER_ELAPSED

pytestmark = pytest.mark.node


def init_ticks(probe, ticks=False, seconds=False, minutes=False):
    request = TimerTicks.Request()
    request.run_ticks = ticks
    request.run_ticks_1sec = seconds
    request.run_ticks_1min = minutes
    return probe.call('hsm_ros_timer_init_ticks', TimerTicks, request)


def start_timer(probe, timeout, repeat=False, name='default'):
    request = TimerStart.Request()
    request.timeout = float(timeout)
    request.repeat = repeat
    request.name = name
    return probe.call('hsm_ros_timer_start', TimerStart, request)


def stop_timer(probe, name='default'):
    request = TimerStop.Request()
    request.name = name
    return probe.call('hsm_ros_timer_stop', TimerStop, request)


def fast_ticks():
    return {'tick_period': 0.02, 'second_period': 0.05, 'minute_period': 0.1}


def test_the_ticks_are_not_running_before_they_are_asked_for(node_factory):
    ctx = node_factory(ROSTimer, **fast_ticks())
    ctx.probe.expect_no_event(TICK)


def test_the_tick_runs_when_it_is_asked_for(node_factory):
    ctx = node_factory(ROSTimer, **fast_ticks())
    assert init_ticks(ctx.probe, ticks=True).ok
    ctx.probe.wait_for_event(TICK)


def test_only_the_requested_ticks_run(node_factory):
    ctx = node_factory(ROSTimer, **fast_ticks())
    init_ticks(ctx.probe, seconds=True)
    ctx.probe.wait_for_event(TICK_1S)
    assert ctx.probe.count_events(TICK) == 0
    assert ctx.probe.count_events(TICK_1M) == 0


def test_every_tick_can_run(node_factory):
    ctx = node_factory(ROSTimer, **fast_ticks())
    init_ticks(ctx.probe, ticks=True, seconds=True, minutes=True)
    for code in (TICK, TICK_1S, TICK_1M):
        ctx.probe.wait_for_event(code)


def test_the_ticks_are_repeated(node_factory):
    ctx = node_factory(ROSTimer, **fast_ticks())
    init_ticks(ctx.probe, ticks=True)
    assert ctx.probe.wait_for(lambda: ctx.probe.count_events(TICK) >= 5)


def test_the_ticks_are_stopped_by_a_second_request(node_factory):
    ctx = node_factory(ROSTimer, **fast_ticks())
    init_ticks(ctx.probe, ticks=True)
    ctx.probe.wait_for_event(TICK)
    assert init_ticks(ctx.probe).ok
    ctx.probe.clear()
    ctx.probe.expect_no_event(TICK)


def test_a_timer_reports_its_name(node_factory):
    ctx = node_factory(ROSTimer)
    assert start_timer(ctx.probe, 0.05, name='wakeup').ok
    event = ctx.probe.wait_for_str_event(ELAPSED)
    assert event.arg == 'wakeup'


def test_a_timer_elapses_once(node_factory):
    ctx = node_factory(ROSTimer)
    start_timer(ctx.probe, 0.05, name='once')
    ctx.probe.wait_for_str_event(ELAPSED)
    ctx.probe.spin(0.3)
    # a timer which does not repeat destroys itself when it has elapsed
    assert len([m for m in ctx.probe.str_events if m.code == ELAPSED]) == 1


def test_a_repeating_timer_keeps_elapsing(node_factory):
    ctx = node_factory(ROSTimer)
    start_timer(ctx.probe, 0.03, repeat=True, name='again')
    assert ctx.probe.wait_for(
        lambda: len([m for m in ctx.probe.str_events if m.code == ELAPSED]) >= 3)


def test_a_repeating_timer_is_stopped(node_factory):
    ctx = node_factory(ROSTimer)
    start_timer(ctx.probe, 0.03, repeat=True, name='again')
    ctx.probe.wait_for_str_event(ELAPSED)
    assert stop_timer(ctx.probe, 'again').ok
    ctx.probe.clear()
    ctx.probe.spin(0.3)
    assert [m for m in ctx.probe.str_events if m.code == ELAPSED] == []


def test_restarting_a_timer_replaces_it(node_factory):
    ctx = node_factory(ROSTimer)
    start_timer(ctx.probe, 10.0, name='slow')
    start_timer(ctx.probe, 0.05, name='slow')
    # the second request replaces the timer instead of leaving two of them
    ctx.probe.wait_for_str_event(ELAPSED)
    ctx.probe.spin(0.2)
    assert len([m for m in ctx.probe.str_events if m.code == ELAPSED]) == 1


def test_timers_are_independent(node_factory):
    ctx = node_factory(ROSTimer)
    start_timer(ctx.probe, 0.05, name='first')
    start_timer(ctx.probe, 0.05, name='second')
    assert ctx.probe.wait_for(
        lambda: {m.arg for m in ctx.probe.str_events if m.code == ELAPSED} ==
        {'first', 'second'})


def test_stopping_an_unknown_timer_is_accepted(node_factory):
    ctx = node_factory(ROSTimer)
    # the diagram may stop a timer which has already elapsed, which is not an error
    assert stop_timer(ctx.probe, 'never started').ok
