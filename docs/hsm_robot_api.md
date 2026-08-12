# ROS2 HSM Robot API Interface Specification

## Navigation Module

`Navigation` module is the high-level movement control interface. It collects and uses knowledge
about the world (navigation, maps, etc.), constructing paths, and so on.

The methods available:

* `move_to_point(x, y, theta=None)` – move to point with the coordinates `(x, y)` and the
target angle `theta` radians;
* `stop()` – stop movement;
* `get_point()` – return the triple `(x, y, theta)` of the robot's current position.

The events available:

* `PATH_FOUND` – the path to the target point was built (declared, but not raised by the
current implementation);
* `PATH_NOT_FOUND` – the path to the target point cannot be built (declared, but not
raised by the current implementation);
* `MOVE_COMPLETED` – the movement was completed, i.e. the robot came closer to the target
point than the goal tolerance;
* `COLLISION_WARNING` – the possible collision detection warning;
* `COLLISION_DETECTED` – the collision detection;
* `RIGHT_OPEN_SPACE` – there is free space to the right of the robot (the distance is
fixed now - 0.5 m).

The `Navigation` module moves the robot with the wheels, therefore using `Navigation`
implies using the `Wheels` module: the `Wheels` events (`STOP_COMPLETED`) are available in
the diagram which declares `Navigation` only, and the wheels module node has to be started
along with the navigation one.

The `get_point()` method returns the robot position immediately without a service call: the
module reads the robot odometry to keep the current position. The method returns nothing
(`None`) until the first odometry message is received.

## Wheels Module

`Wheels` module is the middle-level movement control interface. It controls engines to produce
the target speed - linear or angular.

The methods available:

* `forward(v)` – go forward with the speed `v` m/sec;
* `back(v)` – go back with the speed of `v` m/sec;
* `turn_right(w)` – turn clockwise with the angular speed `w` radians/sec;
* `turn_left(w)` – turn counter-clockwise with the angular speed `w` radians/sec;
* `stop()` – stop movement.

The events available:

* `STOP_COMPLETED` – the stopping process was completed. The event is raised by the
`Wheels` module: it reports the state of the wheels, not of the navigation process.

## Pump Module

Pump module is the pump control interface. It turns on/off the pump motor available at
unmanned ships.

The methods available:

* `turn_on()` – turn on the pump;
* `turn_off()` – turn off the pump.

The events available:

None.

## Timer Module

`Timer` module is the timers control interface. It allows setting timers and use regular time events.

The methods available:

* `start(self, timeout, repeat=False, name='default')` – start timer with the name `name` on
`timeout` seconds and auto-repeat flag `repeat`;
* `stop(name='default')` – stop the timer named `name`.

The events available:

* `TIMER_TICK` – once-a-tick counter timer (tick is the minimal loop interval in the
  system, e.g. 0.2 sec);
* `TIMER_TICK_1S` – once-a-second counter timer;
* `TIMER_TICK_1M` – once-a-minute counter timer;
* `TIMER_ELAPSED(name)` – the previously set timer was completed. The timer's name is
  stored in the `name` variable.

## Debug Module

`Debug` module interface provides logging output for debug purposes. It uses the ROS2 logging
in this implementation.

The level the messages are written with is set by the `log_level` parameter of the debug
node - `debug`, `info` (the default), `warn` or `error`. It is not the level the logger
passes on, which is set by the standard `--log-level` option: the diagram may write at the
debug level and leave the info level to the framework itself.

The methods available:

* `print(s)` – print the string `s` to a log;
* `println(s)` – print the string `s` followed by a new line character to a log.

The events available:

None.

## Storage Module

`Storage` module interface provides saving data to a long-term storage. It stores data on
the local disk.

The methods available:

* `new(name, array)` – create the numeric `array` at the local storage named `name`;
* `add(name, point)` – save the `point` to the storage `name`;
* `load(name)` – load the set of numeric arrays named `name` from file to memory;
* `next(name)` – get the next point from the storage `name`;
* `has_data(name)` – the next point availability flag for the storage `name`.

A point is the array of numbers, e.g. the pair of coordinates; the single number is
accepted as well and is stored as the array of one element. The `next(name)` method
returns the point as the array of numbers and returns nothing (`None`) when the storage is
exhausted, so `has_data(name)` should be checked first.

The `load(name)` method reads the storage into the diagram memory, therefore `next()` and
`has_data()` answer immediately. The points saved by `new()` and `add()` are available for
reading without the `load()` call.

The events available:

None.
