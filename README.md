# The HSM ROS2 Robot API Nodes

This is the project with the HSM ROS2 nodes implementing the robot API for HSM
diagrams. The robot API has no logical dependencies on ROS2 and can be implemented on
different robotics platforms. The robot API contains the interfaces for robot control
including movement, orientation, making actions, etc. The robot API is based on
object-oriented methodology and has methods and events.

This robot API implementation is based on ROS2 and was tested on ROS 2 Jazzy.

The code is distributed under the GNU Lesser General Public License (version 3).

## Documentation

The documentation is located in the `docs` directory and contains:

* The HSM Robot architecture - `hsm_robot_architecture.md`
* The API specificaion - `hsm_robot_api.md`

## Requirements

* ROS 2 Jazzy
* The API interfaces - https://github.com/kruzhok-team/hsm-robot-ros-interfaces

