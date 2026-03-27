import json

from rclpy.action import ActionServer, GoalResponse
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from explainability_msgs.action import GenerateComponentExplanation
from explainability_msgs.msg import Explanation
from rcl_interfaces.msg import Log


class explainerImpl(Node):
    """Implementation of component_explainer_sittable."""

    def __init__(self) -> None:
        """Construct the node."""
        super().__init__('explainer_component_explainer_sittable')

        self.get_logger().info("Initialising...")

        self.explainer_server = None  # action server to start/stop this explainer

        self.logs = []  # Store logs with timestamps for later filtering

        self.get_logger().info('component_explainer_sittable started, but not yet configured.')

    def rosout_callback(self, msg: Log):
        if msg.msg.startswith("[IsSittable]"):
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

        if "[IsSittable] no detections found" in [log['msg'] for log in relevant_logs]:
            explanation = "I failed because my detection pipeline did not detect anything."
        elif any(log['msg'].startswith("[IsSittable] Confidence is") for log in relevant_logs):
            explanation = "I detected a pottential seat, but I wasn't confident enough."
        elif "[IsSittable] No free space in chair due to person" in [
                log['msg'] for log in relevant_logs]:
            explanation = "I detected a pottential seat, but there was a person sitting on it."
        else:
            explanation = "I failed because I detected some objects, but none of them were a seat."

        generated_explanation = Explanation(
            component_name="component_explainer_sittable",
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
        Configure the node, after a configuring transition is requested.
        """
        # create the control server for ourselves
        self.explainer_server = ActionServer(
            self, GenerateComponentExplanation, "/component_explainer_sittable/explain",
            goal_callback=self.on_request_goal,
            execute_callback=self.on_request_exec)

        self.get_logger().info("component_explainer_sittable is configured, but not yet active")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """
        Activate the skill.
        """
        # Create a subscriber to /rosout
        self.rosout_subscriber = self.create_subscription(
            Log,
            '/rosout',
            self.rosout_callback,
            10
        )

        self.get_logger().info("component_explainer_sittable is active and running")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop the timer to stop calling the `run` function."""
        self.get_logger().info("Stopping explainer...")

        self.get_logger().info("component_explainer_sittable is stopped (inactive)")
        return super().on_deactivate(state)

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """
        Shutdown the node, after a shutting-down transition is requested.
        """
        self.get_logger().info('Shutting down component_explainer_sittable.')

        self.get_logger().info("component_explainer_sittable finalized.")
        return TransitionCallbackReturn.SUCCESS

    #################################
