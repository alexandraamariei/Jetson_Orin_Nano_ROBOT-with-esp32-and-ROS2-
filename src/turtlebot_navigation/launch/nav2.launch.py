import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Găsim directoarele pachetelor
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    my_nav_dir = get_package_share_directory('turtlebot_navigation')

    # Configurări
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_file = LaunchConfiguration(
        'map',
        default=os.path.join(my_nav_dir, 'maps', 'my_map.yaml')
    )
    
    # Folosim configurația standard din Nav2 (sau poți crea una personalizată mai târziu)
    nav2_launch_file = os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_launch_file),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'map': map_file,
            'autostart': 'true'
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        DeclareLaunchArgument(
            'map',
            default_value=map_file,
            description='Full path to map yaml file'
        ),
        nav2_bringup
    ])