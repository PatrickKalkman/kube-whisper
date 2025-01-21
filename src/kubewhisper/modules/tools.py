import random
import datetime
from kubernetes import client, config


async def get_current_time():
    return {"current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


async def get_random_number():
    return {"random_number": random.randint(1, 100)}


async def get_number_of_nodes():
    """Returns the number of nodes in the current Kubernetes cluster."""
    try:
        # Load kube config from default location
        config.load_kube_config()

        # Create API client
        v1 = client.CoreV1Api()

        # List all nodes
        nodes = v1.list_node()

        return {"node_count": len(nodes.items)}
    except Exception as e:
        return {"error": f"Failed to get node count: {str(e)}"}


async def get_number_of_pods():
    """Returns the number of pods in the current Kubernetes cluster."""
    try:
        # Load kube config from default location
        config.load_kube_config()

        # Create API client
        v1 = client.CoreV1Api()

        # List all pods across all namespaces
        pods = v1.list_pod_for_all_namespaces()

        return {"pod_count": len(pods.items)}
    except Exception as e:
        return {"error": f"Failed to get pod count: {str(e)}"}


async def get_number_of_namespaces():
    """Returns the number of namespaces in the current Kubernetes cluster."""
    try:
        # Load kube config from default location
        config.load_kube_config()

        # Create API client
        v1 = client.CoreV1Api()

        # List all namespaces
        namespaces = v1.list_namespace()

        return {"namespace_count": len(namespaces.items)}
    except Exception as e:
        return {"error": f"Failed to get namespace count: {str(e)}"}


# Map function names to their corresponding functions
function_map = {
    "get_current_time": get_current_time,
    "get_random_number": get_random_number,
    "get_number_of_nodes": get_number_of_nodes,
    "get_number_of_pods": get_number_of_pods,
    "get_number_of_namespaces": get_number_of_namespaces,
    "get_cluster_information": get_cluster_information,
}

# Tools array for session initialization
tools = [
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Returns the current time.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_random_number",
        "description": "Returns a random number between 1 and 100.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_number_of_nodes",
        "description": "Returns the number of nodes in a Kubernetes cluster.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_number_of_pods",
        "description": "Returns the number of pods in a Kubernetes cluster.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_number_of_namespaces",
        "description": "Returns the number of namespaces in a Kubernetes cluster.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "open_browser",
        "description": "Opens a browser tab with the best-fitting URL based on the user's prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user's prompt to determine which URL to open.",
                },
            },
            "required": ["prompt"],
        },
    },
]
