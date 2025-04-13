import os
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, join_room
from dotenv import load_dotenv
from services.agent_manager import AgentManager
from services.conversation_manager import ConversationManager

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize managers
agent_manager = AgentManager()
conversation_manager = ConversationManager()

# Enable CORS for all routes
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.route('/')
def index():
    return render_template('index.html', agents=agent_manager.list_agents())

@app.route('/api/conversations', methods=['GET', 'POST'])
def conversations():
    if request.method == 'POST':
        # Create a new conversation
        conversation = conversation_manager.create_conversation()
        return jsonify(conversation.model_dump())
    else:
        # List all conversations
        return jsonify([conv.model_dump() for conv in conversation_manager.list_conversations()])

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET', 'POST'])
def messages(conversation_id):
    if request.method == 'POST':
        try:
            # Send a new message
            message_data = request.json
            message = conversation_manager.create_message(
                conversation_id=conversation_id,
                role="user",
                content=message_data.get('content', '')
            )
            
            # Set agent_id in metadata if provided
            if message_data.get('metadata', {}).get('agent_id'):
                message.metadata['agent_id'] = message_data['metadata']['agent_id']
            
            # Add the user message to the conversation first
            conversation_manager.add_message_to_conversation(message)
            
            # Process message with the appropriate agent
            response = agent_manager.process_message(message)
            
            # Add the response to the conversation
            conversation_manager.add_message_to_conversation(response)
            
            # Emit the response via WebSocket
            socketio.emit('message', response.model_dump(), room=conversation_id)
            
            return jsonify(response.model_dump())
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": str(e),
                "message": f"Failed to process message: {str(e)}"
            }), 500
    else:
        # List all messages in a conversation
        return jsonify([msg.model_dump() for msg in conversation_manager.list_messages(conversation_id)])

@app.route('/api/agents', methods=['GET', 'POST'])
def agents():
    if request.method == 'POST':
        try:
            # Add an agent
            agent_data = request.json
            
            # Method 1: Register by URL
            if 'url' in agent_data and isinstance(agent_data['url'], str) and len(agent_data) == 1:
                agent = agent_manager.register_agent_from_url(agent_data['url'])
                if agent:
                    return jsonify(agent.model_dump())
                else:
                    return jsonify({
                        "error": "Failed to register agent",
                        "message": "Could not fetch agent card from the provided URL. Please ensure the URL is correct and the server is running."
                    }), 400
            
            # Method 2: Register with direct JSON data
            elif 'url' in agent_data and len(agent_data) > 1:
                agent = agent_manager.register_agent_from_json(agent_data)
                if agent:
                    return jsonify(agent.model_dump())
                else:
                    return jsonify({
                        "error": "Failed to register agent",
                        "message": "Invalid agent card data. Please ensure all required fields are present and correctly formatted."
                    }), 400
            else:
                return jsonify({
                    "error": "Invalid agent data",
                    "message": "URL is required for registering an agent. Please provide a valid URL."
                }), 400
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": str(e),
                "message": f"Failed to register agent: {str(e)}. Please check the server logs for more details."
            }), 500
    else:
        # List all available agents
        return jsonify([agent.model_dump() for agent in agent_manager.list_agents()])

@app.route('/api/agents/register-from-url', methods=['POST'])
def register_agent_from_url():
    """
    Register an agent directly from a URL via the backend.
    This route helps avoid CORS issues when fetching agent data.
    """
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({
                "success": False,
                "error": "Missing URL parameter",
                "message": "Please provide a URL to register"
            }), 400
        
        # Use the agent manager to register from URL
        agent = agent_manager.register_agent_from_url(url)
        
        if agent:
            return jsonify({
                "success": True,
                "agent": agent.model_dump(),
                "message": f"Successfully registered agent: {agent.name}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to register agent",
                "message": "Could not fetch or validate agent card from the provided URL"
            }), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

