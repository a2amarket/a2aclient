import httpx
import json
from typing import Dict, Any, Optional
from models import AgentCard
import uuid

class A2AClientError(Exception):
    """Base class for A2A client errors"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class A2AClientHTTPError(A2AClientError):
    """HTTP error from A2A client"""
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(f"HTTP error {status_code}: {message}")

class A2AClientJSONError(A2AClientError):
    """JSON parsing error from A2A client"""
    pass

class A2AClient:
    """Client for interacting with A2A protocol compatible agents"""
    
    def __init__(self, agent_card: AgentCard = None, url: str = None, auth_token: str = None):
        """Initialize the client with either an agent card or a URL"""
        if agent_card:
            self.url = agent_card.url.rstrip('/')
        elif url:
            self.url = url.rstrip('/')
        else:
            raise ValueError("Must provide either agent_card or url")
            
        self.auth_token = auth_token
    
    def send_task(self, payload: Dict[str, Any], task_id: str = None) -> Dict[str, Any]:
        """Send a task to the agent"""
        if not task_id:
            task_id = str(uuid.uuid4())
            
        # Format exactly like the CLI sample
        request = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "message": {
                    "role": payload.get("role", "user"),
                    "parts": payload.get("parts", [])
                },
                "metadata": payload.get("metadata", {})
            }
        }
        
        # Add push notification if supported
        if hasattr(self, 'notification_url') and self.notification_url:
            request["params"]["pushNotification"] = {
                "url": self.notification_url,
                "authentication": {
                    "schemes": ["bearer"],
                }
            }
        
        return self._send_request(request)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task"""
        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tasks/get",
            "params": {
                "id": task_id
            }
        }
        
        return self._send_request(request)
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the agent"""
        try:
            print(f"Sending request to {self.url}: {json.dumps(request, indent=2)}")
            
            headers = {'Content-Type': 'application/json'}
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
                
            response = httpx.post(
                self.url,
                json=request,
                headers=headers,
                timeout=30.0
            )
            
            # Print the raw response for debugging
            print(f"Received HTTP {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            try:
                # Try to get the response text even if it's not valid JSON
                print(f"Response body: {response.text}")
            except:
                print("Could not read response text")
                
            response.raise_for_status()
            
            result = response.json()
            print(f"Parsed JSON response: {json.dumps(result, indent=2)}")
            return result
        except httpx.HTTPStatusError as e:
            # Try to parse the error response JSON if available
            error_detail = ""
            try:
                error_json = e.response.json()
                error_detail = json.dumps(error_json)
            except:
                error_detail = e.response.text if hasattr(e.response, 'text') else ""
                
            raise A2AClientHTTPError(
                e.response.status_code, 
                f"{str(e)}. Response: {error_detail}"
            )
        except json.JSONDecodeError as e:
            raise A2AClientJSONError(f"Failed to parse JSON response: {str(e)}")
        except httpx.RequestError as e:
            raise A2AClientHTTPError(500, f"Request failed: {str(e)}") 