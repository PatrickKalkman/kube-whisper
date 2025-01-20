from kubernetes import client, config
from loguru import logger


class KubernetesManager:
    def __init__(self):
        """Initialize Kubernetes client."""
        try:
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            logger.info("Successfully initialized Kubernetes client")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def get_pod_count(self) -> int:
        """Get total number of pods across all namespaces."""
        try:
            pods = self.v1.list_pod_for_all_namespaces()
            count = len(pods.items)
            logger.info(f"Found {count} pods")
            return count
        except Exception as e:
            logger.error(f"Error getting pod count: {e}")
            raise

    def get_node_count(self) -> int:
        """Get total number of nodes in the cluster."""
        try:
            nodes = self.v1.list_node()
            count = len(nodes.items)
            logger.info(f"Found {count} nodes")
            return count
        except Exception as e:
            logger.error(f"Error getting node count: {e}")
            raise

    def get_cluster_status(self) -> dict:
        """Get comprehensive cluster status including nodes and pods."""
        try:
            nodes = self.v1.list_node()
            pods = self.v1.list_pod_for_all_namespaces()

            # Count nodes by status
            node_status = {}
            for node in nodes.items:
                for condition in node.status.conditions:
                    if condition.type == "Ready":
                        status = "Ready" if condition.status == "True" else "NotReady"
                        node_status[status] = node_status.get(status, 0) + 1
                        break

            # Count pods by phase
            pod_status = {}
            for pod in pods.items:
                phase = pod.status.phase
                pod_status[phase] = pod_status.get(phase, 0) + 1

            status = {
                "nodes": {"total": len(nodes.items), "status": node_status},
                "pods": {"total": len(pods.items), "status": pod_status},
            }

            logger.info(f"Cluster status: {status}")
            return status
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            raise
