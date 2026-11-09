/**
 * Balaji Connect — API Client & Global Helpers
 */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerText = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    options.credentials = options.credentials || 'same-origin';
    
    // Attach CSRF token for browser sessions
    const csrfToken = getCookie('csrftoken');
    if (csrfToken && !['GET', 'HEAD'].includes((options.method || 'GET').toUpperCase())) {
        options.headers['X-CSRFToken'] = csrfToken;
    }

    // Set JSON content-type if not multipart/form-data
    if (!(options.body instanceof FormData) && !options.headers['Content-Type']) {
        options.headers['Content-Type'] = 'application/json';
    }

    try {
        const response = await fetch(url, options);

        if (response.status === 401 || response.status === 403) {
            const data = await response.json().catch(() => ({}));
            // If account was deactivated or session invalidated
            if (data.detail && data.detail.includes('deactivated')) {
                window.location.href = '/login/?deactivated=true';
                return null;
            }
            if (response.status === 401 && !window.location.pathname.includes('/login/') && !window.location.pathname.includes('/register/')) {
                window.location.href = '/login/';
                return null;
            }
            if (!response.ok) {
                throw new Error(data.detail || 'Access denied or permission required.');
            }
        }

        if (response.status === 204) {
            return true;
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            let errorMsg = 'An unexpected error occurred.';
            if (data.detail) {
                errorMsg = data.detail;
            } else if (typeof data === 'object') {
                const firstKey = Object.keys(data)[0];
                if (firstKey && Array.isArray(data[firstKey])) {
                    errorMsg = `${firstKey}: ${data[firstKey][0]}`;
                } else if (firstKey) {
                    errorMsg = `${firstKey}: ${data[firstKey]}`;
                }
            }
            throw new Error(errorMsg);
        }

        return data;
    } catch (err) {
        showToast(err.message || 'Network communication error', 'error');
        throw err;
    }
}

