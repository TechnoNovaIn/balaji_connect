/**
 * Balaji Connect — Real-Time Direct Messaging (WebSocket & Channels)
 */

(function () {
    let activeConversationId = null;
    let activeRecipient = null;
    let chatSocket = null;
    let reconnectTimeout = null;
    let reconnectAttempts = 0;
    let conversationsCache = [];

    // Helper: format ISO time to e.g. "2:45 PM" or "Oct 30, 2:45 PM"
    function formatTime(isoStr) {
        if (!isoStr) return '';
        try {
            const date = new Date(isoStr);
            const now = new Date();
            const isToday = date.toDateString() === now.toDateString();
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            if (isToday) return timeStr;
            const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
            return `${dateStr}, ${timeStr}`;
        } catch (e) {
            return '';
        }
    }

    function escapeHTML(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Modal Controls
    function openChatModal(targetConvId = null) {
        if (typeof targetConvId !== 'number' && (typeof targetConvId !== 'string' || isNaN(parseInt(targetConvId)))) {
            targetConvId = null;
        } else {
            targetConvId = parseInt(targetConvId);
        }
        const modal = document.getElementById('chat-modal');
        if (modal) {
            modal.classList.add('active');
            try {
                history.pushState({ modal: 'chat-modal' }, '', '#messages');
            } catch (_) {}
            loadConversations(true, targetConvId);
        }
    }

    function closeChatModal() {
        const modal = document.getElementById('chat-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        disconnectWebSocket();
        activeConversationId = null;
        activeRecipient = null;
        const layout = document.getElementById('chat-modal-layout');
        if (layout) layout.classList.remove('active-chat');
        const backBtn = document.getElementById('btn-chat-back-to-list');
        if (backBtn) backBtn.style.display = 'none';
        const emptyState = document.getElementById('chat-empty-state');
        const thread = document.getElementById('chat-active-thread');
        if (emptyState) emptyState.style.display = 'flex';
        if (thread) thread.style.display = 'none';
        if (window.location.hash === '#messages') {
            try {
                history.replaceState({ view: 'feed' }, '', window.location.pathname);
            } catch (_) {}
        }
    }

    // Update global message badges
    function updateBadges(totalUnread) {
        const badgeIds = ['header-messages-badge', 'tab-messages-badge', 'sidebar-messages-badge'];
        badgeIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                if (totalUnread > 0) {
                    el.innerText = totalUnread > 99 ? '99+' : totalUnread;
                    el.style.display = 'inline-flex';
                } else {
                    el.style.display = 'none';
                }
            }
        });
    }

    // Load Conversations
    async function loadConversations(isInitialOpen = false, targetConvId = null) {
        const listEl = document.getElementById('chat-conversations-list');
        if (!listEl) return;

        try {
            const convs = await BalajiAPI.getConversations();
            conversationsCache = convs || [];

            let totalUnread = 0;
            conversationsCache.forEach(c => {
                totalUnread += (c.unread_count || 0);
            });
            updateBadges(totalUnread);

            if (conversationsCache.length === 0) {
                listEl.innerHTML = `
                    <div style="padding:1.25rem 0.75rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">
                        <div style="font-size:1.6rem; margin-bottom:0.4rem;">💬</div>
                        <p style="font-weight:700; color:var(--text-primary); margin-bottom:0.25rem;">Start a Direct Message</p>
                        <p style="font-size:0.75rem;">Choose a colleague below to begin chatting:</p>
                    </div>
                    <div id="chat-quick-colleagues-list" style="padding:0 0.5rem 0.5rem 0.5rem;"></div>
                `;
                try {
                    const emps = await BalajiAPI.getEmployees('');
                    const quickList = document.getElementById('chat-quick-colleagues-list');
                    if (quickList && emps && emps.length > 0) {
                        quickList.innerHTML = emps.slice(0, 10).map(emp => {
                            const initial = (emp.full_name ? emp.full_name[0] : (emp.username ? emp.username[0] : 'B')).toUpperCase();
                            const avatar = emp.avatar_url 
                                ? `<img src="${escapeHTML(emp.avatar_url)}" alt="${escapeHTML(emp.full_name)}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">`
                                : initial;
                            return `
                                <div class="chat-search-emp-item" data-emp-id="${emp.id}" data-emp-name="${escapeHTML(emp.full_name || emp.username)}" style="display:flex; align-items:center; gap:0.6rem; padding:0.55rem 0.65rem; cursor:pointer; border-radius:8px; margin-bottom:4px; transition:background 0.15s ease; border: 1px solid var(--border-light);">
                                    <div class="avatar-round avatar-sm" style="width:34px; height:34px; min-width:34px; font-size:0.85rem;">${avatar}</div>
                                    <div style="flex:1; min-width:0;">
                                        <div style="font-size:0.85rem; font-weight:700; color:var(--text-primary); text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${escapeHTML(emp.full_name || emp.username)}</div>
                                        <div style="font-size:0.72rem; color:var(--text-muted);">${escapeHTML(emp.department_name || 'Staff')}</div>
                                    </div>
                                    <button type="button" class="btn btn-primary" style="font-size:0.72rem; padding:0.2rem 0.65rem; height:28px;">Chat</button>
                                </div>
                            `;
                        }).join('');

                        quickList.querySelectorAll('.chat-search-emp-item').forEach(el => {
                            el.addEventListener('click', () => {
                                const empId = el.dataset.empId;
                                const empName = el.dataset.empName;
                                startChatWithEmployee(empId, empName);
                            });
                        });
                    }
                } catch (_) {}
                return;
            }

            listEl.innerHTML = conversationsCache.map(conv => {
                const other = conv.other_participant || {};
                const name = other.full_name || other.display_name || 'Colleague';
                const initial = (name[0] || 'B').toUpperCase();
                const avatar = other.avatar_url 
                    ? `<img src="${escapeHTML(other.avatar_url)}" alt="${escapeHTML(name)}">`
                    : initial;
                const lastMsg = conv.last_message ? escapeHTML(conv.last_message.content) : 'No messages yet';
                const time = conv.last_message ? formatTime(conv.last_message.created_at) : '';
                const unreadBadge = conv.unread_count > 0 
                    ? `<span class="chat-conv-badge">${conv.unread_count}</span>` 
                    : '';
                const isActive = activeConversationId === conv.id ? 'active' : '';

                return `
                    <div class="chat-conv-item ${isActive}" data-conv-id="${conv.id}">
                        <div class="chat-conv-avatar">${avatar}</div>
                        <div class="chat-conv-details">
                            <div class="chat-conv-top">
                                <span class="chat-conv-name">${escapeHTML(name)}</span>
                                <span class="chat-conv-time">${time}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span class="chat-conv-snippet">${lastMsg}</span>
                                ${unreadBadge}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // Bind click handlers to items
            listEl.querySelectorAll('.chat-conv-item').forEach(el => {
                el.addEventListener('click', () => {
                    const id = parseInt(el.dataset.convId);
                    selectConversation(id);
                });
            });

            // Automatically open conversation on initial open (both phone and desktop)
            if (isInitialOpen && !activeConversationId && conversationsCache.length > 0) {
                const toSelect = targetConvId || conversationsCache[0].id;
                selectConversation(toSelect);
            } else if (!activeConversationId && window.innerWidth > 640 && conversationsCache.length > 0) {
                selectConversation(conversationsCache[0].id);
            }

        } catch (err) {
            listEl.innerHTML = `
                <div style="padding:1rem; text-align:center; color:var(--danger); font-size:0.85rem;">
                    Failed to load conversations.
                </div>
            `;
        }
    }

    // Select and open conversation
    async function selectConversation(convId) {
        if (!convId) return;
        activeConversationId = convId;

        // Find metadata from cache
        const conv = conversationsCache.find(c => c.id === convId);
        const other = conv ? conv.other_participant : null;
        activeRecipient = other;

        // UI state toggles
        const layout = document.getElementById('chat-modal-layout');
        if (layout) layout.classList.add('active-chat');

        const backBtn = document.getElementById('btn-chat-back-to-list');
        if (backBtn) backBtn.style.display = 'inline-flex';

        if (window.innerWidth <= 640 && (!history.state || history.state.modal !== 'chat-thread')) {
            try {
                history.pushState({ modal: 'chat-thread', convId: convId }, '', '#messages-thread');
            } catch (_) {}
        }

        const emptyState = document.getElementById('chat-empty-state');
        const thread = document.getElementById('chat-active-thread');
        if (emptyState) emptyState.style.display = 'none';
        if (thread) thread.style.display = 'flex';

        // Update active class in list
        document.querySelectorAll('.chat-conv-item').forEach(el => {
            el.classList.toggle('active', parseInt(el.dataset.convId) === convId);
        });

        // Update header
        const titleEl = document.getElementById('chat-modal-title');
        const avatarEl = document.getElementById('chat-header-avatar');
        const statusText = document.getElementById('chat-status-text');
        const statusDot = document.getElementById('chat-status-dot');

        if (other) {
            const name = other.full_name || other.display_name || 'Colleague';
            if (titleEl) titleEl.innerText = name;
            if (avatarEl) {
                avatarEl.innerHTML = other.avatar_url 
                    ? `<img src="${escapeHTML(other.avatar_url)}" alt="${escapeHTML(name)}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">`
                    : (name[0] || 'B').toUpperCase();
            }
            if (statusText) statusText.innerText = 'Balaji Internal Messenger';
        }

        // Load message history
        const messagesList = document.getElementById('chat-messages-list');
        if (messagesList) {
            messagesList.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted); font-size:0.85rem;">Loading messages...</div>`;
        }

        try {
            const messages = await BalajiAPI.getMessages(convId);
            renderMessages(messages);
            scrollChatToBottom();

            // Mark as read
            await BalajiAPI.markConversationRead(convId).catch(() => {});
            // Clear unread badge in cache
            if (conv) {
                conv.unread_count = 0;
                loadConversations();
            }
        } catch (err) {
            if (messagesList) {
                messagesList.innerHTML = `<div style="text-align:center; padding:1.5rem; color:var(--danger); font-size:0.85rem;">Could not load messages.</div>`;
            }
        }

        // Connect WebSocket
        connectWebSocket(convId);

        // Focus message typing input
        setTimeout(() => {
            const input = document.getElementById('chat-message-input');
            if (input) {
                input.focus();
                input.scrollIntoView({ block: 'nearest' });
            }
        }, 150);

        // Focus message input
        const input = document.getElementById('chat-message-input');
        if (input) input.focus();
    }

    // Render list of messages
    function renderMessages(messages) {
        const messagesList = document.getElementById('chat-messages-list');
        if (!messagesList) return;

        if (!messages || messages.length === 0) {
            messagesList.innerHTML = `
                <div style="text-align:center; padding:2.5rem 1rem; color:var(--text-muted); font-size:0.85rem;">
                    <p style="font-size:1.4rem; margin-bottom:0.25rem;">👋</p>
                    <p>This is the start of your private conversation with <strong>${escapeHTML(activeRecipient ? activeRecipient.full_name : 'your colleague')}</strong>.</p>
                    <p style="font-size:0.75rem; margin-top:0.25rem;">Messages are secure and encrypted in transit.</p>
                </div>
            `;
            return;
        }

        messagesList.innerHTML = messages.map(msg => renderMessageRow(msg)).join('');
    }

    function renderMessageRow(msg) {
        const isOutgoing = msg.is_mine;
        const alignClass = isOutgoing ? 'outgoing' : 'incoming';
        const senderName = msg.sender_name || 'Colleague';
        const initial = (senderName[0] || 'B').toUpperCase();
        const avatar = msg.sender_avatar 
            ? `<img src="${escapeHTML(msg.sender_avatar)}" alt="${escapeHTML(senderName)}">` 
            : initial;
        const time = formatTime(msg.created_at);

        let sharedPostHtml = '';
        if (msg.shared_post) {
            const sp = msg.shared_post;
            if (sp.is_available) {
                const origAuthor = sp.author_name || 'Author';
                const origInitial = (origAuthor[0] || 'B').toUpperCase();
                const origAvatar = sp.author_avatar 
                    ? `<img src="${escapeHTML(sp.author_avatar)}" alt="${escapeHTML(origAuthor)}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">`
                    : origInitial;
                const origTime = formatTime(sp.created_at);

                let mediaHtml = '';
                if (sp.media_preview) {
                    if (sp.media_preview.file_type === 'VIDEO') {
                        mediaHtml = `
                            <div style="position:relative; margin-bottom:0.35rem;">
                                <video src="${escapeHTML(sp.media_preview.url)}" class="chat-shared-media-thumb" preload="metadata"></video>
                                <span style="position:absolute; bottom:6px; right:6px; background:rgba(0,0,0,0.7); color:#fff; font-size:0.65rem; padding:1px 4px; border-radius:3px;">▶ Video</span>
                            </div>
                        `;
                    } else {
                        mediaHtml = `<img src="${escapeHTML(sp.media_preview.url)}" alt="Post attachment" class="chat-shared-media-thumb" loading="lazy">`;
                    }
                }

                sharedPostHtml = `
                    <div class="chat-shared-post-indicator">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <circle cx="18" cy="5" r="3"></circle>
                            <circle cx="6" cy="12" r="3"></circle>
                            <circle cx="18" cy="19" r="3"></circle>
                            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                        </svg>
                        <span><strong>${escapeHTML(senderName)}</strong> shared a post</span>
                    </div>
                    <div class="chat-shared-post-card" onclick="window.BalajiChat.openPost(${sp.id})" title="Click to view original post">
                        <div class="chat-shared-author-row">
                            <div class="avatar-round avatar-xs" style="width:24px; height:24px; min-width:24px; font-size:0.7rem;">${origAvatar}</div>
                            <div style="line-height:1.2;">
                                <span class="chat-shared-author-name">${escapeHTML(origAuthor)}</span>
                                <span class="chat-shared-post-time">${origTime}</span>
                            </div>
                        </div>
                        ${sp.content ? `<div class="chat-shared-post-content">${escapeHTML(sp.content)}</div>` : ''}
                        ${mediaHtml}
                        <div class="chat-shared-post-footer">
                            <span class="chat-shared-view-btn">View Post →</span>
                        </div>
                    </div>
                `;
            } else {
                sharedPostHtml = `
                    <div class="chat-shared-post-indicator">
                        <span><strong>${escapeHTML(senderName)}</strong> shared a post</span>
                    </div>
                    <div class="chat-shared-post-card unavailable">
                        <em>This post is no longer available.</em>
                    </div>
                `;
            }
        }

        return `
            <div class="chat-msg-row ${alignClass}" data-msg-id="${msg.id || ''}">
                ${!isOutgoing ? `<div class="chat-msg-avatar">${avatar}</div>` : ''}
                <div class="chat-msg-bubble">
                    ${sharedPostHtml}
                    ${msg.content ? `<div class="chat-msg-text">${escapeHTML(msg.content)}</div>` : ''}
                    <span class="chat-msg-time">${time}</span>
                </div>
            </div>
        `;
    }

    function appendMessage(msg) {
        const messagesList = document.getElementById('chat-messages-list');
        if (!messagesList) return;

        // If currently showing the empty intro state, clear it
        if (messagesList.querySelector('div[style*="text-align:center"]')) {
            messagesList.innerHTML = '';
        }

        const div = document.createElement('div');
        div.innerHTML = renderMessageRow(msg);
        messagesList.appendChild(div.firstElementChild);
        scrollChatToBottom();
    }

    function scrollChatToBottom() {
        const scrollContainer = document.getElementById('chat-messages-scroll');
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    }

    // WebSocket Management
    function disconnectWebSocket() {
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }
        if (chatSocket) {
            try {
                chatSocket.onopen = null;
                chatSocket.onmessage = null;
                chatSocket.onerror = null;
                chatSocket.onclose = null;
                chatSocket.close();
            } catch (e) {}
            chatSocket = null;
        }
    }

    function connectWebSocket(convId) {
        disconnectWebSocket();
        reconnectAttempts = 0;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${convId}/`;

        const statusDot = document.getElementById('chat-status-dot');
        const alertEl = document.getElementById('chat-connection-alert');

        if (statusDot) {
            statusDot.className = 'status-indicator-dot reconnecting';
        }

        try {
            chatSocket = new WebSocket(wsUrl);

            chatSocket.onopen = function () {
                reconnectAttempts = 0;
                if (statusDot) {
                    statusDot.className = 'status-indicator-dot';
                }
                if (alertEl) {
                    alertEl.style.display = 'none';
                }
            };

            chatSocket.onmessage = function (e) {
                try {
                    const data = JSON.parse(e.data);
                    if (data.type === 'message' || data.type === 'chat_message') {
                        // Check if current user is sender
                        const currentUserId = window.CURRENT_USER_ID || (window.currentEmployee ? window.currentEmployee.id : null);
                        const isMine = currentUserId ? data.sender_id === currentUserId : false;

                        appendMessage({
                            id: data.id,
                            content: data.content,
                            shared_post: data.shared_post,
                            sender_name: data.sender_name,
                            sender_avatar: data.sender_avatar,
                            created_at: data.created_at,
                            is_mine: isMine
                        });

                        // If from other party, acknowledge read
                        if (!isMine) {
                            BalajiAPI.markConversationRead(convId).catch(() => {});
                        }

                        // Refresh conversation snippet in list
                        loadConversations();
                    }
                } catch (err) {}
            };

            chatSocket.onerror = function (e) {
                if (statusDot) statusDot.className = 'status-indicator-dot offline';
                if (alertEl) {
                    alertEl.innerText = 'Connection interrupted. Messages will be sent via secure fallback.';
                    alertEl.style.display = 'block';
                }
            };

            chatSocket.onclose = function (e) {
                if (activeConversationId === convId) {
                    if (statusDot) statusDot.className = 'status-indicator-dot reconnecting';
                    // Exponential backoff reconnect (max 10s)
                    const delay = Math.min(1000 * Math.pow(1.5, reconnectAttempts), 10000);
                    reconnectAttempts++;
                    reconnectTimeout = setTimeout(() => {
                        if (activeConversationId === convId) {
                            connectWebSocket(convId);
                        }
                    }, delay);
                }
            };

        } catch (err) {
            if (statusDot) statusDot.className = 'status-indicator-dot offline';
        }
    }

    // Send Message
    async function sendMessage(text) {
        if (!text || !text.trim() || !activeConversationId) return;
        const trimmed = text.trim();

        // 1. If WebSocket is connected, send through socket
        if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                type: 'message',
                message: trimmed
            }));
            return;
        }

        // 2. Fallback to REST API if WebSocket is reconnecting
        try {
            const resp = await BalajiAPI.sendMessage(activeConversationId, trimmed);
            if (resp) {
                appendMessage({
                    id: resp.id,
                    content: resp.content,
                    shared_post: resp.shared_post,
                    sender_name: resp.sender_name,
                    sender_avatar: resp.sender_avatar,
                    created_at: resp.created_at,
                    is_mine: true
                });
                loadConversations();
            }
        } catch (err) {
            showToast(err.message || 'Failed to deliver message.', 'error');
        }
    }

    // Direct chat starter: opens or creates a conversation with an employee
    async function startChatWithEmployee(empId, empName) {
        try {
            openChatModal();
            const conv = await BalajiAPI.getOrCreateConversation(empId, empId);
            if (conv && conv.id) {
                await loadConversations();
                selectConversation(conv.id);
                setTimeout(() => {
                    const input = document.getElementById('chat-message-input');
                    if (input) {
                        input.focus();
                    }
                }, 300);
            }
        } catch (err) {
            showToast(err.message || 'Could not initiate chat with employee.', 'error');
        }
    }

    // Initialize Event Listeners on DOM Ready
    document.addEventListener('DOMContentLoaded', () => {
        // Triggers to open Chat Modal
        const headerBtn = document.getElementById('btn-header-messages');
        const tabBtn = document.getElementById('tab-nav-messages');
        const sidebarBtn = document.getElementById('sidebar-nav-messages');

        if (headerBtn) headerBtn.addEventListener('click', () => openChatModal());
        if (tabBtn) tabBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openChatModal();
        });
        if (sidebarBtn) sidebarBtn.addEventListener('click', () => openChatModal());

        // Mobile back button inside chat modal
        const backBtn = document.getElementById('btn-chat-back-to-list');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                disconnectWebSocket();
                activeConversationId = null;
                const layout = document.getElementById('chat-modal-layout');
                if (layout) layout.classList.remove('active-chat');
                backBtn.style.display = 'none';

                // Reset header
                const titleEl = document.getElementById('chat-modal-title');
                const avatarEl = document.getElementById('chat-header-avatar');
                const statusText = document.getElementById('chat-status-text');
                if (titleEl) titleEl.innerText = 'Direct Messages';
                if (avatarEl) avatarEl.innerHTML = '💬';
                if (statusText) statusText.innerText = 'Balaji Internal Messenger';

                loadConversations(false);
            });
        }

        // New DM button
        const newChatBtn = document.getElementById('btn-new-chat');
        const searchInput = document.getElementById('chat-user-search-input');
        const searchResults = document.getElementById('chat-user-search-results');

        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                disconnectWebSocket();
                activeConversationId = null;
                const layout = document.getElementById('chat-modal-layout');
                if (layout) layout.classList.remove('active-chat');
                if (backBtn) backBtn.style.display = 'none';

                const titleEl = document.getElementById('chat-modal-title');
                const avatarEl = document.getElementById('chat-header-avatar');
                const statusText = document.getElementById('chat-status-text');
                if (titleEl) titleEl.innerText = 'Start a Chat';
                if (avatarEl) avatarEl.innerHTML = '✏️';
                if (statusText) statusText.innerText = 'Search or select colleague below';

                if (searchInput) {
                    searchInput.value = '';
                    searchInput.focus();
                    searchInput.scrollIntoView({ behavior: 'smooth' });
                }
            });
        }

        // Search colleague input debounce
        let searchDebounce = null;
        if (searchInput && searchResults) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounce);
                const query = e.target.value.trim();
                if (!query) {
                    searchResults.style.display = 'none';
                    searchResults.innerHTML = '';
                    return;
                }

                searchDebounce = setTimeout(async () => {
                    try {
                        const employees = await BalajiAPI.getEmployees(query);
                        if (!employees || employees.length === 0) {
                            searchResults.innerHTML = `<div style="padding:0.75rem; font-size:0.8rem; color:var(--text-muted); text-align:center;">No employees found matching "${escapeHTML(query)}".</div>`;
                            searchResults.style.display = 'block';
                            return;
                        }

                        searchResults.innerHTML = employees.map(emp => {
                            const initial = (emp.full_name ? emp.full_name[0] : (emp.username ? emp.username[0] : 'B')).toUpperCase();
                            const avatar = emp.avatar_url 
                                ? `<img src="${escapeHTML(emp.avatar_url)}" alt="${escapeHTML(emp.full_name)}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">`
                                : initial;
                            const handle = emp.username ? `@${emp.username}` : '';
                            const dept = emp.department_name || '';
                            return `
                                <div class="chat-search-emp-item" data-emp-id="${emp.id}" style="display:flex; align-items:center; gap:0.6rem; padding:0.6rem 0.75rem; cursor:pointer; border-bottom:1px solid var(--border-light); transition:background 0.15s ease;">
                                    <div class="avatar-round avatar-sm" style="width:32px; height:32px; min-width:32px; font-size:0.8rem;">${avatar}</div>
                                    <div style="flex:1; min-width:0;">
                                        <div style="font-size:0.85rem; font-weight:700; color:var(--text-primary);">${escapeHTML(emp.full_name)}</div>
                                        <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHTML(handle)}${handle && dept ? ' • ' : ''}${escapeHTML(dept)}</div>
                                    </div>
                                    <button type="button" class="btn btn-secondary" style="font-size:0.75rem; padding:0.2rem 0.5rem; height:28px;">Chat</button>
                                </div>
                            `;
                        }).join('');

                        searchResults.style.display = 'block';

                        searchResults.querySelectorAll('.chat-search-emp-item').forEach(el => {
                            el.addEventListener('click', () => {
                                const empId = el.dataset.empId;
                                searchResults.style.display = 'none';
                                searchInput.value = '';
                                startChatWithEmployee(empId);
                            });
                        });
                    } catch (err) {}
                }, 300);
            });
        }

        // Chat Form Submit
        const form = document.getElementById('chat-input-form');
        const input = document.getElementById('chat-message-input');
        if (form && input) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const text = input.value;
                if (!text || !text.trim()) return;
                input.value = '';
                sendMessage(text);
                input.focus();
            });

            // Enter key support
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    form.dispatchEvent(new Event('submit'));
                }
            });
        }

        // Profile Card "Direct Message" action button
        const profileMsgBtn = document.getElementById('btn-profile-message-action');
        if (profileMsgBtn) {
            profileMsgBtn.addEventListener('click', () => {
                const empIdEl = document.getElementById('profile-emp-id');
                const empId = empIdEl ? empIdEl.innerText.trim() : null;
                if (empId) {
                    startChatWithEmployee(empId);
                }
            });
        }

        // Initial check for unread messages count
        setTimeout(() => {
            BalajiAPI.getConversations().then(convs => {
                if (convs && Array.isArray(convs)) {
                    let total = 0;
                    convs.forEach(c => total += (c.unread_count || 0));
                    updateBadges(total);
                }
            }).catch(() => {});
        }, 1500);
    });

    function openPost(postId) {
        closeChatModal();
        // Switch to feed
        const feedNav = document.getElementById('tab-nav-feed') || document.getElementById('sidebar-nav-feed');
        if (feedNav) {
            feedNav.click();
        }

        setTimeout(() => {
            const postEl = document.getElementById(`post-${postId}`);
            if (postEl) {
                postEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                postEl.style.transition = 'box-shadow 0.3s ease, border-color 0.3s ease';
                postEl.style.boxShadow = '0 0 0 3px var(--primary)';
                postEl.style.borderColor = 'var(--primary)';
                setTimeout(() => {
                    postEl.style.boxShadow = '';
                    postEl.style.borderColor = '';
                }, 2500);
            } else {
                BalajiAPI.getPost(postId).then(post => {
                    showToast(`Loaded Post #${postId} by ${post.author_details?.full_name || 'colleague'}`);
                }).catch(() => {
                    showToast('Post could not be loaded or was removed.', 'error');
                });
            }
        }, 200);
    }

    // Expose global helper
    window.BalajiChat = {
        open: openChatModal,
        close: closeChatModal,
        startWith: startChatWithEmployee,
        openConversationWith: startChatWithEmployee,
        loadConversations: loadConversations,
        openPost: openPost
    };
})();

