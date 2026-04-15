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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alexey Fedoseev',
    maintainer_email='aleksey@fedoseev.net',
    description='HSM Robot API',
    license='LGPL v3',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'node_debug = hsm_robot.debug.debug:main',
            'node_timer = hsm_robot.timer.timer:main',
            'node_navigation = hsm_robot.navigation.navigation:main',            
        ],
    },
)