// Global API service namespace
window.BalajiAPI = {
    // Auth
    login: (identifier, password, remember_me = true) => apiFetch('/api/v1/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ identifier, password, remember_me })
    }),
    register: (payload) => apiFetch('/api/v1/auth/register/', {
        method: 'POST',
        body: JSON.stringify(payload)
    }),
    logout: () => apiFetch('/api/v1/auth/logout/', { method: 'POST' }),
    getMe: () => apiFetch('/api/v1/auth/me/'),
    changePassword: (old_password, new_password) => apiFetch('/api/v1/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({ old_password, new_password })
    }),

    // Feed & Posts
    getFeed: (page = 1) => apiFetch(`/api/v1/posts/?page=${page}`),
    getPost: (postId) => apiFetch(`/api/v1/posts/${postId}/`),
    getEmployeePosts: (authorId, page = 1) => apiFetch(`/api/v1/posts/?author=${authorId}&page=${page}`),
    createPost: (content, media_ids = []) => apiFetch('/api/v1/posts/', {
        method: 'POST',
        body: JSON.stringify({ content, media_ids })
    }),
    deletePost: (postId) => apiFetch(`/api/v1/posts/${postId}/`, { method: 'DELETE' }),
    archivePost: (postId) => apiFetch(`/api/v1/posts/${postId}/archive/`, { method: 'POST' }),
    unarchivePost: (postId) => apiFetch(`/api/v1/posts/${postId}/unarchive/`, { method: 'POST' }),
    getArchivedPosts: (page = 1) => apiFetch(`/api/v1/posts/?archived=true&page=${page}`),
    toggleReaction: (postId, reaction_type = 'LIKE') => apiFetch(`/api/v1/posts/${postId}/toggle_reaction/`, {
        method: 'POST',
        body: JSON.stringify({ reaction_type })
    }),
    getPostReactions: (postId, type = '', all = true) => {
        let q = `/api/v1/posts/${postId}/reactions/?all=${all}`;
        if (type) q += `&type=${encodeURIComponent(type)}`;
        return apiFetch(q);
    },
    getComments: (postId, page = 1) => apiFetch(`/api/v1/posts/${postId}/comments/?page=${page}`),
    getEmployeeComments: (authorId, page = 1) => apiFetch(`/api/v1/comments/?author=${authorId}&page=${page}`),
    createComment: (postId, content) => apiFetch(`/api/v1/posts/${postId}/comments/`, {
        method: 'POST',
        body: JSON.stringify({ content })
    }),
    deleteComment: (commentId) => apiFetch(`/api/v1/comments/${commentId}/`, { method: 'DELETE' }),
    toggleCommentReaction: (commentId, reaction_type = 'LIKE') => apiFetch(`/api/v1/comments/${commentId}/toggle_reaction/`, {
        method: 'POST',
        body: JSON.stringify({ reaction_type })
    }),

    // Profile & Employee Details
    getEmployee: (empId) => apiFetch(`/api/v1/employees/${empId}/`),
    updateProfile: (data) => apiFetch('/api/v1/auth/me/', {
        method: 'PATCH',
        body: JSON.stringify(data)
    }),
    uploadAvatar: (file) => {
        const formData = new FormData();
        formData.append('avatar', file);
        return apiFetch('/api/v1/employees/me/avatar/', {
            method: 'POST',
            body: formData
        });
    },
    removeAvatar: () => apiFetch('/api/v1/employees/me/avatar/', { method: 'DELETE' }),
    getBirthdays: () => apiFetch('/api/v1/employees/birthdays/'),

    // Media
    uploadMedia: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return apiFetch('/api/v1/media/upload/', {
            method: 'POST',
            body: formData
        });
    },

    // Directory
    getEmployees: async (search = '', department = '') => {
        let q = `/api/v1/employees/?all=true&search=${encodeURIComponent(search)}`;
        if (department) q += `&department=${encodeURIComponent(department)}`;
        const data = await apiFetch(q);
        if (!data) return [];
        const list = Array.isArray(data) ? data : (data.results || []);
        list.results = list;
        return list;
    },
    getDepartments: () => apiFetch('/api/v1/departments/'),
    createEmployee: (empData) => apiFetch('/api/v1/employees/', {
        method: 'POST',
        body: JSON.stringify(empData)
    }),
    toggleEmployeeStatus: (empId) => apiFetch(`/api/v1/employees/${empId}/toggle_status/`, { method: 'POST' }),

    // Notifications
    getNotifications: (page = 1) => apiFetch(`/api/v1/notifications/?page=${page}`),
    getUnreadNotificationCount: () => apiFetch('/api/v1/notifications/unread-count/'),
    markNotificationRead: (id) => apiFetch(`/api/v1/notifications/${id}/mark-read/`, { method: 'POST' }),
    markAllNotificationsRead: () => apiFetch('/api/v1/notifications/mark-all-read/', { method: 'POST' }),

    // Moderation
    reportContent: (data) => apiFetch('/api/v1/reports/', {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    getReports: (status = 'PENDING') => apiFetch(`/api/v1/reports/?status=${status}`),
    reviewReport: (reportId, reviewData) => apiFetch(`/api/v1/reports/${reportId}/review/`, {
        method: 'POST',
        body: JSON.stringify(reviewData)
    }),
    getAuditLogs: () => apiFetch('/api/v1/audit-logs/'),

    // Direct Messaging (Chat)
    getConversations: () => apiFetch('/api/v1/chat/conversations/'),
    getOrCreateConversation: (recipientId, employeeId) => apiFetch('/api/v1/chat/conversations/', {
        method: 'POST',
        body: JSON.stringify({ recipient_id: recipientId, employee_id: employeeId })
    }),
    getMessages: (conversationId) => apiFetch(`/api/v1/chat/conversations/${conversationId}/messages/`),
    sendMessage: (conversationId, content) => apiFetch(`/api/v1/chat/conversations/${conversationId}/messages/`, {
        method: 'POST',
        body: JSON.stringify({ content })
    }),
    markConversationRead: (conversationId) => apiFetch(`/api/v1/chat/conversations/${conversationId}/read/`, {
        method: 'POST'
    }),
    sharePost: (postId, recipientIds, message = '') => apiFetch('/api/v1/chat/share-post/', {
        method: 'POST',
        body: JSON.stringify({ post_id: postId, recipient_ids: recipientIds, message: message })
    }),

    // Ephemeral 12-Hour Stories (Stored locally on server disk, auto-purged)
    getStories: () => apiFetch('/api/v1/stories/'),
    createStory: (file, caption = '', background = 'gradient-blue') => {
        const formData = new FormData();
        if (file) formData.append('media_file', file);
        if (caption) formData.append('caption', caption);
        if (background) formData.append('background', background);
        return apiFetch('/api/v1/stories/', {
            method: 'POST',
            body: formData
        });
    },
    recordStoryView: (storyId) => apiFetch(`/api/v1/stories/${storyId}/view/`, { method: 'POST' }),
    deleteStory: (storyId) => apiFetch(`/api/v1/stories/${storyId}/`, { method: 'DELETE' })
};

// Global Password Visibility Toggle Utility
function initPasswordToggles() {
    document.querySelectorAll('.btn-toggle-password').forEach(btn => {
        if (btn.dataset.initialized) return;
        btn.dataset.initialized = 'true';
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (!input) return;

            const eyeShow = btn.querySelector('.eye-show');
            const eyeHide = btn.querySelector('.eye-hide');

            if (input.type === 'password') {
                input.type = 'text';
                if (eyeShow) eyeShow.style.display = 'none';
                if (eyeHide) eyeHide.style.display = 'block';
            } else {
                input.type = 'password';
                if (eyeShow) eyeShow.style.display = 'block';
                if (eyeHide) eyeHide.style.display = 'none';
            }
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPasswordToggles);
} else {
    initPasswordToggles();
}
window.initPasswordToggles = initPasswordToggles;

