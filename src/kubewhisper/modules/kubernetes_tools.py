import datetime
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


async def get_cluster_status():
    """Returns detailed status information about the Kubernetes cluster."""
    try:
        # Load kube config
        config.load_kube_config()
        
        # Initialize API clients
        v1 = client.CoreV1Api()
        custom = client.CustomObjectsApi()
        
        # Get nodes info
        nodes = v1.list_node()
        node_count = len(nodes.items)
        
        # Get metrics using metrics API
        metrics = custom.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )
        
        # Calculate resource usage
        total_cpu_usage = 0
        total_memory_usage = 0
        for item in metrics['items']:
            cpu = item['usage']['cpu']
            memory = item['usage']['memory']
            # Convert CPU from 'n' format to percentage
            total_cpu_usage += int(cpu.rstrip('n')) / 1000000000 * 100
            
            # Convert memory to bytes
            if memory.endswith('Ki'):
                memory_bytes = float(memory.rstrip('Ki')) * 1024
            elif memory.endswith('Mi'):
                memory_bytes = float(memory.rstrip('Mi')) * 1024 * 1024
            elif memory.endswith('Gi'):
                memory_bytes = float(memory.rstrip('Gi')) * 1024 * 1024 * 1024
            elif memory.endswith('Ti'):
                memory_bytes = float(memory.rstrip('Ti')) * 1024 * 1024 * 1024 * 1024
            else:
                # Assume it's in bytes if no suffix
                memory_bytes = float(memory)
            
            # Convert to GB
            total_memory_usage += memory_bytes / (1024 * 1024 * 1024)
            
        avg_cpu = total_cpu_usage / node_count if node_count > 0 else 0
        avg_memory = total_memory_usage / node_count if node_count > 0 else 0
        
        # Get pods across all namespaces
        pods = v1.list_pod_for_all_namespaces()
        pod_status = {}
        total_pods = 0
        
        for pod in pods.items:
            status = pod.status.phase
            pod_status[status] = pod_status.get(status, 0) + 1
            total_pods += 1
            
        # Get recent events (last 15 minutes)
        events = v1.list_event_for_all_namespaces()
        recent_issues = []
        fifteen_mins_ago = datetime.datetime.now(datetime.timezone.utc).timestamp() - (15 * 60)
        
        for event in events.items:
            if (event.type == "Warning" and 
                event.last_timestamp and 
                event.last_timestamp.timestamp() > fifteen_mins_ago):
                recent_issues.append({
                    "reason": event.reason,
                    "message": event.message,
                    "component": event.involved_object.kind
                })
        
        # Prepare status response
        status_response = {
            "cluster_health": {
                "total_nodes": node_count,
                "avg_cpu_usage": f"{avg_cpu:.1f}%",
                "avg_memory_usage": f"{avg_memory:.1f}GB",
                "pod_count": {
                    "total": total_pods,
                    **pod_status
                }
            },
            "recent_issues": {
                "count": len(recent_issues),
                "summary": recent_issues
            } if recent_issues else None,
            "status_summary": "Issues Detected" if recent_issues else "All Systems Normal",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        return status_response
        
    except Exception as e:
        return {
            "error": "Failed to get cluster status",
            "message": str(e)
        }


# Map function names to their corresponding functions
function_map = {
    "get_number_of_nodes": get_number_of_nodes,
    "get_number_of_pods": get_number_of_pods,
    "get_number_of_namespaces": get_number_of_namespaces,
    "get_cluster_status": get_cluster_status,
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
        "name": "get_cluster_status",
        "description": (
            "Returns detailed status information about the Kubernetes cluster including node metrics, "
            "pod status, resource usage, and recent issues."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
