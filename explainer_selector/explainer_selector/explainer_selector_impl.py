import json
import time

from rclpy.action import ActionClient
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

from rclpy.action import ActionServer, GoalResponse

from explainability_msgs.action import GenerateExplanation, GenerateComponentExplanation
from diagnostic_msgs.msg import KeyValue


class GenerateExplanationImpl(Node):
    """Implementation of explainer_selector."""

    def __init__(self) -> None:
        """Construct the node."""
        super().__init__('explainer_selectorer_selector')

        # Attributes
        self.events_buffer = []

        self.component_skills = {
            "component_explainer_navigation": {
                "skills": ["MoveTo"],
                "explanation": "I had issues in my autonomous navigation."
            },
            "component_explainer_sittable": {
                "skills": ["IsSittable"],
                "explanation": "I had issues in finding a free seat."
            },
            "component_explainer_detection": {
                "skills": ["IsDetected"],
                "explanation": "I had issues in detecting objects and persons."
            },
        }

        # Subscribers
        self._events_subscriber = None

        # Component Explainers
        self.component_explainers = None

        self.last_bt_status = None

        self.get_logger().info("Initialising...")
        self.get_logger().info('explainer_selector started, but not yet configured.')

    def on_request_goal(self, goal_handle):
        """Accept incoming goal if appropriate."""
        if self._state_machine.current_state[1] != "active":
            self.get_logger().error("Skill is not active yet, rejecting goal")
            return GoalResponse.REJECT

        self.get_logger().info("Accepted a new goal")
        return GoalResponse.ACCEPT

    def on_request_exec(self, goal_handle):
        self.get_logger().info(f"Current state: {self._state_machine.current_state[1]}")
        """Process incoming goal."""
        self.get_logger().info(
            f"Generating explanation for question: {goal_handle.request.question}")

        # Get the relevant context
        relevant_events = self.get_relevant_events(goal_handle.request.question)

        # Select the component explainer to use
        component_explainer, context = self.select_explainer_and_create_context(
            goal_handle.request.question, relevant_events)

        if component_explainer is None:
            self.get_logger().warn("No relevant skill failure found, returning default message")
            final_explanation = "I can't explain this right now, sorry."
            goal_handle.succeed()
            return GenerateExplanation.Result(explanation=final_explanation)

        # Invoke the selected component explainer
        list_of_explanations = self.invoke_explainer(component_explainer, context)

        list_of_explanations.insert(0, self.component_skills[component_explainer]["explanation"])

        if len(list_of_explanations) == 0:
            self.get_logger().warn("No explanations received, returning default message")
            final_explanation = "I can't explain this right now, sorry."
        elif len(list_of_explanations) == 1:
            final_explanation = list_of_explanations[0]
        else:
            final_explanation = ". ".join(list_of_explanations)

        # Filter double dots and spaces
        final_explanation = final_explanation.replace("..", ".").replace("  ", " ")

        self.get_logger().info(f"Final explanation: {final_explanation}")
        goal_handle.succeed()

        return GenerateExplanation.Result(explanation=final_explanation)

    def get_relevant_events(self, question: str):
        """Fetch the relevant context."""

        relevant_skill = None
        final_timestamp = None
        initial_timestamp = None

        # # Get the latest failure
        # for event in reversed(self.events_buffer):
        #     if event[2] == 3:
        #         relevant_skill = event[1]
        #         final_timestamp = event[0]
        #     if event[1] != relevant_skill and relevant_skill is not None:
        #         initial_timestamp = event[0]

        # # Get the latest event that is not "Explain"
        # for event in reversed(self.events_buffer):
        #     if event[1] != "Explain":
        #         relevant_skill = event[1]
        #         final_timestamp = event[0]
        #     if event[1] != relevant_skill and relevant_skill is not None:
        #         initial_timestamp = event[0]

        # Get the event before the latest
        initial_timestamp = self.events_buffer[-2][0]
        relevant_skill = self.events_buffer[-2][1]
        print(f"Relevant skill: {relevant_skill}, initial timestamp: {initial_timestamp}")

        # current time
        final_timestamp = self.get_clock().now().to_msg()
        final_timestamp = f"{final_timestamp.sec}.{final_timestamp.nanosec}"

        relevant_events = {"initial_timestamp": initial_timestamp,
                           "final_timestamp": final_timestamp,
                           "relevant_skill": relevant_skill}

        return relevant_events

    def select_explainer_and_create_context(self, question: str, relevant_events: dict):
        """Select the component explainer to use."""
        component_explainer = None

        if "IsSittable" in question:
            component_explainer = "component_explainer_sittable"
        elif "IsDetected" in question:
            component_explainer = "component_explainer_detection"
        elif "MoveTo" in question:
            component_explainer = "component_explainer_navigation"
        else:
            for component in self.component_skills:
                if relevant_events["relevant_skill"] in self.component_skills[component]["skills"]:
                    self.get_logger().info(
                        f"Skill failure detected in skill {relevant_events['relevant_skill']}, "
                        f"which is handled by {component} explainer")
                    component_explainer = component
                    break

        context = relevant_events

        return component_explainer, context

    def invoke_explainer(self, component_explainer: str, context: dict):
        self.component_explainer_responded = False

        result = self.send_goal_to_component_explainer(component_explainer, context)

        list_of_explanations = []
        for explanation in result.explanations:
            list_of_explanations.append(explanation.explanation)
        return list_of_explanations

    def on_new_event(self, msg):
        """Implement the callback when the subscriber receives a new task info."""

        if [msg.key, msg.value] == self.last_bt_status:
            return

        self.last_bt_status = [msg.key, msg.value]

        self.get_logger().info(f"Received new bt status for node {msg.key}: {msg.value}")

        current_time_msg = self.get_clock().now().to_msg()
        current_time = f"{current_time_msg.sec}.{current_time_msg.nanosec}"
        self.events_buffer.append([current_time, msg.key, msg.value])

    def component_explainer_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected by component explain')
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.component_get_result_callback)

    def component_get_result_callback(self, future):
        # result = future.result().result
        self.component_explainer_responded = True

    def send_goal_to_component_explainer(self, component_explainer: str, context: dict):
        goal = GenerateComponentExplanation.Goal()
        goal.json_data = json.dumps(context)

        client = self.component_explainers[component_explainer]

        self.get_logger().info(f'Sending goal to {component_explainer}')

        # Wait for the action server to be available
        while not client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info(f'{component_explainer} not available, waiting...')

        # Send the goal to the action server
        future = client.send_goal_async(goal)
        future.add_done_callback(self.component_explainer_response_callback)

        # Wait for the result
        while not self.component_explainer_responded:
            result_future = future.result()
            if result_future:
                result = result_future.get_result().result
            else:
                result = GenerateComponentExplanation.Result()
                result.error_msg = f"Failed to get result from {component_explainer}"

        return result

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Configure the node."""
        self.action_server = ActionServer(self,
                                          GenerateExplanation,
                                          "/generate_explanation",
                                          goal_callback=self.on_request_goal,
                                          execute_callback=self.on_request_exec)

        # Component Explainers
        self._component_explainer_navigation_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_navigation/explain')

        self._component_explainer_b_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_sittable/explain')

        self._component_explainer_detection_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_detection/explain')

        self.component_explainers = {
            "component_explainer_navigation": self._component_explainer_navigation_client,
            "component_explainer_sittable": self._component_explainer_b_client,
            "component_explainer_detection": self._component_explainer_detection_client,
        }

        self.get_logger().info("explainer_selector is configured, but not yet active")
        time.sleep(2)  # Give some time for everything to settle
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Activate the node."""
        # Subscribers
        self._events_sub_cbGroup = MutuallyExclusiveCallbackGroup()
        self._events_subscriber = self.create_subscription(
            KeyValue,
            '/bt_status',
            self.on_new_event,
            10, callback_group=self._events_sub_cbGroup)

        self.get_logger().info("explainer_selector is active and running...")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop the timer to stop calling the `run` function (main task of your application)."""
        self.get_logger().info("Stopping skill...")

        self.get_logger().info("explainer_selector is stopped (inactive)")
        return super().on_deactivate(state)

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown the node, after a shutting-down transition is requested."""
        # Clean up any publishers/subscribers/timers here
        self.destroy_subscription(self._events_subscriber)

        self.get_logger().info('Shutting down explainer_selector skill.')

        self.action_server.destroy()

        self.get_logger().info("explainer_selector finalized.")
        return TransitionCallbackReturn.SUCCESS
