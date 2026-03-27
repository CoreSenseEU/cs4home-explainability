import rosbag2_py
import subprocess
import time
import rclpy

from explainability_msgs.action import GenerateExplanation
from rclpy.action import ActionClient
from rclpy.node import Node

BAGFILE_PATH = "/home/user/exchange/rosbag2_2026_03_24-14_45_30"

START_TIMESTAMP = "1774363640"
TRIGGER_EXPLANATION_TIMESTAMP = "1774363692"
RATE = "1"

# Get the initial timestamp of the bagfile
storage_options = rosbag2_py.StorageOptions(uri=BAGFILE_PATH, storage_id="sqlite3")
converter_options = rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr")
reader = rosbag2_py.SequentialReader()
reader.open(storage_options, converter_options)
metadata = reader.get_metadata()
start_time_ns = metadata.starting_time.nanoseconds
bag_start_timestamp = start_time_ns / 1e9

# Calculate offset
start_offset = float(START_TIMESTAMP) - bag_start_timestamp
trigger_explanation_offset = float(TRIGGER_EXPLANATION_TIMESTAMP) - bag_start_timestamp - start_offset
print(f"Bag start timestamp: {bag_start_timestamp}")
print(f"Start offset: {start_offset}")
print(f"Trigger explanation offset: {trigger_explanation_offset}")


class ExperimentRunner(Node):
    def __init__(self):
        super().__init__('experiment_runner')
        self.action_explain_client = ActionClient(self, GenerateExplanation, '/generate_explanation')

    def call_explain_action(self, question):
        """Call the explain action and return the explanation."""
        self.get_logger().info('Waiting for action server...')
        self.action_explain_client.wait_for_server()

        goal_msg = GenerateExplanation.Goal()
        goal_msg.question = question
        goal_msg.auto_triggered = True
        self.get_logger().info('Sending goal...')

        future = self.action_explain_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return None

        self.get_logger().info('Goal accepted, waiting for result...')
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result().result
        return result.explanation


rclpy.init()

experiment_runner = ExperimentRunner()

# Play bagfile with calculated offset
bagfile_play = subprocess.Popen([
    "ros2", "bag", "play",
    BAGFILE_PATH,
    "--start-offset", str(start_offset),
    "--clock",
    "--rate", RATE
])

# Launch explainers
cmd = ["ros2", "launch", "explainer_selector", "explainer_selector.launch.py"]
explainers_launch = subprocess.Popen(cmd)

print(f"Waiting for {trigger_explanation_offset * float(RATE)} seconds before triggering explanation...")

time.sleep(trigger_explanation_offset * float(RATE))

print("TERMINATING BAGFILE PLAYBACK...")

# stop the bagfile playback
bagfile_play.terminate()

# Call explain action
explanation = experiment_runner.call_explain_action("IsSittable")

print("Explanation received:")
print(explanation)

# Terminate explainers
explainers_launch.terminate()
