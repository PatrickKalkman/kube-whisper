import datetime
import random
from kubernetes import client, config


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


async def get_cluster_information():
    """Returns comprehensive information about the Kubernetes cluster."""
    try:
        # Load kube config from default location
        config.load_kube_config()

        # Create API client
        v1 = client.CoreV1Api()

        # Get all resources
        nodes = v1.list_node()
        pods = v1.list_pod_for_all_namespaces()
        namespaces = v1.list_namespace()

        return {
            "cluster_info": {"nodes": len(nodes.items), "pods": len(pods.items), "namespaces": len(namespaces.items)}
        }
    except Exception as e:
        return {"error": f"Failed to get cluster information: {str(e)}"}


# Map function names to their corresponding functions
function_map = {
    "get_number_of_nodes": get_number_of_nodes,
    "get_number_of_pods": get_number_of_pods,
    "get_number_of_namespaces": get_number_of_namespaces,
    "get_cluster_information": get_cluster_information,
}

# Tools array for session initialization
tools = [
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
        "name": "get_cluster_information",
        "description": (
            "Returns comprehensive information about the Kubernetescluster including node, pod, and namespace counts."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
