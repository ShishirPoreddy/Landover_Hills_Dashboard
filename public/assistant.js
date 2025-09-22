/**
 * Municipal Budget Assistant Widget
 * 
 * A floating chat widget that allows users to ask questions about municipal budgets.
 * Posts to the /ask endpoint and displays answers with evidence and citations.
 * 
 * Usage:
 * 1. Include this script in your HTML page
 * 2. Call BudgetAssistant.init() to initialize the widget
 * 3. Optionally customize the API URL and styling
 */

class BudgetAssistant {
    constructor(options = {}) {
        this.apiUrl = options.apiUrl || 'http://localhost:8000';
        this.isOpen = false;
        this.isLoading = false;
        this.conversation = [];
        this.isMinimized = false;
        this.persistentMode = options.persistentMode !== false; // Default to true
        
        this.init();
    }
    
    init() {
        this.createWidget();
        this.attachEventListeners();
        this.loadStyles();
    }
    
    createWidget() {
        // Create the main widget container
        this.widget = document.createElement('div');
        this.widget.id = 'budget-assistant-widget';
        this.widget.innerHTML = `
            <div class="budget-assistant-container">
                <!-- Minimized State -->
                <div class="budget-assistant-minimized" id="budget-assistant-minimized">
                    <button class="budget-assistant-minimize-toggle" id="budget-assistant-minimize-toggle">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                        <span class="budget-assistant-minimize-label">Budget Assistant</span>
                        <div class="budget-assistant-notification-dot" id="budget-assistant-notification-dot" style="display: none;"></div>
                    </button>
                </div>
                
                <!-- Chat Button (Full State) -->
                <button class="budget-assistant-toggle" id="budget-assistant-toggle">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span class="budget-assistant-label">Ask the Budget</span>
                    <div class="budget-assistant-notification-dot" id="budget-assistant-notification-dot-full" style="display: none;"></div>
                </button>
                
                <!-- Chat Panel -->
                <div class="budget-assistant-panel" id="budget-assistant-panel">
                    <div class="budget-assistant-header">
                        <h3>Municipal Budget Assistant</h3>
                        <div class="budget-assistant-header-controls">
                            <button class="budget-assistant-minimize-btn" id="budget-assistant-minimize-btn" title="Minimize">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="5" y1="12" x2="19" y2="12"/>
                                </svg>
                            </button>
                            <button class="budget-assistant-close" id="budget-assistant-close" title="Close">×</button>
                        </div>
                    </div>
                    
                    <div class="budget-assistant-messages" id="budget-assistant-messages">
                        <div class="budget-assistant-welcome">
                            <p>Welcome! I can help you find information about municipal budgets.</p>
                            <p>Try asking questions like:</p>
                            <ul>
                                <li>"How much is allocated to road repairs?"</li>
                                <li>"What's the Police budget for 2024?"</li>
                                <li>"Show me Public Works spending"</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="budget-assistant-input-container">
                        <input 
                            type="text" 
                            id="budget-assistant-input" 
                            placeholder="Ask about the budget..."
                            disabled
                        >
                        <button id="budget-assistant-send" disabled>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="22" y1="2" x2="11" y2="13"/>
                                <polygon points="22,2 15,22 11,13 2,9 22,2"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.widget);
        
        // Initialize state
        this.updateWidgetState();
    }
    
    loadStyles() {
        const style = document.createElement('style');
        style.textContent = `
            #budget-assistant-widget {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .budget-assistant-container {
                position: relative;
            }
            
            .budget-assistant-toggle {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 50px;
                padding: 12px 20px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
                transition: all 0.2s ease;
                position: relative;
            }
            
            .budget-assistant-toggle:hover {
                background: #1d4ed8;
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
            }
            
            .budget-assistant-minimized {
                display: none;
            }
            
            .budget-assistant-minimized.show {
                display: block;
            }
            
            .budget-assistant-minimize-toggle {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 8px 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
                font-weight: 500;
                box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
                transition: all 0.2s ease;
                position: relative;
                min-width: 120px;
            }
            
            .budget-assistant-minimize-toggle:hover {
                background: #1d4ed8;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
            }
            
            .budget-assistant-minimize-label {
                white-space: nowrap;
            }
            
