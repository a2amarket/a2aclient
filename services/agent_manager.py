import os
import json
import httpx
import traceback
import uuid
from typing import List, Dict, Any, Optional, Tuple
from models import AgentCard, AgentSkill, AgentCapabilities, Message, Part
from services.a2a_client import A2AClient, A2AClientHTTPError, A2AClientJSONError

class AgentManager:
    """Manages AI agents and routes messages to the appropriate agent."""
    
    def __init__(self):
        self.agents: Dict[str, AgentCard] = {}
        self._pending_tasks: Dict[str, Dict[str, Any]] = {}
        # No default host agent initialization anymore
    
    def register_agent_from_url(self, url: str) -> Optional[AgentCard]:
        """Register an agent from its agent card URL."""
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                print(f"Added http:// prefix to URL: {url}")
                
            # Ensure URL is properly formatted (remove trailing slashes)
            url = url.rstrip("/")
            
            # Try to fetch the agent card - check if the URL already points to agent.json
            agent_card_url = url
            if not url.endswith('agent.json'):
                # Try the well-known path first
                well_known_url = f"{url}/.well-known/agent.json" 
                print(f"Attempting to fetch agent card from well-known URL: {well_known_url}")
                try:
                    response = httpx.get(well_known_url, timeout=15.0)
                    response.raise_for_status()
                    agent_card_url = well_known_url
                    print(f"Successfully found agent card at well-known URL")
                except (httpx.HTTPStatusError, httpx.RequestError):
                    # If well-known path fails, try the base URL
                    print(f"No agent card found at well-known URL, trying base URL: {url}")
                    response = httpx.get(url, timeout=15.0)
                    response.raise_for_status()
            else:
                # URL already points to agent.json
                print(f"Fetching agent card from URL: {url}")
                response = httpx.get(url, timeout=15.0)
                response.raise_for_status()
            
            agent_data = response.json()
            print(f"Received agent data: {json.dumps(agent_data)}")
            
            # Validate received data has minimum required fields
            required_fields = ['name']
            missing_fields = [field for field in required_fields if field not in agent_data]
            if missing_fields:
                print(f"Error: Missing required fields in agent data: {', '.join(missing_fields)}")
                return None
            
            # Set the URL if not present or different from the request URL
            if "url" not in agent_data:
                # Set the base URL (not the agent.json URL)
                agent_data["url"] = url
                print(f"Added missing URL field: {url}")
            else:
                print(f"Using URL from agent data: {agent_data['url']}")
                
            # Create the agent card
            try:
                agent = AgentCard(**agent_data)
                return self.register_agent(agent)
            except Exception as e:
                print(f"Error creating AgentCard from data: {str(e)}")
                traceback.print_exc()
                return None
                
        except httpx.TimeoutError:
            print(f"Timeout error connecting to agent URL {url}. The server took too long to respond.")
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error accessing agent URL {url}: {e.response.status_code} {e.response.reason_phrase}")
            if e.response.status_code == 404:
                print(f"The agent card was not found at {url}. Try checking if the URL is correct.")
            elif e.response.status_code == 403:
                print(f"Access to the agent card at {url} is forbidden. Check authentication requirements.")
            return None
        except httpx.RequestError as e:
            print(f"Request error accessing agent URL {url}: {str(e)}")
            print(f"This might be due to network issues or the server not being available.")
            return None
        except ValueError as e:
            print(f"JSON parsing error for agent at {url}: {str(e)}")
            print("The response was not valid JSON. Check if the server is returning the proper agent card format.")
            return None
        except Exception as e:
            print(f"Error registering agent from URL {url}: {str(e)}")
            traceback.print_exc()
            return None
    
    def register_agent_from_json(self, json_data: Dict[str, Any]) -> Optional[AgentCard]:
        """Register an agent from JSON data."""
        try:
            # Ensure required fields are present
            if "url" not in json_data:
                print("Missing 'url' field in agent JSON data")
                return None
                
            if "name" not in json_data:
                print("Missing 'name' field in agent JSON data")
                json_data["name"] = f"Agent at {json_data['url']}"
                
            agent = AgentCard(**json_data)
            return self.register_agent(agent)
        except Exception as e:
            print(f"Error registering agent from JSON: {str(e)}")
            traceback.print_exc()
            return None
    
    def _get_agent_id(self, agent: AgentCard) -> str:
        """Generate a unique ID for an agent based on its URL."""
        return agent.url.replace("/", "_").replace(":", "_").replace(".", "_")
    
    def register_agent(self, agent: AgentCard) -> AgentCard:
        """Register a new agent."""
        agent_id = self._get_agent_id(agent)
        self.agents[agent_id] = agent
        print(f"Registered agent: {agent.name} at {agent.url}")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[AgentCard]:
        """List all available agents."""
        return list(self.agents.values())
    
    def select_agent_for_message(self, message: Message) -> Optional[Tuple[str, AgentCard]]:
        """Select the appropriate agent for a message based on content."""
        # Check if the message specifies an agent
        if message.metadata and "agent_id" in message.metadata:
            agent_id = message.metadata["agent_id"]
            agent = self.get_agent(agent_id)
            if agent:
                print(f"Selected agent {agent.name} from metadata")
                return agent_id, agent
            else:
                print(f"Warning: Specified agent_id '{agent_id}' not found")
        
        # Use the host agent for routing if available
        for agent_id, agent in self.agents.items():
            if "host" in agent.name.lower() or any("routing" in skill.id.lower() for skill in agent.skills):
                print(f"Using host agent: {agent.name}")
                return agent_id, agent
        
        # Default to the first agent if no host agent
        if self.agents:
            agent_id, agent = next(iter(self.agents.items()))
            print(f"Using default agent: {agent.name}")
            return agent_id, agent
        
        print("No agents available")
        return None
    
    def process_message(self, message: Message) -> Message:
        """Process a message using the appropriate agent."""
        print(f"\nProcessing message: {message.id}")
        if message.metadata:
            print(f"Message metadata: {message.metadata}")
        
        agent_info = self.select_agent_for_message(message)
        if not agent_info:
            # Create a system message indicating no agent is available
            response = Message(
                role="system",
                conversation_id=message.conversation_id
            )
            response.add_text("No AI agent is available to process your message. Please add an agent first by clicking the 'Add Agent' button in the sidebar.")
            return response
        
        agent_id, agent = agent_info
        
        # Generate response using the selected agent
        try:
            print(f"Sending message to agent: {agent.name} at {agent.url}")
            
            # Create a unique task ID for this message
            task_id = str(uuid.uuid4())
            
            # Create A2A client for this agent
            client = A2AClient(agent_card=agent)
            
            # Prepare message parts
            parts = []
            for part in message.parts:
                if part.type == "text":
                    parts.append({
                        "type": "text",
                        "text": part.content
                    })
                elif part.type == "data":
                    parts.append({
                        "type": "data",
                        "data": part.content
                    })
                elif part.type == "file":
                    parts.append({
                        "type": "file",
                        "file": {
                            "mimeType": part.mime_type,
                            "bytes": part.content
                        }
                    })
            
            # Get or create a session ID from metadata
            session_id = message.metadata.get("session_id", str(uuid.uuid4()))
            
            # Store task information
            self._pending_tasks[task_id] = {
                "message_id": message.id,
                "conversation_id": message.conversation_id,
                "agent_id": agent_id,
                "session_id": session_id
            }
            
            # Send the request using the A2A client
            response_data = client.send_task({
                "role": message.role,
                "parts": parts,
                "metadata": {
                    "conversation_id": message.conversation_id,
                    "message_id": message.id,
                    "task_id": task_id,
                    "session_id": session_id
                }
            }, task_id)
            
            # Parse response
            if "result" in response_data:
                task_result = response_data["result"]
                
                # Create response message
                response_message = Message(
                    role="assistant",
                    conversation_id=message.conversation_id,
                    metadata={
                        "agent_id": agent_id,
                        "task_id": task_id,
                        "session_id": task_result.get("sessionId", session_id)
                    }
                )
                
                # Check for artifacts format (A2A protocol v2)
                if "artifacts" in task_result and isinstance(task_result["artifacts"], list):
                    try:
                        for artifact in task_result["artifacts"]:
                            if "parts" in artifact and isinstance(artifact["parts"], list):
                                for part in artifact["parts"]:
                                    if part.get("type") == "text" and "text" in part:
                                        response_message.add_text(part["text"])
                                    elif part.get("type") == "data":
                                        response_message.add_data(part.get("data", {}))
                                    elif part.get("type") == "file" and "file" in part:
                                        file_data = part["file"]
                                        response_message.add_file(
                                            file=file_data.get("bytes", ""),
                                            mime_type=file_data.get("mimeType", "application/octet-stream")
                                        )
                    except Exception as e:
                        print(f"Error parsing artifacts: {str(e)}")
                        # If we fail to properly parse artifacts, return the raw JSON
                        response_message.add_text(json.dumps(task_result))
                
                # Original format - Extract content from the task status
                elif "status" in task_result and "message" in task_result["status"]:
                    agent_message = task_result["status"]["message"]
                    
                    if "parts" in agent_message:
                        for part in agent_message["parts"]:
                            if part.get("type") == "text":
                                response_message.add_text(part.get("text", ""))
                            elif part.get("type") == "data":
                                response_message.add_data(part.get("data", {}))
                            elif part.get("type") == "file" and "file" in part:
                                file_data = part["file"]
                                response_message.add_file(
                                    file=file_data.get("bytes", ""),
                                    mime_type=file_data.get("mimeType", "application/octet-stream")
                                )
                else:
                    # Fallback if we can't find the message in the expected structure
                    # Check if it looks like an A2A protocol response
                    if ("artifacts" in task_result or "sessionId" in task_result) and task_result.get("status", {}).get("state") in ["completed", "failed"]:
                        # It's likely an A2A protocol response, keep it intact
                        response_message = Message(
                            role="assistant",
                            conversation_id=message.conversation_id,
                            metadata={
                                "agent_id": agent_id,
                                "task_id": task_id,
                                "session_id": task_result.get("sessionId", session_id),
                                "is_a2a_raw_response": True
                            }
                        )
                        response_message.content = task_result
                    else:
                        # Just pass the raw JSON to the client for processing
                        response_message.add_text(json.dumps(task_result))
                
                return response_message
            else:
                # Handle error
                error_message = Message(
                    role="system",
                    conversation_id=message.conversation_id
                )
                error_text = response_data.get('error', {})
                if isinstance(error_text, dict):
                    error_text = json.dumps(error_text)
                error_message.add_text(f"Error from agent: {error_text}")
                return error_message
            
        except (A2AClientHTTPError, A2AClientJSONError) as e:
            print(f"A2A client error: {str(e)}")
            traceback.print_exc()
            
            # Handle client errors by returning a system message
            response = Message(
                role="system",
                conversation_id=message.conversation_id
            )
            error_msg = f"""Error communicating with agent: {str(e)}

Please make sure the agent server is running and accessible.

To fix this issue:
1. Check that the agent URL is correct and formatted properly (no double slashes)
2. Ensure the agent server supports the A2A protocol
3. Check agent server logs for more details
4. Try adding a different agent

You can add an agent by clicking "Add Agent" in the sidebar.
"""
            response.add_text(error_msg)
            return response
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            traceback.print_exc()
            
            # Handle general errors by returning a system message
            response = Message(
                role="system",
                conversation_id=message.conversation_id
            )
            error_msg = f"""Error processing message: {str(e)}

Please make sure the agent server is running and accessible.

To fix this issue:
1. Check that the agent URL is correct and the server is running
2. Ensure your network connection is stable
3. Try adding a different agent

You can add an agent by clicking "Add Agent" in the sidebar.
"""
            response.add_text(error_msg)
            return response 