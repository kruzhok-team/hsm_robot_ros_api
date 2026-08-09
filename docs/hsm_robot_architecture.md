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
    |      Node      | <-- events ----- | (the caller node) | <-- STOP_COMPLETED --- |  (ROS2 impl.)   |
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
    |                |                  | (the caller node) | <-- the stored data -- |  (local disk)   |
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
* `Storage.next()` and `Storage.has_data()` read the data cache filled by the
  `Storage.load()` call.

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

The `code` parameter holds the unique message id.

The event messages are transfered through the following topics:

* `/hsm_ros_msg` - the ROS2 topic for HSM simple messages;
* `/hsm_ros_str_msg` - the ROS2 topic for HSM string messages.
* `/hsm_ros_num_msg` - the ROS2 topic for HSM number messages.

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
