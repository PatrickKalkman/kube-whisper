import datetime
import re
import os
from collections import defaultdict
import aiohttp
import yaml
from kubernetes import client, config
from typing import Dict, Any


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


async def analyze_deployment_logs(deployment_name: str, namespace: str = "default"):
    """Analyze logs from all pods in a deployment for criticals/errors/warnings in the last hour."""
    try:
        config.load_kube_config()
        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        # Get pods from deployment
        deployment = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)

        # Get label selector
        selector = deployment.spec.selector.match_labels
        label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])

        # Get pods with this selector
        pods = core_v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        error_patterns = {
            "exception": r"(?i)(exception|error|failure|failed|traceback)",
            "warning": r"(?i)(warning|warn)",
            "critical": r"(?i)(critical|fatal|panic)",
            "timeout": r"(?i)(timeout|timed out)",
            "connection": r"(?i)(connection refused|connection reset|connection closed)",
            "permission": r"(?i)(permission denied|unauthorized|forbidden)",
            "memory": r"(?i)(out of memory|memory limit)",
            "disk": r"(?i)(disk full|no space left)",
        }

        errors = defaultdict(list)
        error_counts = defaultdict(int)
        total_errors = 0
        current_time = datetime.datetime.now(datetime.timezone.utc)
        time_threshold = current_time - datetime.timedelta(minutes=60)

        for pod in pods.items:
            try:
                logs = core_v1.read_namespaced_pod_log(
                    name=pod.metadata.name, namespace=namespace, tail_lines=1000, timestamps=True
                )

                for line in logs.split("\n"):
                    if not line.strip():
                        continue

                    try:
                        # Split timestamp and log message
                        timestamp_str = line.split()[0]
                        timestamp = datetime.datetime.fromisoformat(timestamp_str.rstrip("Z")).replace(
                            tzinfo=datetime.timezone.utc
                        )

                        # Check if log is within time window
                        if timestamp < time_threshold:
                            continue

                        # Check for different error patterns
                        for error_type, pattern in error_patterns.items():
                            if re.search(pattern, line):
                                errors[error_type].append(
                                    {
                                        "timestamp": timestamp_str,
                                        "message": line.strip(),
                                        "age_minutes": round((current_time - timestamp).total_seconds() / 60, 1),
                                    }
                                )
                                error_counts[error_type] += 1
                                total_errors += 1

                    except Exception:
                        continue

            except Exception as e:
                errors["pod_access_errors"].append(f"Could not access logs for pod {pod.metadata.name}: {str(e)}")

        return {
            "summary": {
                "total_errors": total_errors,
                "error_types": dict(error_counts),
                "pods_analyzed": len(pods.items),
                "time_window_minutes": 60,
            },
            "detailed_errors": dict(errors),
        }

    except Exception as e:
        return {"error": f"Failed to analyze logs: {str(e)}"}


async def get_version_info():
    """Returns version information for both Kubernetes API server and nodes."""
    try:
        config.load_kube_config()
        version_api = client.VersionApi()
        core_api = client.CoreV1Api()
        
        # Get API server version
        api_version = version_api.get_code()
        
        # Get node versions
        nodes = core_api.list_node()
        node_versions = {}
        for node in nodes.items:
            version = node.status.node_info.kubelet_version
            node_versions[node.metadata.name] = version
            
        return {
            "api_server": {
                "version": api_version.git_version,
                "platform": api_version.platform,
                "build_date": api_version.build_date
            },
            "nodes": node_versions
        }
    except Exception as e:
        return {"error": f"Failed to get version info: {str(e)}"}

