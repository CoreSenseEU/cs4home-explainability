# CoreSense4Home Explainability

This repository provides the explainability framework used by the CoreSense4Home RoboCup@Home testbed. It collects behaviour-tree status and component evidence, selects the relevant component explainer and returns a short explanation of the robot's behaviour.

The implemented component explainers cover `IsDetected`, `IsSittable` and `MoveTo`.

## CoreSense role

The terms below follow the [CoreSense Ontology (CSO)](https://w3id.org/coresense/cso).

- Explanation generation is a [Cognitive Function](https://w3id.org/coresense/cso#CognitiveFunction) that processes execution information.
- The framework provides the [Cognitive Capability](https://w3id.org/coresense/cso#CognitiveCapability) to explain selected robot actions and failures to a person.
- Behaviour-tree events and component logs form the relevant [Context](https://w3id.org/coresense/cso#Context).
- The generated explanation communicates the [Meaning](https://w3id.org/coresense/cso#Meaning) assigned to the observed execution evidence.

## Data flow

~~~mermaid
flowchart LR
    events["Behaviour-tree status and component evidence"] --> selector["Explainer selector"]
    question["Explanation request"] --> selector
    selector --> component["Detection, seating or navigation explainer"]
    component --> explanation["Human-readable explanation"]
~~~

The repository contains the selector, three component explainers and the `explainability_msgs` interfaces.

## Requirements and build

Use a ROS 2 Humble workspace containing the CoreSense4Home dependencies. The navigation explainer also requires the LLM service used by `llama_ros`.

~~~bash
mkdir -p ~/cs4home_ws/src
cd ~/cs4home_ws/src
git clone https://github.com/CoreSenseEU/cs4home-explainability.git
cd ..
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
~~~

## Run

The launch file starts the selector and all component explainers, then configures and activates their lifecycle nodes.

~~~bash
ros2 launch explainer_selector explainer_selector.launch.py
~~~

Request an explanation with:

~~~bash
ros2 action send_goal /generate_explanation \
  explainability_msgs/action/GenerateExplanation \
  "{question: 'Why did IsDetected fail?', auto_triggered: false}"
~~~

## Acknowledgement

<img src="https://github.com/user-attachments/assets/b11da974-9201-4f79-902e-c9c20e8aa7a4" alt="Funded by the European Union" width="240"/>

This work has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement No 101070254 ([CORESENSE](https://coresense.eu)). Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Commission. Neither the European Union nor the granting authority can be held responsible for them.
