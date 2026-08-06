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
    |                | <-- events ----- | (the caller node) | <-- service result -- |  (ROS2 impl.)   |
    |                |                  +-------------------+                       +-----------------+
    | HSM Controller |
    |      Node      |                    wheels_caller.py
    |                |                  +-------------------+
    |   (based on    | --- methods ---> |      Wheels       | --- ...
    |  HSM diagram)  | <-- events ----- | (the caller node) | <-- ...
    |                |                  +-------------------+
    |                |
    |                |      ...
    +----------------+

For instance, the code incorporated into the HSM diagram calls a method from the
`Navigation` object. This call is proxied through the ROS2 service call to the dedicated
navigation node running in the system. A syncronous result or an event are proxied back.

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

## The HSM-ROS Messages and Topics

The Module Nodes send messages to the controller according to the HSM diagram. There are
three types of messages:

* `hsm_controller/msg/SimpleMessage.msg` - messages without arguments;
* `hsm_controller/msg/StringArgMessage.msg` - messages with the single string argument
  (e.g. `TIMER_ELAPSED`);
* `hsm_controller/msg/NumberArgMessage.msg` - messages with the single numeric argument. 

The `code` parameter holds the unique message id.

The messages are transfered through the following topics:

* `/hsm_ros_msg` - the ROS2 topic for HSM simple messages;
* `/hsm_ros_str_msg` - the ROS2 topic for HSM string messages.
* `/hsm_ros_num_msg` - the ROS2 topic for HSM number messages.

## The ROS2 Incapsulation

This library uses ROS2 as hardware-independed layer for programming robots. Therefore this
package uses standard ROS2 topics and calls. Here is the list of the ROS2 objects used in
this implementation:

* `/cmd_vel` - define the robot velocity;
* `/odom` - receive the robot odometry.
