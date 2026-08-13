# ROS2 HSM Robot API Interface Acrhitecture

The robot API has no logical dependencies on ROS2 and can be implemented on different
robotics platforms. The ROS2 robot API implementation has the following architecture.

HSM Controller Node is generated from a HSM diagram. The diagram uses the robot API calls
and events embedded into the diagram within the Pyrhon code. The HSM Controller Node is
connected to the proxy objects (callers) incapsulated the ROS2 service calls to the
processing nodes. Each processing node implements the particular object from the API. The
events triggered by the objects are returned and processed by the HSM dispatcher (pysm is
used in this version).

Here is the architectural scheme of the API implementation:

     hsm_controller.py                   navigation_caller.py                          navigation.py
    +----------------+                  +-------------------+                       +-----------------+
    |                | --- methods ---> |    Navigation     | --- service call ---> | Navigation Node |
    |                | <-- events ----- | (the caller node) | <-- events ---------- |  (ROS2 impl.)   |
    |                |                  |                   | <-- /odom ----------- |    (position)   |
    |                |                  +-------------------+                       +-----------------+
    |                |
    |                |                    wheels_caller.py                              wheels.py
    |                |                  +-------------------+                       +-----------------+
    | HSM Controller | --- methods ---> |      Wheels       | --- service call ---> |   Wheels Node   |
    |      Node      | <-- events ----- | (the caller node) | <-- events----------- |  (ROS2 impl.)   |
    |                |                  +-------------------+                       +-----------------+
    |   (based on    |
    |  HSM diagram)  |                    pump_caller.py                                 pump.py
    |                |                  +-------------------+                       +-----------------+
    |                | --- methods ---> |       Pump        | --- service call ---> |    Pump Node    |
    |                |                  | (the caller node) |                       |  (ROS2 impl.)   |
    |                |                  +-------------------+                       +-----------------+
    |                |
    |                |                    storage_caller.py                             storage.py
    |                |                  +-------------------+                       +-----------------+
    |                | --- methods ---> |      Storage      | --- service call ---> |  Storage Node   |
    |                |                  | (the caller node) | <-- the stored data - |  (local disk)   |
    |                |                  |  (the data cache) |                       +-----------------+
    |                |                  +-------------------+
    |                |
    |                |                    timer_caller.py, debug_caller.py
    |                |                  +-------------------+
    |                | --- methods ---> |   Timer, Debug    | --- ...
    |                | <-- events ----- | (the caller nodes)| <-- ...
    |                |                  +-------------------+
    +----------------+

Most of the API methods are proxied to the module nodes through the ROS2 service calls, but
two of them have to answer immediately, because a blocking call inside the HSM diagram code
would stop the controller node:

* `Navigation.get_point()` reads the robot position from the odometry topic and returns the
  cached value;
* `Storage.next()`, `Storage.has_data()` and `Storage.points()` read the data cache filled
  by the `Storage.load()` call.

The navigation node keeps the trajectory of `Navigation.move_along_traj()` and publishes its
points to `/goal_pose` one at a time, the next one as soon as the current one is achieved.
The driver of the platform therefore always sees a single goal and needs no knowledge of the
trajectories.

## The HSM Modules Dependencies

A module may imply the other modules. The dependencies are declared in the
`HSM_MODULE_DEPENDENCIES` table of the `hsm_controller/constants.py` file and are resolved
both by the code generator and by the controller node, so the diagram declaring a module
gets the implied callers and their events as well.

The dependencies available:

* `Navigation` implies `Wheels` – the navigation module moves the robot with the wheels,
  and the wheels module reports `STOP_COMPLETED`.

For instance, the code incorporated into the HSM diagram calls a method from the
`Navigation` object. This call is proxied through the ROS2 service call to the dedicated
navigation node running in the system. A syncronous result or an event are proxied back.

## The HSM-ROS Messages and Topics

The Module Nodes send messages to the controller according to the HSM diagram. There are
three types of messages:

* `hsm_controller/msg/SimpleMessage.msg` - messages without arguments;
* `hsm_controller/msg/StringArgMessage.msg` - messages with the single string argument
  (e.g. `TIMER_ELAPSED`);
* `hsm_controller/msg/NumberArgMessage.msg` - messages with the single numeric argument.
  The message is declared by the interfaces package, but no module uses it yet.

The `code` parameter holds the unique message id.

The event messages are transfered through the following topics:

