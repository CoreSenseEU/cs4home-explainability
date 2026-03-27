from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler, Shutdown
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    pkg = 'component_explainer_detection'
    node = 'component_explainer_detection'
    ld = LaunchDescription()

    node = LifecycleNode(
        package=pkg,
        executable='start_component_explainer',
        namespace='',
        name=node,
        output='both', emulate_tty=True,
        on_exit=Shutdown()
    )

    ld.add_action(node)

    # automatically perform the lifecycle transitions to configure and activate
    # the task at startup
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

    return ld
