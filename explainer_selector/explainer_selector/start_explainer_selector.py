import rclpy

from rclpy.executors import MultiThreadedExecutor

import explainer_selector.explainer_selector_impl


def main():
    rclpy.init()

    skill = explainer_selector.explainer_selector_impl.GenerateExplanationImpl()
    skill_executor = MultiThreadedExecutor()
    skill_executor.add_node(skill)

    try:
        skill_executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        print("Goodbye!")
        skill.destroy_node()


if __name__ == '__main__':
    main()
