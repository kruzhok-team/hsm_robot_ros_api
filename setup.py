from setuptools import find_packages, setup

package_name = 'hsm_robot'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/start.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alexey Fedoseev',
    maintainer_email='aleksey@fedoseev.net',
    description='HSM Robot API',
    license='LGPL-3.0-or-later',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'debug_node = hsm_robot.debug:main',
            'timer_node = hsm_robot.timer:main',
            'navigation_node = hsm_robot.navigation:main',            
            'wheels_node = hsm_robot.wheels:main',
        ],
    },
)