            .budget-assistant-notification-dot {
                position: absolute;
                top: -2px;
                right: -2px;
                width: 8px;
                height: 8px;
                background: #ef4444;
                border-radius: 50%;
                border: 2px solid white;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.2); opacity: 0.7; }
                100% { transform: scale(1); opacity: 1; }
            }
            
            .budget-assistant-panel {
                position: absolute;
                bottom: 70px;
                right: 0;
                width: 400px;
                height: 500px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
                display: none;
                flex-direction: column;
                overflow: hidden;
            }
            
            .budget-assistant-panel.open {
                display: flex;
            }
            
            .budget-assistant-header {
                background: #f8fafc;
                padding: 16px 20px;
                border-bottom: 1px solid #e2e8f0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .budget-assistant-header h3 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
                color: #1e293b;
            }
            
            .budget-assistant-header-controls {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .budget-assistant-minimize-btn,
            .budget-assistant-close {
                background: none;
                border: none;
                cursor: pointer;
                color: #64748b;
                padding: 4px;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            .budget-assistant-minimize-btn:hover,
            .budget-assistant-close:hover {
                color: #1e293b;
                background: #e2e8f0;
            }
            
            .budget-assistant-close {
                font-size: 18px;
                font-weight: bold;
            }
            
            .budget-assistant-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            
            .budget-assistant-welcome {
                color: #64748b;
                font-size: 14px;
                line-height: 1.5;
            }
            
            .budget-assistant-welcome ul {
                margin: 8px 0 0 0;
                padding-left: 20px;
            }
            
            .budget-assistant-welcome li {
                margin: 4px 0;
            }
            
            .budget-assistant-message {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .budget-assistant-message.user {
                align-items: flex-end;
            }
            
            .budget-assistant-message.assistant {
                align-items: flex-start;
            }
            
            .budget-assistant-message-bubble {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 18px;
                font-size: 14px;
                line-height: 1.4;
            }
            
            .budget-assistant-message.user .budget-assistant-message-bubble {
                background: #2563eb;
                color: white;
            }
            
            .budget-assistant-message.assistant .budget-assistant-message-bubble {
                background: #f1f5f9;
                color: #1e293b;
            }
            
            .budget-assistant-evidence {
                margin-top: 8px;
                padding: 12px;
                background: #f8fafc;
                border-radius: 8px;
                border-left: 3px solid #2563eb;
            }
            
            .budget-assistant-evidence h4 {
                margin: 0 0 8px 0;
                font-size: 12px;
                font-weight: 600;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .budget-assistant-evidence-item {
                font-size: 12px;
                color: #64748b;
                margin: 4px 0;
                padding: 4px 0;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .budget-assistant-evidence-item:last-child {
                border-bottom: none;
            }
            
            .budget-assistant-total {
                background: #dcfce7;
                color: #166534;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: 600;
                margin: 8px 0;
            }
            
            .budget-assistant-filters {
                background: #fef3c7;
                color: #92400e;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 12px;
                margin: 8px 0;
            }
            
            .budget-assistant-loading {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #64748b;
                font-size: 14px;
            }
            
            .budget-assistant-loading-spinner {
                width: 16px;
                height: 16px;
                border: 2px solid #e2e8f0;
                border-top: 2px solid #2563eb;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .budget-assistant-input-container {
                padding: 16px 20px;
                border-top: 1px solid #e2e8f0;
                display: flex;
                gap: 8px;
            }
            
            .budget-assistant-input-container input {
                flex: 1;
                padding: 10px 12px;
                border: 1px solid #d1d5db;
                border-radius: 20px;
                font-size: 14px;
                outline: none;
            }
            
            .budget-assistant-input-container input:focus {
                border-color: #2563eb;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
            }
            
            .budget-assistant-input-container input:disabled {
                background: #f9fafb;
                color: #9ca3af;
            }
            
            .budget-assistant-input-container button {
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .budget-assistant-input-container button:hover:not(:disabled) {
                background: #1d4ed8;
            }
            
            .budget-assistant-input-container button:disabled {
                background: #d1d5db;
                cursor: not-allowed;
            }
            
            .budget-assistant-insights-button {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                cursor: pointer;
                margin-top: 8px;
                transition: background-color 0.3s;
            }
            
            .budget-assistant-insights-button:hover:not(:disabled) {
                background: #45a049;
            }
            
            .budget-assistant-insights-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .budget-assistant-insights {
                margin-top: 12px;
                padding: 12px;
                background: #f8f9fa;
                border-radius: 6px;
                border-left: 3px solid #4CAF50;
            }
            
            .budget-assistant-insights-content h4 {
                margin: 0 0 8px 0;
                color: #333;
                font-size: 14px;
                font-weight: 600;
            }
            
            .budget-assistant-insights-text {
                color: #555;
                font-size: 13px;
                line-height: 1.5;
            }
            
            .budget-assistant-insights-text strong {
                color: #333;
                font-weight: 600;
            }
            
            @media (max-width: 480px) {
                .budget-assistant-panel {
                    width: calc(100vw - 40px);
                    right: -20px;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    attachEventListeners() {
        const toggle = document.getElementById('budget-assistant-toggle');
        const close = document.getElementById('budget-assistant-close');
        const minimizeBtn = document.getElementById('budget-assistant-minimize-btn');
        const minimizeToggle = document.getElementById('budget-assistant-minimize-toggle');
        const input = document.getElementById('budget-assistant-input');
        const send = document.getElementById('budget-assistant-send');
        
        toggle.addEventListener('click', () => this.toggle());
        close.addEventListener('click', () => this.close());
        minimizeBtn.addEventListener('click', () => this.minimize());
        minimizeToggle.addEventListener('click', () => this.expand());
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isLoading) {
                this.sendMessage();
            }
        });
        
        send.addEventListener('click', () => {
            if (!this.isLoading) {
                this.sendMessage();
            }
        });
        
        // Enable input when panel opens
        toggle.addEventListener('click', () => {
            setTimeout(() => {
                input.disabled = false;
                send.disabled = false;
                input.focus();
            }, 100);
        });
        
        // Enable input when minimized widget is clicked
        minimizeToggle.addEventListener('click', () => {
            setTimeout(() => {
                input.disabled = false;
                send.disabled = false;
                input.focus();
            }, 100);
        });
        
        // Persist conversation across page navigation
        if (this.persistentMode) {
            this.loadConversationFromStorage();
            this.saveConversationToStorage();
        }
    }
    
    toggle() {
        this.isOpen = !this.isOpen;
        this.isMinimized = false;
        this.updateWidgetState();
    }
    
    close() {
        this.isOpen = false;
        this.isMinimized = false;
        this.updateWidgetState();
    }
    
    minimize() {
        this.isOpen = false;
        this.isMinimized = true;
        this.updateWidgetState();
    }
    
    expand() {
        this.isOpen = true;
        this.isMinimized = false;
        this.updateWidgetState();
    }
    
    updateWidgetState() {
        const panel = document.getElementById('budget-assistant-panel');
        const toggle = document.getElementById('budget-assistant-toggle');
        const minimized = document.getElementById('budget-assistant-minimized');
        
        if (this.isOpen) {
            panel.classList.add('open');
            toggle.style.display = 'none';
            minimized.classList.remove('show');
        } else if (this.isMinimized) {
            panel.classList.remove('open');
            toggle.style.display = 'none';
            minimized.classList.add('show');
        } else {
            panel.classList.remove('open');
            toggle.style.display = 'flex';
            minimized.classList.remove('show');
        }
    }
    
    showNotification() {
        const dot = document.getElementById('budget-assistant-notification-dot');
        const dotFull = document.getElementById('budget-assistant-notification-dot-full');
        
        if (dot) dot.style.display = 'block';
        if (dotFull) dotFull.style.display = 'block';
        
        // Auto-hide notification after 5 seconds
        setTimeout(() => {
            if (dot) dot.style.display = 'none';
            if (dotFull) dotFull.style.display = 'none';
        }, 5000);
    }
    
    hideNotification() {
        const dot = document.getElementById('budget-assistant-notification-dot');
        const dotFull = document.getElementById('budget-assistant-notification-dot-full');
        
        if (dot) dot.style.display = 'none';
        if (dotFull) dotFull.style.display = 'none';
    }
    
    saveConversationToStorage() {
        if (this.persistentMode) {
            try {
                localStorage.setItem('budget-assistant-conversation', JSON.stringify(this.conversation));
            } catch (e) {
                console.warn('Could not save conversation to localStorage:', e);
            }
        }
    }
    
    loadConversationFromStorage() {
        if (this.persistentMode) {
            try {
                const saved = localStorage.getItem('budget-assistant-conversation');
                if (saved) {
                    this.conversation = JSON.parse(saved);
                    this.renderConversation();
                }
            } catch (e) {
                console.warn('Could not load conversation from localStorage:', e);
            }
        }
    }
    
    renderConversation() {
        const messagesContainer = document.getElementById('budget-assistant-messages');
        
        // Clear existing messages
        messagesContainer.innerHTML = '';
        
        if (this.conversation.length === 0) {
            // Show welcome message
            const welcome = document.createElement('div');
            welcome.className = 'budget-assistant-welcome';
            welcome.innerHTML = `
                <p>Welcome! I can help you find information about municipal budgets.</p>
                <p>Try asking questions like:</p>
                <ul>
                    <li>"How much is allocated to road repairs?"</li>
                    <li>"What's the Police budget for 2024?"</li>
                    <li>"Show me Public Works spending"</li>
                </ul>
            `;
            messagesContainer.appendChild(welcome);
        } else {
            // Render saved conversation
            this.conversation.forEach(msg => {
                this.addMessageToDOM(msg.sender, msg.content, msg.data);
            });
        }
    }
    
    async sendMessage() {
        const input = document.getElementById('budget-assistant-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message to conversation
        this.addMessage('user', message);
        input.value = '';
        
        // Show loading state
        this.showLoading();
        
        try {
            const response = await fetch(`${this.apiUrl}/ask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.hideLoading();
            
            // Debug logging for API responses
            console.log('DEBUG API Response:', data);
            
            // Add assistant response
            this.addMessage('assistant', data.answer, data);
            
        } catch (error) {
            this.hideLoading();
            this.addMessage('assistant', `Sorry, I encountered an error: ${error.message}`);
        }
    }
    
    addMessage(sender, content, data = null) {
        // Add to conversation array
        this.conversation.push({
            sender: sender,
            content: content,
            data: data,
            timestamp: new Date().toISOString()
        });
        
        // Save to localStorage
        this.saveConversationToStorage();
        
        // Add to DOM
        this.addMessageToDOM(sender, content, data);
        
        // Show notification if minimized
        if (this.isMinimized) {
            this.showNotification();
        }
    }
    
    addMessageToDOM(sender, content, data = null) {
        try {
            const messagesContainer = document.getElementById('budget-assistant-messages');
            
            // Remove welcome message if it exists
            const welcome = messagesContainer.querySelector('.budget-assistant-welcome');
            if (welcome) {
                welcome.remove();
            }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `budget-assistant-message ${sender}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'budget-assistant-message-bubble';
        bubble.textContent = content;
        messageDiv.appendChild(bubble);
        
        // Add evidence if available
        if (data && data.evidence && data.evidence.length > 0) {
            try {
                console.log('DEBUG Processing evidence:', data.evidence);
                
                const evidenceDiv = document.createElement('div');
                evidenceDiv.className = 'budget-assistant-evidence';
                
                let evidenceHTML = '<h4>Sources</h4>';
                data.evidence.slice(0, 3).forEach((item, index) => {
                    console.log(`DEBUG Evidence item ${index}:`, item);
                    
                    // Handle both old and new evidence formats
                    const department = item.department || item.category || 'Unknown';
                    const fiscalYear = item.fiscal_year || 'N/A';
                    const amount = item.amount || item.total;
                    
                    console.log(`DEBUG Processed values - department: ${department}, fiscalYear: ${fiscalYear}, amount: ${amount}, amount type: ${typeof amount}`);
                    
                    evidenceHTML += `
                        <div class="budget-assistant-evidence-item">
                            [${index + 1}] ${department} - FY${fiscalYear}
                            ${item.file_name ? ` (${item.file_name})` : ''}
                            ${amount && typeof amount === 'number' ? ` - $${amount.toLocaleString()}` : ''}
                        </div>
                    `;
                });
                
                evidenceDiv.innerHTML = evidenceHTML;
                messageDiv.appendChild(evidenceDiv);
            } catch (error) {
                console.error('Error processing evidence:', error);
                console.error('Evidence data that caused error:', data.evidence);
                // Don't add evidence section if there's an error
            }
        }
        
        // Add total if available
        if (data && data.total && typeof data.total === 'number') {
            try {
                console.log('DEBUG Processing total:', data.total, 'type:', typeof data.total);
                
                const totalDiv = document.createElement('div');
                totalDiv.className = 'budget-assistant-total';
                totalDiv.textContent = `Total: $${data.total.toLocaleString()}`;
                messageDiv.appendChild(totalDiv);
            } catch (error) {
                console.error('Error processing total:', error);
                console.error('Total data that caused error:', data.total, 'type:', typeof data.total);
                // Don't add total section if there's an error
            }
        } else {
            console.log('DEBUG Total not processed - data.total:', data?.total, 'type:', typeof data?.total);
        }
        
        // Add filters if available
        if (data && data.filters) {
            const filters = data.filters;
            const filterParts = [];
            if (filters.fiscal_year) filterParts.push(`FY${filters.fiscal_year}`);
            if (filters.department) filterParts.push(filters.department);
            if (filters.category) filterParts.push(filters.category);
            if (filters.line_item) filterParts.push(filters.line_item);
            
            if (filterParts.length > 0) {
                const filtersDiv = document.createElement('div');
                filtersDiv.className = 'budget-assistant-filters';
                filtersDiv.textContent = `Filters: ${filterParts.join(', ')}`;
                messageDiv.appendChild(filtersDiv);
            }
        }
        
        // Add expandable insights button for assistant messages
        if (sender === 'assistant') {
            const insightsButton = document.createElement('button');
            insightsButton.className = 'budget-assistant-insights-button';
            insightsButton.textContent = 'View Insights';
            insightsButton.onclick = () => this.toggleInsights(messageDiv, data, content);
            messageDiv.appendChild(insightsButton);
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        } catch (error) {
            console.error('Error adding message to DOM:', error);
            // Fallback: just add a simple message without fancy formatting
            const messagesContainer = document.getElementById('budget-assistant-messages');
            const fallbackDiv = document.createElement('div');
            fallbackDiv.className = `budget-assistant-message ${sender}`;
            fallbackDiv.innerHTML = `<div class="budget-assistant-message-bubble">${content}</div>`;
            messagesContainer.appendChild(fallbackDiv);
        }
    }
    
    async toggleInsights(messageDiv, data, originalContent) {
        const insightsDiv = messageDiv.querySelector('.budget-assistant-insights');
        const button = messageDiv.querySelector('.budget-assistant-insights-button');
        
        if (insightsDiv) {
            // Toggle existing insights
            insightsDiv.style.display = insightsDiv.style.display === 'none' ? 'block' : 'none';
            button.textContent = insightsDiv.style.display === 'none' ? 'View Insights' : 'Hide Insights';
        } else {
            // Fetch and show insights
            button.textContent = 'Loading...';
            button.disabled = true;
            
            try {
                const response = await fetch(`${this.apiUrl}/insights`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question: this.getQuestionFromMessage(messageDiv) })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const insightsData = await response.json();
                
                // Create insights div
                const insightsDiv = document.createElement('div');
                insightsDiv.className = 'budget-assistant-insights';
                insightsDiv.innerHTML = `
                    <div class="budget-assistant-insights-content">
                        <h4>Detailed Insights</h4>
                        <div class="budget-assistant-insights-text">${this.formatInsights(insightsData.insights)}</div>
                    </div>
                `;
                
                // Insert after the message bubble
                const bubble = messageDiv.querySelector('.budget-assistant-message-bubble');
                bubble.parentNode.insertBefore(insightsDiv, bubble.nextSibling);
                
                button.textContent = 'Hide Insights';
                button.disabled = false;
                
            } catch (error) {
                button.textContent = 'View Insights';
                button.disabled = false;
                console.error('Error fetching insights:', error);
            }
        }
    }
    
    getQuestionFromMessage(messageDiv) {
        // Find the corresponding user message to get the original question
        const messagesContainer = document.getElementById('budget-assistant-messages');
        const allMessages = messagesContainer.querySelectorAll('.budget-assistant-message');
        
        for (let i = allMessages.length - 1; i >= 0; i--) {
            if (allMessages[i] === messageDiv) {
                // Look for the previous user message
                for (let j = i - 1; j >= 0; j--) {
                    if (allMessages[j].classList.contains('user')) {
                        return allMessages[j].querySelector('.budget-assistant-message-bubble').textContent;
                    }
                }
                break;
            }
        }
        return '';
    }
    
    formatInsights(insights) {
        // Format insights text with proper line breaks and styling
        return insights.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }
    
    showLoading() {
        this.isLoading = true;
        const messagesContainer = document.getElementById('budget-assistant-messages');
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'budget-assistant-message assistant';
        loadingDiv.id = 'budget-assistant-loading';
        
        loadingDiv.innerHTML = `
            <div class="budget-assistant-message-bubble">
                <div class="budget-assistant-loading">
                    <div class="budget-assistant-loading-spinner"></div>
                    <span>Thinking...</span>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(loadingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Disable input
        document.getElementById('budget-assistant-input').disabled = true;
        document.getElementById('budget-assistant-send').disabled = true;
    }
    
    hideLoading() {
        this.isLoading = false;
        const loading = document.getElementById('budget-assistant-loading');
        if (loading) {
            loading.remove();
        }
        
        // Re-enable input
        document.getElementById('budget-assistant-input').disabled = false;
        document.getElementById('budget-assistant-send').disabled = false;
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.BudgetAssistant = new BudgetAssistant();
});

// Export for manual initialization
window.BudgetAssistant = BudgetAssistant;
