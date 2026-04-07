import json

from rclpy.action import ActionServer, GoalResponse
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from explainability_msgs.action import GenerateComponentExplanation
from explainability_msgs.msg import Explanation
from rcl_interfaces.msg import Log


class explainerImpl(Node):
    """Implementation of component_explainer_detection."""

    def __init__(self) -> None:
        """Construct the node."""
        super().__init__('explainer_component_explainer_detection')

        self.get_logger().info("Initialising...")

        self.explainer_server = None  # action server to start/stop this explainer
        self.logs = []  # Store logs with timestamps for later filtering

        self.get_logger().info('component_explainer_detection started, but not yet configured.')

    def rosout_callback(self, msg: Log):
        if msg.msg.startswith("[IsDetected]"):
            now = self.get_clock().now().to_msg()
            timestamp = f"{now.sec}.{now.nanosec}"
            self.logs.append({
                'timestamp': timestamp,
                'name': msg.name,
                'msg': msg.msg
            })
            self.get_logger().info(f"Received log: [{msg.name}] {msg.msg}")

    def on_request_goal(self, goal_handle):
        """Accept incoming goal if appropriate."""
        if self._state_machine.current_state[1] != "active":
            self.get_logger().error("explainer is not active, rejecting goal")
            return GoalResponse.REJECT

        self.get_logger().info("Accepted a new goal")
        return GoalResponse.ACCEPT

    def on_request_exec(self, goal_handle):
        """Process incoming goal."""
        context = json.loads(goal_handle.request.json_data)

        # Get here your attributes from the input context
        initial_timestamp = context.get("initial_timestamp", "")
        final_timestamp = context.get("final_timestamp", "")

        feedback_msg = GenerateComponentExplanation.Feedback()
        feedback_msg.status = "explainer started"

        goal_handle.publish_feedback(feedback_msg)

        # Filter logs based on the timestamps in the context
        relevant_logs = [
            log for log in self.logs
            if initial_timestamp <= log['timestamp'] <= final_timestamp
        ]

        log_messages = [log['msg'] for log in relevant_logs]
        target_msg = "[IsDetected] Persons detected, but not the target one"
        if target_msg in log_messages:
            explanation = "I detected some people, but not the one I was looking for."
        elif "[IsDetected] No detections" in log_messages:
            explanation = "My detection pipeline did not detect anything."
        elif any(log['msg'].startswith("[IsDetected] Confidence is") for log in relevant_logs):
            explanation = "I detected a potential person or object, but I wasn't confident enough."
        elif any(log['msg'].startswith("[IsDetected] Distance is") for log in relevant_logs):
            explanation = "I detected a potential person or object, but too far away from me."
        elif any(
            log['msg'].startswith("[IsDetected] I have detected")
            and "but not" in log['msg']
            for log in relevant_logs
        ):
            explanation = "I detected some objects, but not the one I was looking for."
        else:
            explanation = "My detection pipeline did not detect anything."

        generated_explanation = Explanation(
            component_name="component_explainer_detection",
            explanation=explanation)

        self.get_logger().info(f"Generated explanation: {generated_explanation.explanation}")

        explanations = [generated_explanation]

        feedback_msg.status = "explainer completed"
        goal_handle.publish_feedback(feedback_msg)

        goal_handle.succeed()
        return GenerateComponentExplanation.Result(explanations=explanations)

    #################################
    #
    # Lifecycle transitions callbacks
    #
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """
        Configure the skill.
        """
        # create the control server for ourselves
        self.explainer_server = ActionServer(
            self, GenerateComponentExplanation, "/component_explainer_detection/explain",
            goal_callback=self.on_request_goal,
            execute_callback=self.on_request_exec)

        self.get_logger().info("component_explainer_detection is configured, but not yet active")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """
        Activate the skill.

        You usually want to do the following in this state:
        - Create and start any timers performing periodic routines
        - Start processing data, and accepting action goals, if any

        """
        self.get_logger().info("component_explainer_detection is active and running")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop the timer to stop calling the `run` function."""
        self.get_logger().info("Stopping explainer...")

        self.get_logger().info("component_explainer_detection is stopped (inactive)")
        return super().on_deactivate(state)

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """
        Shutdown the node, after a shutting-down transition is requested.
        """
        self.get_logger().info('Shutting down component_explainer_detection.')

        self.get_logger().info("component_explainer_detection finalized.")
        return TransitionCallbackReturn.SUCCESS

    #################################
