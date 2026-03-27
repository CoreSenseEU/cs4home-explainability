Coresense Explainability Framework
====================

This repository contains an implementation of Coresense explainability ofr the Robocup@Home league.


The main elements of the framework are:
- Component Explainers: These are responsible for generating explanations tailored to specific modules of the robotic system. In this case, we have implemented three component explainers: for the IsDetected module, the IsSittable module and the MoveTo module.
- Explainer Selector: This module selects the most appropriate component explainer based on the behaviour tree status.

Getting Started
----------------
To test the current implementation, you can first build the workspace and then launch the explainer selector along with the component explainers using the provided launch file. Remember to set your API key for the LLM service as a launch argument, or point to your local ollama server.

```bash
colcon build
source install/setup.bash
ros2 launch explainer_selector explainer_selector.launch.py

ros2 action send_goal /generate_explanation explainability_msgs/action/GenerateExplanation "question: ''
auto_triggered: true" 
```