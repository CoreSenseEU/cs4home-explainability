from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler, DeclareLaunchArgument
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition
from lifecycle_msgs.msg import Transition

import os
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription


def generate_launch_description():
    pkg = 'explainer_selector'
    node = 'explainer_selector'
    ld = LaunchDescription()

    node = LifecycleNode(
        package=pkg,
        executable='start_explainer_selector',
        namespace='',
        name=node,
        output='both', emulate_tty=True,
    )

    ld.add_action(node)

    # automatically perform the lifecycle transitions to configure and activate
    configure_event = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(node),
        transition_id=Transition.TRANSITION_CONFIGURE))

    ld.add_action(configure_event)

    activate_event = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=node, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(node),
            transition_id=Transition.TRANSITION_ACTIVATE))],
        handle_once=True))

    ld.add_action(activate_event)

    explainers_launch_path = os.path.join(
        get_package_share_directory(pkg),
        'launch',
        'explainers.launch.py'
    )
    ld.add_action(IncludeLaunchDescription(
          PythonLaunchDescriptionSource(explainers_launch_path)
        ))

    return ld
