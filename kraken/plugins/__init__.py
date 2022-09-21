import dataclasses
import json
import logging
from os.path import abspath
from typing import List, Dict

from arcaflow_plugin_sdk import schema, serialization, jsonschema
import kraken.plugins.vmware.vmware_plugin as vmware_plugin
from kraken.plugins.pod_plugin import kill_pods, wait_for_pods
from kraken.plugins.run_python_plugin import run_python_file
from kraken.plugins.network.ingress_shaping import network_chaos


@dataclasses.dataclass
class PluginStep:
    schema: schema.StepSchema
    error_output_ids: List[str]

    def render_output(self, output_id: str, output_data) -> str:
        return json.dumps({
            "output_id": output_id,
            "output_data": self.schema.outputs[output_id].serialize(output_data),
        }, indent='\t')


class Plugins:
    """
    Plugins is a class that can run plugins sequentially. The output is rendered to the standard output and the process
    is aborted if a step fails.
    """
    steps_by_id: Dict[str, PluginStep]

    def __init__(self, steps: List[PluginStep]):
        self.steps_by_id = dict()
        for step in steps:
            if step.schema.id in self.steps_by_id:
                raise Exception(
                    "Duplicate step ID: {}".format(step.schema.id)
                )
            self.steps_by_id[step.schema.id] = step

    def run(self, file: str, kubeconfig_path: str):
        """
        Run executes a series of steps
        """
        data = serialization.load_from_file(abspath(file))
        if not isinstance(data, list):
            raise Exception(
                "Invalid scenario configuration file: {} expected list, found {}".format(file, type(data).__name__)
            )
        i = 0
        for entry in data:
            if not isinstance(entry, dict):
                raise Exception(
                    "Invalid scenario configuration file: {} expected a list of dict's, found {} on step {}".format(
                        file,
                        type(entry).__name__,
                        i
                    )
                )
            if "id" not in entry:
                raise Exception(
                    "Invalid scenario configuration file: {} missing 'id' field on step {}".format(
                        file,
                        i,
                    )
                )
            if "config" not in entry:
                raise Exception(
                    "Invalid scenario configuration file: {} missing 'config' field on step {}".format(
                        file,
                        i,
                    )
                )

            if entry["id"] not in self.steps_by_id:
                raise Exception(
                    "Invalid step {} in {} ID: {} expected one of: {}".format(
                        i,
                        file,
                        entry["id"],
                        ', '.join(self.steps_by_id.keys())
                    )
                )
            step = self.steps_by_id[entry["id"]]
            unserialized_input = step.schema.input.unserialize(entry["config"])
            if "kubeconfig_path" in step.schema.input.properties:
                unserialized_input.kubeconfig_path = kubeconfig_path
            output_id, output_data = step.schema(unserialized_input)
            logging.info(step.render_output(output_id, output_data) + "\n")
            if output_id in step.error_output_ids:
                raise Exception(
                    "Step {} in {} ({}) failed".format(i, file, step.schema.id)
                )
            i = i + 1

    def json_schema(self):
        """
        This function generates a JSON schema document and renders it from the steps passed.
        """
        result = {
            "$id": "https://github.com/redhat-chaos/krkn/",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Kraken Arcaflow scenarios",
            "description": "Serial execution of Arcaflow Python plugins. See https://github.com/arcaflow for details.",
            "type": "array",
            "minContains": 1,
            "items": {
                "oneOf": [

                ]
            }
        }
        for step_id in self.steps_by_id.keys():
            step = self.steps_by_id[step_id]
            step_input = jsonschema.step_input(step.schema)
            del step_input["$id"]
            del step_input["$schema"]
            del step_input["title"]
            del step_input["description"]
            result["items"]["oneOf"].append({
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "const": step_id,
                    },
                    "config": step_input,
                },
                "required": [
                    "id",
                    "config",
                ]
            })
        return json.dumps(result, indent="\t")


PLUGINS = Plugins(
    [
        PluginStep(
            kill_pods,
            [
                "error",
            ]
        ),
        PluginStep(
            wait_for_pods,
            [
                "error"
            ]
        ),
        PluginStep(
            run_python_file,
            [
                "error"
            ]
        ),
        PluginStep(
            vmware_plugin.node_start,
            [
                "error"
            ]
        ),
        PluginStep(
            vmware_plugin.node_stop,
            [
                "error"
            ]
        ),
        PluginStep(
            vmware_plugin.node_reboot,
            [
                "error"
            ]
        ),
        PluginStep(
            vmware_plugin.node_terminate,
            [
                "error"
            ]
        ),
        PluginStep(
            network_chaos,
            [
                "error"
            ]
        )
    ]
)


def run(scenarios: List[str], kubeconfig_path: str, failed_post_scenarios: List[str]) -> List[str]:
    for scenario in scenarios:
        try:
            PLUGINS.run(scenario, kubeconfig_path)
        except Exception as e:
            failed_post_scenarios.append(scenario)
            logging.error("Error while running {}: {}".format(scenario, e))
            return failed_post_scenarios
    return failed_post_scenarios
