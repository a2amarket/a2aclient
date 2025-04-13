# AI Chat Application

A Flask-based chat application that allows users to communicate with AI agents, similar to the demo UI in the A2A project.

## Features

- Chat with AI agents powered by Google's Gemini models
- Create multiple conversations
- Add custom AI agents
- Modern, responsive UI
- Real-time updates via WebSockets

## Setup Instructions

### Prerequisites

- Python 3.8+
- Google API Key for Gemini models

### Installation

1. Clone this repository
2. Navigate to the project directory
3. Create a virtual environment:
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Application

1. Make sure your virtual environment is activated
2. Start the application:
   ```
   python app.py
   ```
3. Open your browser and navigate to `http://localhost:5000`

## Using the Application

### Creating a Conversation

Click the "New Chat" button in the sidebar to create a new conversation.

### Sending Messages

1. Select a conversation from the sidebar
2. Choose an AI agent from the dropdown menu
3. Type your message in the input field
4. Press Enter or click the send button

### Adding a Custom Agent

1. Click "Add Agent" in the sidebar
2. Choose "Custom Agent..." from the dropdown
3. Fill in the agent details:
   - Agent ID: A unique identifier
   - Agent Name: Display name
   - Description: (Optional)
   - Model Name: The name of the model (e.g., "gemini-pro")
   - Capabilities: Comma-separated list of capabilities

## Architecture

- Flask web server
- Flask-SocketIO for real-time communication
- Google Generative AI Python SDK for model interaction
- Bootstrap 5 for responsive design