// DOM Elements
const newConversationBtn = document.getElementById('newConversationBtn');
const conversationsList = document.getElementById('conversationsList');
const messagesContainer = document.getElementById('messagesContainer');
const messageInput = document.getElementById('messageInput');
const sendMessageBtn = document.getElementById('sendMessageBtn');
const welcomeMessage = document.getElementById('welcomeMessage');
const currentConversationTitle = document.getElementById('currentConversationTitle');
const currentAgentBadge = document.getElementById('currentAgentBadge');
const agentSelector = document.getElementById('agentSelector');
const agentSelectionDropdown = document.getElementById('agentSelectionDropdown');
const saveAgentBtn = document.getElementById('saveAgentBtn');
const approveAgentBtn = document.getElementById('approveAgentBtn');
const denyAgentBtn = document.getElementById('denyAgentBtn');

// State
let currentConversation = null;
let conversations = [];
let agents = [];
let socket = null;
let pendingAgentData = null;

// Initialize app
document.addEventListener('DOMContentLoaded', initialize);

async function initialize() {
    // Load conversations
    await loadConversations();
    
    // Load agents
    await loadAgents();
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Event listeners
    setupEventListeners();
}

// API calls
async function loadConversations() {
    try {
        const response = await fetch('/api/conversations');
        conversations = await response.json();
        renderConversations();
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

async function loadAgents() {
    try {
        const response = await fetch('/api/agents');
        agents = await response.json();
        renderAgents();
    } catch (error) {
        console.error('Error loading agents:', error);
    }
}

async function createConversation() {
    try {
        const response = await fetch('/api/conversations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const newConversation = await response.json();
        conversations.push(newConversation);
        renderConversations();
        selectConversation(newConversation.id);
    } catch (error) {
        console.error('Error creating conversation:', error);
    }
}

async function loadMessages(conversationId) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}/messages`);
        const messages = await response.json();
        renderMessages(messages);
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

async function sendMessage(conversationId, content) {
    try {
        const selectedAgentId = agentSelector.value;
        
        // Check if an agent is selected
        if (!selectedAgentId) {
            alert("Please select an agent before sending a message.");
            return;
        }
        
        console.log(`Sending message to ${conversationId} using agent ${selectedAgentId}`);
        
        const messageData = {
            content: content,
            metadata: {
                agent_id: selectedAgentId
            }
        };
        
        // Add user message immediately to UI
        addMessageToUI({
            id: Date.now().toString(),
            role: 'user',
            parts: [{ type: 'text', content: content, mime_type: 'text/plain' }],
            created_at: Date.now() / 1000,
            conversation_id: conversationId
        });
        
        // Add typing indicator
        addTypingIndicator();
        
        // Send the message to the server
        const response = await fetch(`/api/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(messageData)
        });
        
        // Check if the response is ok
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Failed to send message');
        }
        
        // Response will come through WebSocket
    } catch (error) {
        console.error('Error sending message:', error);
        // Remove typing indicator
        removeTypingIndicator();
        
        // Show error message in chat
        addMessageToUI({
            id: Date.now().toString(),
            role: 'system',
            parts: [{ type: 'text', content: `Error: ${error.message}`, mime_type: 'text/plain' }],
            created_at: Date.now() / 1000,
            conversation_id: conversationId
        });
    }
}

async function registerAgent(agentData) {
    try {
        const response = await fetch('/api/agents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(agentData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Failed to register agent');
        }
        
        const newAgent = await response.json();
        agents.push(newAgent);
        renderAgents();
        
        // Show success message
        alert(`Agent "${newAgent.name}" was successfully added!`);
    } catch (error) {
        console.error('Error registering agent:', error);
        alert(`Error registering agent: ${error.message}`);
    }
}

// Rendering functions
function renderConversations() {
    conversationsList.innerHTML = '';
    conversations.forEach(conversation => {
        const conversationElement = document.createElement('div');
        conversationElement.className = 'conversation-item';
        conversationElement.dataset.id = conversation.id;
        if (currentConversation && conversation.id === currentConversation) {
            conversationElement.classList.add('active');
        }
        conversationElement.textContent = conversation.name || `Conversation ${conversation.id.substring(0, 8)}`;
        conversationElement.addEventListener('click', () => selectConversation(conversation.id));
        conversationsList.appendChild(conversationElement);
    });
}