async def get_kubernetes_latest_version_information() -> Dict[str, Any]:
    """Retrieves the latest stable version information from the Kubernetes GitHub repository."""
    try:
        async with aiohttp.ClientSession() as session:
            # Get releases from GitHub API
            async with session.get('https://api.github.com/repos/kubernetes/kubernetes/releases') as response:
                if response.status != 200:
                    return {"error": f"GitHub API request failed with status {response.status}"}
                
                releases = await response.json()
                
                # Filter and process releases
                stable_releases = []
                for release in releases:
                    if not release['prerelease'] and not release['draft']:
                        version = release['tag_name'].lstrip('v')
                        published_at = release['published_at']
                        stable_releases.append({
                            "version": version,
                            "published_at": published_at,
                            "html_url": release['html_url']
                        })
                        if len(stable_releases) >= 5:  # Get latest 5 stable releases
                            break
                
                if not stable_releases:
                    return {"error": "No stable releases found"}
                
                return {
                    "latest_stable_version": stable_releases[0]['version'],
                    "latest_releases": stable_releases,
                    "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                
    except Exception as e:
        return {"error": f"Failed to get Kubernetes version information: {str(e)}"}

async def get_available_clusters():
    """Returns a list of all available Kubernetes clusters from the kubeconfig."""
    try:
        # Get all contexts from kubeconfig
        contexts, active_context = config.list_kube_config_contexts()
        if not contexts:
            return {"error": "No Kubernetes contexts found in kubeconfig"}
            
        clusters = []
        active_cluster = None
        
        for ctx in contexts:
            cluster_info = {
                "name": ctx['context']['cluster'],
                "context_name": ctx['name'],
                "is_active": ctx == active_context
            }
            clusters.append(cluster_info)
            if cluster_info["is_active"]:
                active_cluster = cluster_info
                
        return {
            "clusters": clusters,
            "active_cluster": active_cluster,
            "total_clusters": len(clusters)
        }
    except config.config_exception.ConfigException as e:
        return {"error": f"Failed to get cluster information: {str(e)}"}

async def switch_cluster(cluster_name: str):
    """Switch to a different Kubernetes cluster context and persist the change."""
    try:
        # Get all available contexts
        contexts, active_context = config.list_kube_config_contexts()
        
        # Find the context that matches the requested cluster name
        target_context = None
        for ctx in contexts:
            if ctx['context']['cluster'] == cluster_name:
                target_context = ctx['name']
                break
                
        if not target_context:
            return {
                "error": f"Cluster '{cluster_name}' not found in kubeconfig",
                "available_clusters": [ctx['context']['cluster'] for ctx in contexts]
            }
            
        # Use the config module to directly modify current context
        config_file = os.path.expanduser(config.kube_config.KUBE_CONFIG_DEFAULT_LOCATION)
        config.kube_config.load_kube_config()
        
        # Load and modify the config file
        with open(config_file) as f:
            kube_config = yaml.safe_load(f)
        
        # Update the current-context
        kube_config['current-context'] = target_context
        
        # Save the changes back to the config file
        with open(config_file, 'w') as f:
            yaml.safe_dump(kube_config, f)
        
        # Load the new context for the current session
        config.load_kube_config(context=target_context)
        
        return {
            "success": True,
            "message": f"Successfully switched to cluster '{cluster_name}' and persisted the change",
            "context": target_context
        }
        
    except config.config_exception.ConfigException as e:
        return {"error": f"Failed to switch cluster: {str(e)}"}

async def get_cluster_name():
    """Returns the name of the current Kubernetes cluster."""
    try:
        # Load kube config
        config.load_kube_config()
        
        # Get current context info
        contexts, active_context = config.list_kube_config_contexts()
        if not active_context:
            return {"error": "No active Kubernetes context found"}
            
        cluster_name = active_context['context']['cluster']
        return {
            "cluster_name": cluster_name,
            "context_name": active_context['name']
        }
    except config.config_exception.ConfigException as e:
        return {"error": f"Failed to get cluster name: {str(e)}"}

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
        metrics = custom.list_cluster_custom_object(group="metrics.k8s.io", version="v1beta1", plural="nodes")

        # Calculate resource usage
        total_cpu_usage = 0
        total_memory_usage = 0
        for item in metrics["items"]:
            cpu = item["usage"]["cpu"]
            memory = item["usage"]["memory"]
            # Convert CPU from 'n' format to percentage
            total_cpu_usage += int(cpu.rstrip("n")) / 1000000000 * 100

            # Convert memory to bytes
            if memory.endswith("Ki"):
                memory_bytes = float(memory.rstrip("Ki")) * 1024
            elif memory.endswith("Mi"):
                memory_bytes = float(memory.rstrip("Mi")) * 1024 * 1024
            elif memory.endswith("Gi"):
                memory_bytes = float(memory.rstrip("Gi")) * 1024 * 1024 * 1024
            elif memory.endswith("Ti"):
                memory_bytes = float(memory.rstrip("Ti")) * 1024 * 1024 * 1024 * 1024
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
            if event.type == "Warning" and event.last_timestamp and event.last_timestamp.timestamp() > fifteen_mins_ago:
                recent_issues.append(
                    {"reason": event.reason, "message": event.message, "component": event.involved_object.kind}
                )

        # Prepare status response
        status_response = {
            "cluster_health": {
                "total_nodes": node_count,
                "avg_cpu_usage": f"{avg_cpu:.1f}%",
                "avg_memory_usage": f"{avg_memory:.1f}GB",
                "pod_count": {"total": total_pods, **pod_status},
            },
            "recent_issues": {"count": len(recent_issues), "summary": recent_issues} if recent_issues else None,
            "status_summary": ("Issues Detected" if recent_issues else "All Systems Normal"),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        return status_response

    except Exception as e:
        return {"error": "Failed to get cluster status", "message": str(e)}


# Map function names to their corresponding functions
function_map = {
    "get_number_of_nodes": get_number_of_nodes,
    "get_number_of_pods": get_number_of_pods,
    "get_number_of_namespaces": get_number_of_namespaces,
    "get_cluster_status": get_cluster_status,
    "analyze_deployment_logs": analyze_deployment_logs,
    "get_version_info": get_version_info,
    "get_kubernetes_latest_version_information": get_kubernetes_latest_version_information,
    "get_cluster_name": get_cluster_name,
    "get_available_clusters": get_available_clusters,
    "switch_cluster": switch_cluster,
}

# Tools array for session initialization
tools = [
    {
        "type": "function",
        "name": "switch_cluster",
        "description": "Switch to a different Kubernetes cluster using its name.",
        "parameters": {
            "type": "object",
            "properties": {
                "cluster_name": {
                    "type": "string",
                    "description": "The name of the cluster to switch to"
                }
            },
            "required": ["cluster_name"],
        },
    },
    {
        "type": "function",
        "name": "get_available_clusters",
        "description": "Returns a list of all available Kubernetes clusters configured in kubeconfig.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_cluster_name",
        "description": "Returns the name of the current Kubernetes cluster and its context.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_kubernetes_latest_version_information",
        "description": "Retrieves the latest stable version information from the Kubernetes GitHub repository.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_version_info",
        "description": "Returns version information for both Kubernetes API server and nodes.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "analyze_deployment_logs",
        "description": ("Analyzes logs from all pods in a deployment for criticals/errors/warnings in the last hour."),
        "parameters": {
            "type": "object",
            "properties": {
                "deployment_name": {"type": "string", "description": "The name of the deployment to analyze"},
                "namespace": {"type": "string", "description": "The namespace of the deployment", "default": "default"},
            },
            "required": ["deployment_name"],
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
        "name": "get_cluster_status",
        "description": (
            "Returns detailed status information about the Kubernetes cluster "
            "including node metrics, pod status, resource usage, and recent issues."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
