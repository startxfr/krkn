import yaml
import logging
import sys
import time
from kraken.node_actions.aws_node_scenarios import aws_node_scenarios
from kraken.node_actions.general_cloud_node_scenarios import general_node_scenarios
from kraken.node_actions.az_node_scenarios import azure_node_scenarios
from kraken.node_actions.gcp_node_scenarios import gcp_node_scenarios
from kraken.node_actions.openstack_node_scenarios import openstack_node_scenarios
from kraken.node_actions.alibaba_node_scenarios import alibaba_node_scenarios
from kraken.node_actions.bm_node_scenarios import bm_node_scenarios
import kraken.node_actions.common_node_functions as common_node_functions
import kraken.cerberus.setup as cerberus


node_general = False


# Get the node scenarios object of specfied cloud type
def get_node_scenario_object(node_scenario):
    if "cloud_type" not in node_scenario.keys() or node_scenario["cloud_type"] == "generic":
        global node_general
        node_general = True
        return general_node_scenarios()
    if node_scenario["cloud_type"] == "aws":
        return aws_node_scenarios()
    elif node_scenario["cloud_type"] == "gcp":
        return gcp_node_scenarios()
    elif node_scenario["cloud_type"] == "openstack":
        return openstack_node_scenarios()
    elif node_scenario["cloud_type"] == "azure" or node_scenario["cloud_type"] == "az":
        return azure_node_scenarios()
    elif node_scenario["cloud_type"] == "alibaba" or node_scenario["cloud_type"] == "alicloud":
        return alibaba_node_scenarios()
    elif node_scenario["cloud_type"] == "bm":
        return bm_node_scenarios(
            node_scenario.get("bmc_info"), node_scenario.get("bmc_user", None), node_scenario.get("bmc_password", None)
        )
    else:
        logging.error(
            "Cloud type " + node_scenario["cloud_type"] + " is not currently supported; "
            "try using 'generic' if wanting to stop/start kubelet or fork bomb on any "
            "cluster"
        )
        sys.exit(1)


# Run defined scenarios
def run(scenarios_list, config, wait_duration):
    for node_scenario_config in scenarios_list:
        with open(node_scenario_config, "r") as f:
            node_scenario_config = yaml.full_load(f)
            for node_scenario in node_scenario_config["node_scenarios"]:
                node_scenario_object = get_node_scenario_object(node_scenario)
                if node_scenario["actions"]:
                    for action in node_scenario["actions"]:
                        start_time = int(time.time())
                        inject_node_scenario(action, node_scenario, node_scenario_object)
                        logging.info("Waiting for the specified duration: %s" % (wait_duration))
                        time.sleep(wait_duration)
                        end_time = int(time.time())
                        cerberus.get_status(config, start_time, end_time)
                        logging.info("")


# Inject the specified node scenario
def inject_node_scenario(action, node_scenario, node_scenario_object):
    generic_cloud_scenarios = ("stop_kubelet_scenario", "node_crash_scenario")
    # Get the node scenario configurations
    run_kill_count = node_scenario.get("runs", 1)
    instance_kill_count = node_scenario.get("instance_count", 1)
    node_name = node_scenario.get("node_name", "")
    label_selector = node_scenario.get("label_selector", "")
    timeout = node_scenario.get("timeout", 120)
    service = node_scenario.get("service", "")
    ssh_private_key = node_scenario.get("ssh_private_key", "~/.ssh/id_rsa")
    # Get the node to apply the scenario
    if node_name:
        node_name_list = node_name.split(",")
    else:
        node_name_list = [node_name]
    for single_node_name in node_name_list:
        nodes = common_node_functions.get_node(single_node_name, label_selector, instance_kill_count)
        for single_node in nodes:
            if node_general and action not in generic_cloud_scenarios:
                logging.info("Scenario: " + action + " is not set up for generic cloud type, skipping action")
            else:
                if action == "node_start_scenario":
                    node_scenario_object.node_start_scenario(run_kill_count, single_node, timeout)
                elif action == "node_stop_scenario":
                    node_scenario_object.node_stop_scenario(run_kill_count, single_node, timeout)
                elif action == "node_stop_start_scenario":
                    node_scenario_object.node_stop_start_scenario(run_kill_count, single_node, timeout)
                elif action == "node_termination_scenario":
                    node_scenario_object.node_termination_scenario(run_kill_count, single_node, timeout)
                elif action == "node_reboot_scenario":
                    node_scenario_object.node_reboot_scenario(run_kill_count, single_node, timeout)
                elif action == "stop_start_kubelet_scenario":
                    node_scenario_object.stop_start_kubelet_scenario(run_kill_count, single_node, timeout)
                elif action == "stop_kubelet_scenario":
                    node_scenario_object.stop_kubelet_scenario(run_kill_count, single_node, timeout)
                elif action == "node_crash_scenario":
                    node_scenario_object.node_crash_scenario(run_kill_count, single_node, timeout)
                elif action == "stop_start_helper_node_scenario":
                    if node_scenario["cloud_type"] != "openstack":
                        logging.error(
                            "Scenario: " + action + " is not supported for "
                            "cloud type " + node_scenario["cloud_type"] + ", skipping action"
                        )
                    else:
                        if not node_scenario["helper_node_ip"]:
                            logging.error("Helper node IP address is not provided")
                            sys.exit(1)
                        node_scenario_object.helper_node_stop_start_scenario(
                            run_kill_count, node_scenario["helper_node_ip"], timeout
                        )
                        node_scenario_object.helper_node_service_status(
                            node_scenario["helper_node_ip"], service, ssh_private_key, timeout
                        )
                else:
                    logging.info("There is no node action that matches %s, skipping scenario" % action)