function renderAgents() {
    // Clear agent dropdowns
    agentSelector.innerHTML = '<option value="">Select an agent</option>';
    
    // Add agents to available agents dropdown
    const agentDropdownItems = agentSelectionDropdown.querySelectorAll('.agent-item');
    agentDropdownItems.forEach(item => item.remove());
    
    const customAgentItem = agentSelectionDropdown.querySelector('a[data-bs-target="#addAgentModal"]').parentNode;
    
    agents.forEach(agent => {
        // Add to agent selector in chat
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        agentSelector.appendChild(option);
        
        // Add to dropdown menu
        const li = document.createElement('li');
        li.className = 'agent-item';
        const a = document.createElement('a');
        a.className = 'dropdown-item';
        a.href = '#';
        a.textContent = agent.name;
        a.dataset.id = agent.id;
        a.addEventListener('click', () => selectAgent(agent.id));
        li.appendChild(a);
        agentSelectionDropdown.insertBefore(li, customAgentItem);
    });
}

function renderMessages(messages) {
    messagesContainer.innerHTML = ''; // Clear messages container
    welcomeMessage.classList.add('d-none');
    
    if (messages.length === 0) {
        // Show welcome message for new conversation
        const emptyStateMessage = document.createElement('div');
        emptyStateMessage.className = 'text-center my-5';
        emptyStateMessage.innerHTML = `
            <p class="text-muted">This is the beginning of your conversation.</p>
            <p class="text-muted">Type a message to get started!</p>
        `;
        messagesContainer.appendChild(emptyStateMessage);
        
        // Make sure chat input is visible for empty conversations
        document.getElementById('chatInputContainer').classList.remove('d-none');
        return;
    }
    
    messages.forEach(message => {
        addMessageToUI(message);
    });
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addMessageToUI(message) {
    const messageElement = document.createElement('div');
    messageElement.className = `message ${message.role}`;
    messageElement.dataset.id = message.id;
    
    // Check if the message is a raw JSON response string
    if (typeof message === 'string') {
        try {
            // Try to parse it as JSON
            const parsedMessage = JSON.parse(message);
            if (parsedMessage.artifacts && Array.isArray(parsedMessage.artifacts)) {
                // Handle A2A protocol format
                let content = '';
                parsedMessage.artifacts.forEach(artifact => {
                    if (artifact.parts && Array.isArray(artifact.parts)) {
                        artifact.parts.forEach(part => {
                            if (part.type === 'text') {
                                content += part.text;
                            } else if (part.text) {
                                content += part.text;
                            }
                        });
                    }
                });
                
                if (content) {
                    messageElement.textContent = content;
                } else {
                    // Fallback: just show formatted JSON
                    messageElement.innerHTML = `<pre class="text-wrap">${JSON.stringify(parsedMessage, null, 2)}</pre>`;
                }
                
                // Add to the UI
                messagesContainer.appendChild(messageElement);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                return;
            }
        } catch (e) {
            // Not JSON, continue with normal processing
            console.log('Not a valid JSON string:', e);
        }
    }
    
    // Handle A2A protocol format directly
    if (message.artifacts && Array.isArray(message.artifacts)) {
        let messageContent = '';
        message.artifacts.forEach(artifact => {
            if (artifact.parts && Array.isArray(artifact.parts)) {
                artifact.parts.forEach(part => {
                    if (part.type === 'text') {
                        messageContent += part.text;
                    } else if (part.text) {
                        messageContent += part.text;
                    }
                });
            }
        });
        
        if (messageContent) {
            messageElement.innerHTML = messageContent;
            
            // Add timestamp
            if (message.status && message.status.timestamp) {
                const timestampElement = document.createElement('div');
                timestampElement.className = 'message-time';
                const date = new Date(message.status.timestamp);
                timestampElement.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                messageElement.appendChild(timestampElement);
            }
            
            messagesContainer.appendChild(messageElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            return;
        }
    }
    
    // Standard message format processing
    let messageContent = '';
    
    // Handle message.parts if it exists
    if (message.parts && Array.isArray(message.parts)) {
        message.parts.forEach(part => {
            if (part.type === 'text') {
                messageContent += part.content || part.text || '';
            } else if (part.type === 'data') {
                messageContent += `<pre class="text-wrap">${JSON.stringify(part.content, null, 2)}</pre>`;
            } else if (part.type === 'file' && part.mime_type && part.mime_type.startsWith('image/')) {
                messageContent += `<img src="data:${part.mime_type};base64,${part.content}" class="img-fluid" />`;
            }
        });
    } else {
        // Fallback for simple content
        messageContent = message.content || JSON.stringify(message, null, 2);
    }
    
    messageElement.innerHTML = messageContent;
    
    // Add timestamp
    const timestampElement = document.createElement('div');
    timestampElement.className = 'message-time';
    const date = new Date(message.created_at * 1000 || Date.now());
    timestampElement.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    messageElement.appendChild(timestampElement);
    
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addTypingIndicator() {
    // Remove any existing typing indicator
    removeTypingIndicator();
    
    const typingElement = document.createElement('div');
    typingElement.className = 'message assistant typing-indicator-container';
    typingElement.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    messagesContainer.appendChild(typingElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = messagesContainer.querySelector('.typing-indicator-container');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Event handlers
function selectConversation(conversationId) {
    currentConversation = conversationId;
    
    // Update UI
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id === conversationId);
    });
    
    const conversation = conversations.find(c => c.id === conversationId);
    if (conversation) {
        currentConversationTitle.textContent = conversation.name || `Conversation ${conversation.id.substring(0, 8)}`;
    }
    
    // Show chat input container
    document.getElementById('chatInputContainer').classList.remove('d-none');
    
    // Enable input and send button
    messageInput.disabled = false;
    sendMessageBtn.disabled = false;
    agentSelector.disabled = false;
    
    // Load messages
    loadMessages(conversationId);
    
    // Join WebSocket room
    if (socket) {
        socket.emit('join', { conversation_id: conversationId });
    }
}

function selectAgent(agentId) {
    agentSelector.value = agentId;
    const agent = agents.find(a => a.id === agentId);
    if (agent) {
        currentAgentBadge.textContent = `Agent: ${agent.name}`;
        currentAgentBadge.classList.remove('d-none');
    }
}

function handleSendMessage() {
    const content = messageInput.value.trim();
    if (!content || !currentConversation) return;
    
    sendMessage(currentConversation, content);
    messageInput.value = '';
}

function handleAddAgent() {
    const activeTab = document.querySelector('.nav-link.active').id;
    
    if (activeTab === 'url-tab') {
        // Add agent by URL
        const agentUrl = document.getElementById('agentUrl').value.trim();
        
        if (!agentUrl) {
            alert('Agent URL is required');
            return;
        }
        
        // Fetch agent data to preview it
        fetchAgentDataForPreview(agentUrl);
    } else {
        // Add agent by JSON
        try {
            const agentJsonText = document.getElementById('agentJson').value.trim();
            
            if (!agentJsonText) {
                alert('Agent JSON data is required');
                return;
            }
            
            const agentData = JSON.parse(agentJsonText);
            
            if (!agentData.url) {
                alert('The agent JSON must include a "url" field');
                return;
            }
            
            // Show preview
            showAgentPreview(agentData);
        } catch (error) {
            alert(`Invalid JSON: ${error.message}`);
            return;
        }
    }
}

async function fetchAgentDataForPreview(url) {
    try {
        // Show loading in the add agent modal
        document.getElementById('agentUrl').disabled = true;
        saveAgentBtn.disabled = true;
        saveAgentBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        
        // Show connection test results for better feedback
        const connectionResults = document.getElementById('connectionTestResults');
        const connectionStatus = document.getElementById('connectionStatus');
        const diagnosticSteps = document.getElementById('diagnosticSteps');
        
        connectionResults.classList.remove('d-none');
        connectionStatus.className = 'alert alert-info';
        connectionStatus.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Testing connection...';
        diagnosticSteps.innerHTML = '<div class="mb-2"><i class="fas fa-info-circle text-info me-1"></i> The system will automatically try these URLs in order:</div>' +
            `<div class="ms-3 mb-1">1. ${url}/.well-known/agent.json (A2A standard location)</div>` +
            `<div class="ms-3 mb-1">2. ${url} (Direct URL)</div>`;
        
        // Use the backend API to fetch agent data (this avoids CORS issues)
        const response = await fetch('/api/debug/test-agent-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        
        // Reset the form state
        document.getElementById('agentUrl').disabled = false;
        saveAgentBtn.disabled = false;
        saveAgentBtn.innerHTML = 'Add Agent';
        
        // Update the connection status based on the result
        if (data.success) {
            connectionStatus.className = 'alert alert-success';
            connectionStatus.innerHTML = `<i class="fas fa-check-circle me-2"></i> Connection successful! Found agent: <strong>${data.agent_data.name}</strong>`;
            
            // Update diagnosticSteps with the detailed steps from the server
            if (data.steps && data.steps.length > 0) {
                diagnosticSteps.innerHTML = '';
                data.steps.forEach(step => {
                    const statusIcon = getStatusIcon(step.status);
                    diagnosticSteps.innerHTML += `<div class="mb-2">
                        <span class="fw-bold">${step.step}:</span> ${statusIcon} ${step.message}
                    </div>`;
                });
            }
            
            // Close the add agent modal after a brief delay to show success
            setTimeout(() => {
                const addAgentModal = bootstrap.Modal.getInstance(document.getElementById('addAgentModal'));
                addAgentModal.hide();
                
                // Show agent preview
                showAgentPreview(data.agent_data);
            }, 1000);
        } else {
            throw new Error(data.error || 'Failed to fetch agent data');
        }
    } catch (error) {
        console.error('Error fetching agent data:', error);
        
        // Reset the form state
        document.getElementById('agentUrl').disabled = false;
        saveAgentBtn.disabled = false;
        saveAgentBtn.innerHTML = 'Add Agent';
        
        // Update connection status to show error
        const connectionResults = document.getElementById('connectionTestResults');
        const connectionStatus = document.getElementById('connectionStatus');
        
        connectionResults.classList.remove('d-none');
        connectionStatus.className = 'alert alert-danger';
        connectionStatus.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> Connection failed: ${error.message}`;
        
        // Show detailed error message
        let errorMessage = `Error fetching agent data: ${error.message}`;
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage += '\n\nPossible reasons:\n- The agent server is not running\n- The URL is incorrect\n- Network connectivity issues\n\nTry checking if the agent server is accessible.';
        }
        
        // Don't alert, let the UI show the error
        // alert(errorMessage);
    }
}

function showAgentPreview(agentData) {
    // Store agent data for later use
    pendingAgentData = agentData;
    
    // Populate the preview card
    document.getElementById('previewAgentName').textContent = agentData.name || 'Unnamed Agent';
    document.getElementById('previewAgentDescription').textContent = agentData.description || 'No description provided';
    document.getElementById('previewAgentUrl').textContent = agentData.url;
    document.getElementById('previewAgentVersion').textContent = agentData.version || '1.0.0';
    
    // Display capabilities
    const capabilitiesList = document.getElementById('previewAgentCapabilities');
    capabilitiesList.innerHTML = '';
    
    if (agentData.capabilities) {
        for (const [key, value] of Object.entries(agentData.capabilities)) {
            const li = document.createElement('li');
            const badge = document.createElement('span');
            badge.className = `badge ${value ? 'bg-success' : 'bg-secondary'} me-2`;
            badge.textContent = value ? 'Yes' : 'No';
            li.appendChild(badge);
            li.appendChild(document.createTextNode(key.charAt(0).toUpperCase() + key.slice(1)));
            capabilitiesList.appendChild(li);
        }
    }
    
    // Display skills
    const skillsContainer = document.getElementById('previewAgentSkills');
    skillsContainer.innerHTML = '';
    
    if (agentData.skills && agentData.skills.length > 0) {
        agentData.skills.forEach(skill => {
            const skillCard = document.createElement('div');
            skillCard.className = 'card mb-2';
            
            const skillBody = document.createElement('div');
            skillBody.className = 'card-body py-2';
            
            const skillTitle = document.createElement('h6');
            skillTitle.className = 'card-title mb-1';
            skillTitle.textContent = skill.name;
            
            const skillDesc = document.createElement('p');
            skillDesc.className = 'card-text small mb-1';
            skillDesc.textContent = skill.description || 'No description';
            
            if (skill.tags && skill.tags.length > 0) {
                const tagsDiv = document.createElement('div');
                tagsDiv.className = 'mt-1';
                
                skill.tags.forEach(tag => {
                    const tagBadge = document.createElement('span');
                    tagBadge.className = 'badge bg-info me-1';
                    tagBadge.textContent = tag;
                    tagsDiv.appendChild(tagBadge);
                });
                
                skillBody.appendChild(skillTitle);
                skillBody.appendChild(skillDesc);
                skillBody.appendChild(tagsDiv);
            } else {
                skillBody.appendChild(skillTitle);
                skillBody.appendChild(skillDesc);
            }
            
            skillCard.appendChild(skillBody);
            skillsContainer.appendChild(skillCard);
        });
    } else {
        const noSkills = document.createElement('p');
        noSkills.className = 'text-muted';
        noSkills.textContent = 'No skills declared';
        skillsContainer.appendChild(noSkills);
    }
    
    // Show the preview modal
    const previewModal = new bootstrap.Modal(document.getElementById('agentPreviewModal'));
    previewModal.show();
}

function handleApproveAgent() {
    if (pendingAgentData) {
        // Close the preview modal
        const previewModal = bootstrap.Modal.getInstance(document.getElementById('agentPreviewModal'));
        previewModal.hide();
        
        // Register the agent
        registerAgent(pendingAgentData);
        
        // Clear pending data
        pendingAgentData = null;
        
        // Clear forms
        document.getElementById('addAgentUrlForm').reset();
        document.getElementById('addAgentJsonForm').reset();
    }
}

function handleDenyAgent() {
    // Close the preview modal
    const previewModal = bootstrap.Modal.getInstance(document.getElementById('agentPreviewModal'));
    previewModal.hide();
    
    // Clear pending data
    pendingAgentData = null;
    
    // Clear forms
    document.getElementById('addAgentUrlForm').reset();
    document.getElementById('addAgentJsonForm').reset();
}

function connectWebSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to WebSocket');
    });
    
    socket.on('message', (message) => {
        // Remove typing indicator
        removeTypingIndicator();
        
        console.log('Received message:', message);
        
        // Check if message is a string (raw JSON)
        if (typeof message === 'string') {
            try {
                // Try parsing as JSON
                const parsedMessage = JSON.parse(message);
                // Handle it as a message with the parsed object
                addMessageToUI(parsedMessage);
            } catch (e) {
                // If not valid JSON, just display as text
                addMessageToUI({
                    id: Date.now().toString(),
                    role: 'assistant',
                    parts: [{ type: 'text', content: message }],
                    created_at: Date.now() / 1000
                });
            }
        } else {
            // Add received message
            addMessageToUI(message);
        }
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket');
    });
}

async function testAgentConnection() {
    const agentUrl = document.getElementById('agentUrl').value.trim();
    const connectionResults = document.getElementById('connectionTestResults');
    const connectionStatus = document.getElementById('connectionStatus');
    const diagnosticSteps = document.getElementById('diagnosticSteps');
    
    if (!agentUrl) {
        alert('Please enter an agent URL to test');
        return;
    }
    
    // Show and reset results container
    connectionResults.classList.remove('d-none');
    connectionStatus.className = 'alert alert-info';
    connectionStatus.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Testing connection...';
    diagnosticSteps.innerHTML = '';
    
    try {
        // Make the request to the debug endpoint
        const response = await fetch('/api/debug/test-agent-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: agentUrl })
        });
        
        const data = await response.json();
        
        // Display the results
        if (data.success) {
            connectionStatus.className = 'alert alert-success';
            connectionStatus.innerHTML = `<i class="fas fa-check-circle me-2"></i> Connection successful! Found agent: <strong>${data.agent_data.name}</strong>`;
        } else {
            connectionStatus.className = 'alert alert-danger';
            connectionStatus.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> Connection failed: ${data.error}`;
        }
        
        // Display diagnostic steps
        if (data.steps && data.steps.length > 0) {
            const stepsHtml = data.steps.map(step => {
                const statusIcon = getStatusIcon(step.status);
                return `<div class="mb-2">
                    <span class="fw-bold">${step.step}:</span> ${statusIcon} ${step.message}
                </div>`;
            }).join('');
            
            diagnosticSteps.innerHTML = `
                <h6 class="mt-3 mb-2">Diagnostic Details:</h6>
                ${stepsHtml}
            `;
        }
    } catch (error) {
        connectionStatus.className = 'alert alert-danger';
        connectionStatus.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i> Error running connection test: ${error.message}`;
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'Success':
            return '<i class="fas fa-check-circle text-success me-1"></i>';
        case 'Failed':
            return '<i class="fas fa-times-circle text-danger me-1"></i>';
        case 'Warning':
            return '<i class="fas fa-exclamation-triangle text-warning me-1"></i>';
        case 'Modified':
            return '<i class="fas fa-edit text-info me-1"></i>';
        case 'Valid':
            return '<i class="fas fa-check text-success me-1"></i>';
        default:
            return '<i class="fas fa-info-circle text-secondary me-1"></i>';
    }
}

async function directAddAgent() {
    const agentUrl = document.getElementById('agentUrl').value.trim();
    
    if (!agentUrl) {
        alert('Agent URL is required');
        return;
    }
    
    try {
        // Show loading indicator
        const directAddBtn = document.getElementById('directAddAgentBtn');
        const originalBtnText = directAddBtn.innerHTML;
        directAddBtn.disabled = true;
        directAddBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Adding...';
        
        // Call the backend endpoint to register the agent directly
        const response = await fetch('/api/agents/register-from-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: agentUrl })
        });
        
        const data = await response.json();
        
        // Reset button state
        directAddBtn.disabled = false;
        directAddBtn.innerHTML = originalBtnText;
        
        if (data.success) {
            // Close the modal
            const addAgentModal = bootstrap.Modal.getInstance(document.getElementById('addAgentModal'));
            addAgentModal.hide();
            
            // Add the agent to the list and render
            agents.push(data.agent);
            renderAgents();
            
            // Show success message
            alert(`Agent "${data.agent.name}" was successfully added via backend!`);
            
            // Clear form
            document.getElementById('addAgentUrlForm').reset();
        } else {
            alert(`Failed to add agent: ${data.message}`);
        }
    } catch (error) {
        console.error('Error registering agent:', error);
        
        // Reset button
        const directAddBtn = document.getElementById('directAddAgentBtn');
        directAddBtn.disabled = false;
        directAddBtn.innerHTML = '<i class="fas fa-server me-1"></i> Add directly via backend';
        
        // Show error
        alert(`Error registering agent: ${error.message}`);
    }
}

function setupEventListeners() {
    // New conversation button
    newConversationBtn.addEventListener('click', createConversation);
    
    // Send message button
    sendMessageBtn.addEventListener('click', handleSendMessage);
    
    // Input keypress (Enter to send)
    messageInput.addEventListener('keypress', event => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSendMessage();
        }
    });
    
    // Save agent button
    saveAgentBtn.addEventListener('click', handleAddAgent);
    
    // Test connection button
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', testAgentConnection);
    }
    
    // Direct add agent button
    const directAddAgentBtn = document.getElementById('directAddAgentBtn');
    if (directAddAgentBtn) {
        directAddAgentBtn.addEventListener('click', directAddAgent);
    }
    
    // Approve agent button
    approveAgentBtn.addEventListener('click', handleApproveAgent);
    
    // Deny agent button
    denyAgentBtn.addEventListener('click', handleDenyAgent);
} 