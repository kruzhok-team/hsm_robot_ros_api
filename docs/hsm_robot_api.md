# ROS2 HSM Robot API Interface Specification

## Navigation Module

`Navigation` module is the high-level movement control interface. It collects and uses knowledge
about the world (navigation, maps, etc.), constructing paths, and so on.

The methods available:

* `move_to_point(x, y, theta=None)` – move to point with the coordinates `(x, y)` and the
targe angle `theta` radians;
* `stop()` – stop movement;
* `get_point()` – return the pair `(x, y, theta)` of the robot's current position.

The events available:

* `PATH_FOUND` – the path to the target point was built; 
* `PATH_NOT_FOUND` – the path to the target point cannot be built;
* `MOVE_COMPLETED` – the movement was completed;
* `STOP_COMPLETED` – the stopping process was completed;
* `COLLISION_WARNING` – the possible collision detecion warning;
* `COLLISION_DETECTED` – the collision detection;
* `RIGHT_OPEN_SPACE` – there is free space to the right of the robot (the disance if
fixed now - 0.5 m).

## Wheels Module

`Wheels` module is the middle-level movement control interface. It controls engines to produce
the target speed - linear or angular.

The methods available:

* `forward(v)` – go forward with the speed `v` m/sec;
* `back(v)` – go back with the speed of `v` m/sec;
* `turn_right(w)` – turn clockwise with the angular speed `w` radians/sec;
* `turn_left(w)` – turn contr-clockwise with the angular speed `w` radians/sec;
* `stop()` – stop movement.

The events available:

* `STOP_COMPLETED` – the stopping process was completed;

## Pump Module

Pump module is the pump control interface. It turns on/off the pump motor available at
unmanned ships.

The methods available:

* `turn_on()` – turn on the pump;
* `turn_off()` – turn off the pump.

The events available:

* `STOP_COMPLETED` – the stopping process was completed;

## Timer Module

`Timer` module is the timers control interface. It allows setting timers and use regular time events.

The methods available:

* `start(self, timeout, repeat=False, name='default')` – start timer with the name `name` on
`timeout` seconda and auto-repeat flag `repeat`;
*`stop(name='default')` – stop the timer named `name`.

The events available:

* `TIMER_TICK` – once-a-tick counter timer (tick is the minimal loop interval in the
  system, e.g. 0.2 sec);
* `TIMER_TICK_1S` – once-a-second counter timer;
* `TIMER_TICK_1M` – once-a-minute counter timer;
* `TIMER_ELAPSED(name)` – the previously set timer was completed. The timer's name is
  stored in the `name` variable.

## Debug Module

`Debug` module interface provides logging output for debug purposes. It uses ROS2 debug logging
in this implementation.

The methods available:

* `print(s)` – print the string `s` to a debug log;
* `println(s)` – print the string `s` followed by a new line characters to a debug log.

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

The events available:

None.
