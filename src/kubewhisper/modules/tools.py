import random
import datetime


async def get_current_time():
    return {"current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


async def get_random_number():
    return {"random_number": random.randint(1, 100)}


# Map function names to their corresponding functions
function_map = {
    "get_current_time": get_current_time,
    "get_random_number": get_random_number,
    "get_number_of_nodes": get_number_of_nodes,
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