@app.route('/api/debug/test-agent-connection', methods=['POST'])
def test_agent_connection():
    """Debug endpoint to test connectivity to an agent URL."""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({
                "success": False,
                "error": "Missing URL parameter",
                "message": "Please provide a URL to test"
            }), 400
            
        import httpx
        import traceback
        
        diagnostic_info = {
            "url": url,
            "steps": [],
            "success": False,
            "error": None,
            "agent_data": None
        }
        
        # Step 1: Validate URL format
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            diagnostic_info["steps"].append({
                "step": "URL Formatting",
                "status": "Modified",
                "message": f"Added http:// prefix: {url}"
            })
        else:
            diagnostic_info["steps"].append({
                "step": "URL Formatting",
                "status": "Valid",
                "message": "URL has valid protocol prefix"
            })
        
        # Step 2: Remove trailing slashes
        original_url = url
        url = url.rstrip('/')
        if original_url != url:
            diagnostic_info["steps"].append({
                "step": "URL Cleaning",
                "status": "Modified",
                "message": f"Removed trailing slashes: {url}"
            })
        else:
            diagnostic_info["steps"].append({
                "step": "URL Cleaning",
                "status": "Valid",
                "message": "URL had no trailing slashes"
            })
        
        # Step 3: Determine URL paths to try
        urls_to_try = []
        
        # Check if URL already ends with agent.json
        if url.endswith('agent.json'):
            urls_to_try.append((url, "Direct agent.json URL"))
        else:
            # Try well-known path first, then base URL
            urls_to_try.append((f"{url}/.well-known/agent.json", "Well-known path"))
            urls_to_try.append((url, "Base URL"))
            
        diagnostic_info["steps"].append({
            "step": "URL Resolution",
            "status": "Info",
            "message": f"Will try {len(urls_to_try)} URL variations"
        })
        
        # Step 4: Try each URL
        agent_data = None
        success = False
        
        for test_url, description in urls_to_try:
            try:
                response = httpx.get(test_url, timeout=10.0)
                status_code = response.status_code
                reason = response.reason_phrase
                
                diagnostic_info["steps"].append({
                    "step": f"Connection Attempt ({description})",
                    "status": "Success" if response.is_success else "Failed",
                    "message": f"HTTP {status_code} {reason}",
                    "details": {
                        "url": test_url,
                        "status_code": status_code,
                        "reason": reason
                    }
                })
                
                if response.is_success:
                    try:
                        # Parse JSON
                        data = response.json()
                        
                        # Check required fields
                        if "name" in data:
                            agent_data = data
                            success = True
                            diagnostic_info["steps"].append({
                                "step": "Agent Validation",
                                "status": "Success",
                                "message": f"Found valid agent: {data.get('name')}"
                            })
                            
                            # Add URL field if missing
                            if "url" not in agent_data:
                                # Use the base URL, not the agent.json URL
                                base_url = url
                                agent_data["url"] = base_url
                                diagnostic_info["steps"].append({
                                    "step": "URL Field",
                                    "status": "Modified",
                                    "message": f"Added missing URL field: {base_url}"
                                })
                            
                            # Break the loop - we found a valid agent
                            break
                        else:
                            diagnostic_info["steps"].append({
                                "step": "Agent Validation",
                                "status": "Failed",
                                "message": "Response missing required 'name' field"
                            })
                    except ValueError:
                        diagnostic_info["steps"].append({
                            "step": "JSON Parsing",
                            "status": "Failed",
                            "message": "Response is not valid JSON"
                        })
            except httpx.TimeoutError:
                diagnostic_info["steps"].append({
                    "step": f"Connection Attempt ({description})",
                    "status": "Failed",
                    "message": "Connection timed out after 10 seconds"
                })
            except httpx.RequestError as e:
                diagnostic_info["steps"].append({
                    "step": f"Connection Attempt ({description})",
                    "status": "Failed",
                    "message": f"Request error: {str(e)}"
                })
        
        # Final result
        if success:
            diagnostic_info["success"] = True
            diagnostic_info["agent_data"] = agent_data
            return jsonify(diagnostic_info), 200
        else:
            diagnostic_info["error"] = "Could not find a valid agent at any of the tried URLs"
            return jsonify(diagnostic_info), 400
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "An unexpected error occurred during connection test"
        }), 500

@socketio.on('join')
def on_join(data):
    # Join a conversation room
    room = data.get('conversation_id')
    if room:
        join_room(room)

@socketio.on('connect')
def on_connect():
    print("Client connected")

@socketio.on('disconnect')
def on_disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    print("Starting AI Chat Application with A2A Protocol Support")
    print(f"Number of agents available: {len(agent_manager.list_agents())}")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 