# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 contract of the storage module node
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

# The storage is written to the disk, so every test points the node at its own directory:
# a test run must not touch the storage of the developer.

import json
import os

import pytest

from hsm_interfaces.srv import StorageAdd, StorageLoad, StorageNew
from hsm_robot.storage import ROSStorage

pytestmark = pytest.mark.node


def new(probe, name, array):
    request = StorageNew.Request()
    request.name = name
    request.array = [float(v) for v in array]
    return probe.call('hsm_ros_storage_new', StorageNew, request)


def add(probe, name, point):
    request = StorageAdd.Request()
    request.name = name
    request.point = [float(v) for v in point]
    return probe.call('hsm_ros_storage_add', StorageAdd, request)


def load(probe, name):
    request = StorageLoad.Request()
    request.name = name
    return probe.call('hsm_ros_storage_load', StorageLoad, request)


def test_a_new_storage_is_written_to_the_disk(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    assert new(ctx.probe, 'path', [1.0, 2.0]).ok
    written = os.path.join(storage_directory, 'path.json')
    assert os.path.isfile(written)
    with open(written) as f:
        assert json.load(f) == [[1.0, 2.0]]


def test_a_stored_array_is_read_back(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'path', [1.0, 2.0])
    response = load(ctx.probe, 'path')
    assert response.ok
    assert list(response.data) == [1.0, 2.0]
    assert list(response.lengths) == [2]


def test_the_arrays_are_flattened_with_their_lengths(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'path', [1.0, 2.0])
    add(ctx.probe, 'path', [3.0, 4.0, 5.0])
    add(ctx.probe, 'path', [6.0])
    response = load(ctx.probe, 'path')
    # the arrays are concatenated and the lengths say where each of them ends
    assert list(response.data) == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert list(response.lengths) == [2, 3, 1]


def test_the_storages_are_separate(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'first', [1.0])
    new(ctx.probe, 'second', [2.0])
    assert list(load(ctx.probe, 'first').data) == [1.0]
    assert list(load(ctx.probe, 'second').data) == [2.0]


def test_a_missing_storage_reads_as_empty(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    response = load(ctx.probe, 'never written')
    # a storage which was never created is not an error, it is empty
    assert response.ok
    assert list(response.data) == []
    assert list(response.lengths) == []


def test_a_new_storage_replaces_the_old_one(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'path', [1.0])
    add(ctx.probe, 'path', [2.0])
    new(ctx.probe, 'path', [9.0])
    assert list(load(ctx.probe, 'path').data) == [9.0]


def test_a_point_may_be_a_single_number(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'path', [1.0])
    add(ctx.probe, 'path', [2.0])
    assert list(load(ctx.probe, 'path').lengths) == [1, 1]


def test_an_empty_name_is_refused(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    # the name of the storage comes from the diagram and becomes a file name, so a bad
    # name is reported and not written; the service never raises, it answers ok = false
    assert not new(ctx.probe, '', [1.0]).ok


def test_a_name_with_a_path_is_refused(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    assert not new(ctx.probe, '../escaped', [1.0]).ok
    assert not new(ctx.probe, 'sub/path', [1.0]).ok
    assert not new(ctx.probe, '..', [1.0]).ok
    assert not new(ctx.probe, '.', [1.0]).ok
    assert os.listdir(storage_directory) == [] if os.path.isdir(storage_directory) else True


def test_a_refused_storage_is_not_remembered(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'bad/name', [1.0])
    # the failed creation must not leave the storage behind in the memory of the node
    assert not add(ctx.probe, 'bad/name', [2.0]).ok


def test_the_storage_outlives_the_node(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'path', [1.0, 2.0])
    add(ctx.probe, 'path', [3.0])
    # the file is what the storage is: a node started later reads what was written
    with open(os.path.join(storage_directory, 'path.json')) as f:
        assert json.load(f) == [[1.0, 2.0], [3.0]]


def test_the_default_storage_is_not_touched(node_factory, storage_directory):
    ctx = node_factory(ROSStorage, storage_path=storage_directory)
    new(ctx.probe, 'path', [1.0])
    home = os.path.expanduser('~/.hsm_robot/storage')
    assert not os.path.isfile(os.path.join(home, 'path.json'))
