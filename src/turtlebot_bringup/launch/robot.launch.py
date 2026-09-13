import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node

def generate_launch_description():

    # 1. Declarăm parametrul  use_sim_time (True = Gazebo, False = Real)
    use_sim_time = LaunchConfiguration('use_sim_time')
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Folosesc timpul din simulare daca sunt in Gazebo'
    )

    # 2. Găsesc pachetul cu descrierea robotului (URDF-ul)
    turtlebot_desc_dir = get_package_share_directory('turtlebot_description')
    # 2.5 Pornește Robot State Publisher (pentru a trimite modelul 3D / URDF-ul către RViz2)
    rsp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot_desc_dir, 'launch', 'rsp.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )
    # 3. Lansarea pentru Simulare
    gazebo_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot_desc_dir, 'launch', 'sim.launch.py')
        ),
        condition=IfCondition(use_sim_time)
    )

    # 4. Lansarea pentru Hardware Real
   
    micro_ros_agent = ExecuteProcess(
        cmd=[
            'sh', '-c',
            'docker rm -f $(docker ps -qa) 2>/dev/null || true ; '
            'docker run --rm --name mros_agent -v /dev:/dev --privileged --net=host microros/micro-ros-agent:jazzy serial --dev /dev/ttyUSB0 -v6'
        ],
        output='screen',
        condition=UnlessCondition(use_sim_time)
    )

    # C. Nodul de Hardware (Odometrie din encodere)
    hardware_node = Node(
        package='turtlebot_hardware', 
        executable='odom_calculator',    
        name='hardware_interface',
        output='screen',
        condition=UnlessCondition(use_sim_time)
    )

    # B. Driverul pentru LiDAR (Pregătit pentru când îți ajunge)
    lidar_node = Node(
        package='rplidar_ros',     
        executable='rplidar_node',
        name='rplidar_node',
        parameters=[{
            'serial_port': '/dev/ttyUSB1',
            'frame_id': 'laser_frame',
            'angle_compensate': True,
            'scan_mode': 'Standard'
        }],
        output='screen',
        condition=UnlessCondition(use_sim_time)
    )

    # 5. trimit către ROS 2
    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(gazebo_sim_launch)
    ld.add_action(micro_ros_agent)
    ld.add_action(hardware_node) 
    # ld.add_action(lidar_node)

    return ld