* `/hsm_ros_msg` - the ROS2 topic for HSM simple messages;
* `/hsm_ros_str_msg` - the ROS2 topic for HSM string messages.

The topic for the number messages is reserved for the first module reporting a numeric
value and is not created yet.

## The Code Structure
	
The API implementation code is distributed onto three packages:

* `hsm_robot_ros_api` (this project) - the package impelemting API modules
  (`navigation.py`, `wheels.py`, etc.);
* `hsm_robot_ros_interfaces` - the ROS2 interface package for the API-specific messages
  and services (mainly `hsm_controller/mgs/SimpleMessage`, `hsm_controller/srv/..`, and so
  on);
* `hsm_robot_ros_generator` - the HSM-to-Python code generator and the basic template code
  with the API callers (`hsm_controller.py` is generated, it inherits
  `base_hsm_controller.py` and the callers from `navigation_caller.py`,
  `wheels_caller.py`, and so on).

## The ROS2 Incapsulation

This library uses ROS2 as hardware-independed layer for programming robots. Therefore this
package uses standard ROS2 topics and calls. Here is the list of the ROS2 objects used in
this implementation:

* `/cmd_vel` - define the robot velocity;
* `/odom` - receive the robot odometry. The topic is used by the wheels module to detect
  the stopping of the robot, by the navigation module to detect the reaching of the target
  point, and by the navigation caller to answer the `get_point()` calls;
* `/scan` - receive the laser scan (the navigation module obstacle detection);
* `/goal_pose` - define the navigation target point;
* `/pump` - turn the pump on and off.

The long-term storage of the `Storage` module is kept on the local disk in the
`~/.hsm_robot/storage` directory, a single JSON file per storage.

## The Configuration

The module nodes are configured the ROS2 way, and the two mechanisms are used for what
each of them is meant for.

The **names** - the topics and the services - are the contract between the nodes and are
changed by the ROS2 remapping, which renames them for the node it is applied to:

    ros2 run hsm_robot navigation_node --ros-args -r /odom:=/robot/odom

The **values** - the tolerances, the ranges, the timer periods, the storage directory -
are the node parameters. They are read once, while the node is built, and their defaults
are the values the modules were tuned with for the turtlesim platform:

    ros2 run hsm_robot navigation_node --ros-args -p goal_tolerance:=0.2

The launch file passes a parameter file to every node, `config/default_params.yaml` by
default, which lists every parameter with its default value and its meaning:

    ros2 launch hsm_robot start.launch.py params_file:=my_robot.yaml

The nodes are not renamed by the launch file, so a node is called the way it names itself
(`hsm_ros_navigation` and so on) whether it is started by the launch file or by `ros2 run`,
and the same parameter file applies in both cases.

The controller generated from a diagram carries two parameters of its own,
`service_startup_timeout` and `service_startup_limit`: how often it checks for the module
services of the API and how long it waits before reporting that one is missing. Its node
name depends on the diagram (`<state machine>_hsm_controller`), so its parameters are set
inline or through a `/**` block rather than by a file shipped with the framework.

## The Testing

The ROS2 objects listed above are what makes the API testable. The modules never talk to a
robot directly, so any node implementing those topics can stand in for one:

     the API module nodes           the robot
    +--------------------+       +---------------+
    |  navigation.py     |       | turtle_driver | --- the turtlesim simulator
    |  wheels.py         | <---> |      or       |
    |  pump.py, ...      |       | the fake robot| --- the tests
    +--------------------+       +---------------+
        /cmd_vel, /odom, /scan, /goal_pose, /pump

The fake robot node adds the laser scan turtlesim cannot provide, so the obstacle detection
of the navigation module is testable as well.

The tests of the module nodes are located in the `test` directory of this package. They are
the L2 tier: one node at a time, driven through the ROS2 objects it declares, with the
fixtures of the `hsm_test_utils` package - `node_factory` builds the node and its probe, and
parameter overrides reach it through `rclpy.init`, because the node classes take no
constructor arguments. `test_debug_node.py` is the pattern on one screen.

```
colcon test --packages-select hsm_robot --pytest-args -m node
```

The testing architecture of the whole framework, and the recipe for adding a test to any of
its tiers, are described in the testing project -
https://github.com/kruzhok-team/hsm_robot_ros_tests, `docs/hsm_robot_testing.md` and
`docs/howto_write_a_test.md`.
