# HSM-ROS2 in Docker (Ubuntu 24.04, ROS 2 Jazzy)

Three images, each built on the previous one, and the scripts that drive them:

```
 <dist>/{libs/,ubuntu-24.04/,}*.deb            <repos dir>/<ROS repos> (a package.xml)
 (the Cyberiada toolchain)                     (never copied by hand)
          │ baked into dev                              │ mounted
 build-images.sh ─► hsm-ros2-test:jazzy ─► test-docker.sh   clean: rosdep + .debs + build + L0..L4 + plugin
                    hsm-ros2-dev:jazzy  ─► build-docker.sh  build + L0..L4 (--shell: a dev shell)
                    hsm-ros2-gui:jazzy  ─► run-gui.sh       persistent: CyberiadaPro, rviz2, rqt, turtlesim
```

| file | role |
|------|------|
| `test/Dockerfile` | the clean base: ROS core, colcon, rosdep. The package dependencies come per run, so an undeclared one fails. |
| `dev/Dockerfile` | + every build/test dependency of the packages and the toolchain .debs (CyberiadaPro, the python binding). |
| `gui/Dockerfile` | + `ros-jazzy-desktop` (rviz2, rqt and its plugins, turtlesim), Mesa/OpenGL, X11/Wayland Qt, the host user. |
| `build-images.sh` | builds the images (once; rebuild dev and gui after a toolchain update). |
| `build-docker.sh` | builds and tests the packages in the dev image. |
| `test-docker.sh` | builds and tests from scratch in a disposable test container. |
| `run-gui.sh` | the everyday persistent container on the host display. |
| `in-container.sh` | the build/test phases, run inside the dev and test containers. |
| `lib.sh` | the common part of the scripts: names, the ROS repo discovery, the dist lookup, the .deb staging. |
| `hsm-ros2-env.sh` | sources ROS 2 and `$HSM_ROS2_WS/install` in every shell of the images. |
| `retry` | repeats a failing network command (in the images: `/usr/local/bin/retry`). |
| `hsm-ros2-init` | (gui) links the ROS repos, installs their deps, builds the workspace, installs the CyberiadaPro `hsm-ros2` plugin; the image runs it from the mounted repo. |

## Prerequisites

- Docker with BuildKit (buildx) on a Linux host, the default builder (it sees the local base images).
- The ROS repos side by side in the repos dir, the parent of `hsm_robot_ros_api` (e.g.
  `~/ros2_ws/src`, or `~/sources` next to the Cyberiada repos).
- The Cyberiada toolchain .debs, built by `CyberiadaHSM-Editor/packaging/build-linux-docker.sh`.
  The dist dir is `--dist DIR`, else `~/sources/dist`, `~/devel/dist`, then `../dist` of the repo;
  the .debs are taken from its `libs/`, `ubuntu-24.04/` and the dir itself (a later one wins).

## Use

    docker/build-images.sh                        # once: test, dev, gui
    docker/build-images.sh --images "dev gui" --rebuild   # after a toolchain update

    docker/build-docker.sh                        # build + L0..L4, nothing kept
    docker/build-docker.sh --tiers "L1" --out /tmp/hsm-ws  # keep the workspace, incremental
    docker/build-docker.sh --shell                # a dev shell on the sources

    docker/test-docker.sh                         # the clean test, RESULT jazzy PASS|FAIL
                                                  # logs: <dist>/test-logs/ros2-jazzy/

### The ROS repos

The ROS repos are found, not listed: a subdir of the repos dir with a `package.xml` at its top
or one level down (`ros2_repos` in `lib.sh`). The other repos (the Cyberiada ones, `dist/`) are
never mounted into the dev/test containers nor built; a `COLCON_IGNORE` in a repo leaves it out.
A new ROS repo is cloned next to the others and is picked up by the next run:

- `build-docker.sh`, `test-docker.sh`: mount the found repos read-only under `/src`; rosdep
  installs their dependencies missing in the image (as root), then the build and the tests run
  as the host user (the clean test as well);
- in the gui container: `hsm-ros2-init` again (links, rosdep, build). No image rebuild, no
  `--recreate`; the run-time deps last until the container is recreated, add them to
  `dev/Dockerfile` and rebuild to make them permanent.

### A flaky network

The network steps do not break the build at the first failure:

- each one (apt, the ROS apt source download, `rosdep init/update`, and in the clean test the
  apt, .deb and rosdep phases) runs under `retry` (5 attempts, growing pauses; `RETRY_TIMES`,
  `RETRY_DELAY`), and apt itself retries the downloads with timeouts;
- each network step is a layer of its own and the downloaded .debs stay in the BuildKit apt
  cache, so a failed image build is repeated by `build-images.sh` (`--retries N`, default 3)
  from the last finished layer, without downloading again;
- `--host-network` builds with the host network (its DNS, proxy, VPN) when the hosts resolve on
  the host but not in the build; `--mirror ""` drops the country mirror.

The tiers are those of `hsm_robot_ros_tests/docs/hsm_robot_testing.md`: L0 linter, L1 unit (the
generator), L2 node, L3 integration, L4 system (turtlesim, headless).

## The everyday container

    docker/run-gui.sh                 # a shell; the first time run hsm-ros2-init inside
    docker/run-gui.sh --editor -d     # CyberiadaPro
    docker/run-gui.sh rviz2           # or: rqt, rqt_graph, ros2 run turtlesim turtlesim_node
    docker/run-gui.sh --status | --stop | --rm | --recreate

The container `hsm-ros2` is created once and then reused. Nothing is copied into it: the original
dirs are bind-mounted read-write at their host paths, so git, the editor and the plugin see the
same paths inside and outside:

| host | in the container |
|------|------------------|
| the repos dir (`--src`, default the parent of `hsm_robot_ros_api`) | same path |
| the workspace | `~/ros2_ws` in the `hsm-ros2-ws` volume, or a host dir at its path (`--ws DIR`) |
| the Cyberiada sources (`--sources DIR`, only when asked) | same path |
| extra dirs, e.g. the diagrams (`--mount DIR`) | same path |
| the rest of the home dir | the `hsm-ros2-home` volume (editor settings, the plugin, history) |

`hsm-ros2-init` links the ROS repos of the repos dir into the workspace `src/`, so they may live
in `~/ros2_ws/src` or in `~/sources` among the Cyberiada repos alike:

    ~/ros2_ws/src/<ros repo> -> <repos dir>/<ros repo>      (links of removed repos are pruned)

The display is the host one: `/tmp/.X11-unix` with the session X cookie (refreshed on every run),
`/dev/dri` for OpenGL, `--ipc host` for the Qt/rviz2 shared memory, and the host network for the
DDS discovery with the host nodes (`--isolated` turns it off). Under Wayland the X11 apps run on
XWayland; `--wayland` switches Qt to native Wayland (rviz2 still needs `QT_QPA_PLATFORM=xcb`).
No GPU: `--software-gl`; NVIDIA: `--nvidia` (the nvidia container toolkit). If the X server
refuses the client: `xhost +SI:localuser:$USER` on the host.

The mounts, the network and the devices are fixed at creation: change them with `--recreate`
(the volumes stay). A new ROS repo in the repos dir needs no recreate, only `hsm-ros2-init`. The gui image is built for the user who runs `build-images.sh`.
