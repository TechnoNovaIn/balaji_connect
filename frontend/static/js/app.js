/**
 * Balaji Connect — Facebook-Inspired Mobile-First Application Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    initBalajiApp();
});

const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '😡', '🔥', '🎉', '👏', '💯', '🤝', '🙌'];
const REACTION_GIFS = [
    { label: 'Applause', url: 'https://media.giphy.com/media/nbvFVPiEiJH6TCGAXf/giphy.gif' },
    { label: 'Thumbs Up', url: 'https://media.giphy.com/media/111ebonMs90YLu/giphy.gif' },
    { label: 'Celebrate', url: 'https://media.giphy.com/media/artj92V8o75VPL7AeQ/giphy.gif' },
    { label: 'High Five', url: 'https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif' },
    { label: 'Laughing', url: 'https://media.giphy.com/media/10JhviFuU2gWD6/giphy.gif' },
    { label: 'Thinking', url: 'https://media.giphy.com/media/d3mlE7uhX8KFgEmY/giphy.gif' },
    { label: 'Thank You', url: 'https://media.giphy.com/media/osAcIGeWAaP8A/giphy.gif' },
    { label: 'Great Job', url: 'https://media.giphy.com/media/3ohzdIuqJoo8QdKlnW/giphy.gif' }
];

const REACTION_MAP = {
    LIKE: { emoji: '👍', label: 'Like', cls: 'reaction-LIKE' },
    LOVE: { emoji: '❤️', label: 'Love', cls: 'reaction-LOVE' },
    HAHA: { emoji: '😂', label: 'Haha', cls: 'reaction-HAHA' },
    WOW: { emoji: '😮', label: 'Wow', cls: 'reaction-WOW' },
    SAD: { emoji: '😢', label: 'Sad', cls: 'reaction-SAD' },
    ANGRY: { emoji: '😡', label: 'Angry', cls: 'reaction-ANGRY' }
};

let currentUser = null;
let currentProfileUser = null;
let currentPendingMedia = null; // { id, type, url, filename }
let currentFeedPage = 1;
let hasNextFeedPage = false;
let isFeedLoading = false;
let isSubmittingPost = false;

async function initBalajiApp() {
    try {
        currentUser = await BalajiAPI.getMe();
        if (currentUser) {
            setupUserSessionUI(currentUser);
            loadSocialFeed(1);
            loadBirthdaysBanner();
            setupComposerInteractions();
            setupNavigationTabs();
            setupNotificationsEngine();
            setupDirectoryEngine();
            setupModerationEngine();
            setupProfileAndSecurity();
            setupProfileScreen();
            setupEditProfileModal();
            setupAccountToggleMenu();
            setupPostReactionsModal();
            setupCommentActionModal();
            setupShareModal();
            setupPostActionModal();
            setupAdminModalTabs();
            setupStoriesFeature();
        }
    } catch (err) {
        console.warn('Session verification notice:', err);
    }
}

// -------------------------------------------------------------
// USER SESSION & UI HYDRATION
// -------------------------------------------------------------
function setupUserSessionUI(user) {
    const initial = (user.first_name?.[0] || user.employee_id?.[0] || 'B').toUpperCase();
    document.querySelectorAll('.user-avatar-placeholder').forEach(el => {
        if (user.avatar_url) {
            el.innerHTML = `<img src="${user.avatar_url}" alt="${user.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;">`;
        } else {
            el.innerText = initial;
        }
    });

    document.querySelectorAll('.user-full-name').forEach(el => {
        el.innerText = user.full_name;
    });

    document.querySelectorAll('.user-first-name').forEach(el => {
        el.innerText = user.first_name || user.display_name || 'team';
    });

    const deptText = user.department_details?.code || user.department_details?.name || 'Balaji';
    document.querySelectorAll('.user-department').forEach(el => {
        el.innerText = deptText;
    });

    const flyoutBio = document.getElementById('user-flyout-bio');
    if (flyoutBio) {
        if (user.bio && user.bio.trim()) {
            flyoutBio.innerText = user.bio;
            flyoutBio.style.display = 'block';
        } else {
            flyoutBio.style.display = 'none';
        }
    }

    document.querySelectorAll('.user-employee-id').forEach(el => {
        el.innerText = user.employee_id;
    });

    // Reveal administrator controls if user is ADMIN
    if (user.role === 'ADMIN') {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'flex';
        });
    }

    // Show desktop right sidebar if on widescreen
    if (window.innerWidth >= 1200) {
        const rightSidebar = document.getElementById('desktop-right-sidebar');
        if (rightSidebar) rightSidebar.style.display = 'block';
    }
}

// -------------------------------------------------------------
// POST COMPOSER (Facebook Pattern)
// -------------------------------------------------------------
function setupComposerInteractions() {
    const triggerPill = document.getElementById('btn-trigger-composer');
    const quickPhotoBtn = document.getElementById('btn-quick-photo');
    const quickMilestoneBtn = document.getElementById('btn-quick-milestone');
    const composerModal = document.getElementById('composer-modal');
    const modalFileSelect = document.getElementById('modal-media-file-input');
    const modalPostTextarea = document.getElementById('modal-post-textarea');
    const modalPublishBtn = document.getElementById('btn-modal-publish-post');
    const modalHeaderPublishBtn = document.getElementById('btn-modal-header-publish');
    const modalPreviewBox = document.getElementById('composer-media-preview');
    const modalPreviewContent = document.getElementById('modal-preview-content');
    const removeMediaBtn = document.getElementById('modal-remove-media-btn');

    function updatePublishButtons(disabled, text) {
        if (modalPublishBtn) {
            modalPublishBtn.disabled = disabled;
            modalPublishBtn.innerText = text;
        }
        if (modalHeaderPublishBtn) {
            modalHeaderPublishBtn.disabled = disabled;
            modalHeaderPublishBtn.innerText = text;
        }
    }

    // Open composer modal on pill click
    triggerPill?.addEventListener('click', () => {
        openModal(composerModal);
        modalPostTextarea?.focus();
    });

    // Quick Photo/Video button
    quickPhotoBtn?.addEventListener('click', () => {
        modalFileSelect?.click();
    });

    // Quick Milestone button
    quickMilestoneBtn?.addEventListener('click', () => {
        openModal(composerModal);
        modalPostTextarea.value = "🚀 Milestone Update: ";
        modalPostTextarea.focus();
    });

    let isUploadingMedia = false;

    // Handle file selection & upload to media vault
    modalFileSelect?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        openModal(composerModal);

        // Immediate instant client-side preview so user sees the image immediately
        const localBlobUrl = URL.createObjectURL(file);
        modalPreviewContent.innerHTML = '';
        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = localBlobUrl;
            img.className = 'media-preview-img';
            img.alt = 'Uploaded preview';
            modalPreviewContent.appendChild(img);
        } else {
            const video = document.createElement('video');
            video.src = localBlobUrl;
            video.controls = true;
            video.className = 'media-preview-video';
            modalPreviewContent.appendChild(video);
        }
        modalPreviewBox.classList.add('active');

        // Dynamic upload status badge on the preview
        let uploadBadge = document.getElementById('composer-upload-badge');
        if (!uploadBadge) {
            uploadBadge = document.createElement('div');
            uploadBadge.id = 'composer-upload-badge';
            uploadBadge.className = 'composer-upload-badge';
            modalPreviewBox.appendChild(uploadBadge);
        }
        uploadBadge.innerHTML = '<span>⚡ Uploading to Google Drive vault...</span>';
        uploadBadge.style.display = 'flex';

        isUploadingMedia = true;
        updatePublishButtons(true, 'Uploading media...');

        try {
            const attachment = await BalajiAPI.uploadMedia(file);
            currentPendingMedia = attachment;
            uploadBadge.innerHTML = '<span>✓ Saved to Google Drive</span>';
            setTimeout(() => { if (uploadBadge) uploadBadge.style.display = 'none'; }, 2000);
            showToast('Media attached successfully.', 'success');
        } catch (err) {
            modalFileSelect.value = '';
            currentPendingMedia = null;
            modalPreviewBox.classList.remove('active');
            if (uploadBadge) uploadBadge.style.display = 'none';
        } finally {
            isUploadingMedia = false;
            updatePublishButtons(false, 'Post');
        }
    });

    // Remove attached media
    removeMediaBtn?.addEventListener('click', () => {
        currentPendingMedia = null;
        modalFileSelect.value = '';
        modalPreviewBox.classList.remove('active');
        modalPreviewContent.innerHTML = '';
    });

    // Publish Post handler
    const handlePublishPost = async () => {
        if (isSubmittingPost) return;
        if (isUploadingMedia) {
            showToast('Please wait, your media is still uploading to the vault...', 'info');
            return;
        }

        const content = modalPostTextarea.value.trim();
        const mediaIds = currentPendingMedia ? [currentPendingMedia.id] : [];

        if (!content && mediaIds.length === 0) {
            showToast('Please enter text or attach a photo/video.', 'error');
            return;
        }

        isSubmittingPost = true;
        updatePublishButtons(true, 'Publishing...');

        try {
            await BalajiAPI.createPost(content, mediaIds);
            showToast('Post published to company feed!', 'success');
            modalPostTextarea.value = '';
            currentPendingMedia = null;
            modalFileSelect.value = '';
            modalPreviewBox.classList.remove('active');
            modalPreviewContent.innerHTML = '';
            closeAllModals();
            loadSocialFeed(1);
        } catch (err) {
            // Handled in apiFetch
        } finally {
            isSubmittingPost = false;
            updatePublishButtons(false, 'Post');
        }
    };

    modalPublishBtn?.addEventListener('click', handlePublishPost);
    modalHeaderPublishBtn?.addEventListener('click', handlePublishPost);
}

// -------------------------------------------------------------
// SOCIAL FEED RENDERING
// -------------------------------------------------------------
async function loadSocialFeed(page = 1) {
    const feedContainer = document.getElementById('feed-container');
    const loadMoreContainer = document.getElementById('load-more-container');
    if (!feedContainer || isFeedLoading) return;

    isFeedLoading = true;
    if (page === 1) {
        feedContainer.innerHTML = '<div class="empty-state-card"><p>Loading company updates...</p></div>';
    }

    try {
        const response = await BalajiAPI.getFeed(page);
        isFeedLoading = false;

        if (page === 1) {
            feedContainer.innerHTML = '';
        }

        if (!response.results || response.results.length === 0) {
            if (page === 1) {
                feedContainer.innerHTML = `
                    <div class="empty-state-card">
                        <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                            <polyline points="17 21 17 13 7 13 7 21"></polyline>
                        </svg>
                        <h4 style="margin-bottom:0.25rem;">No company updates yet</h4>
                        <p style="font-size:0.875rem;">Be the first to share an operational update, fleet photograph, or milestone!</p>
                    </div>`;
            }
            hasNextFeedPage = false;
            if (loadMoreContainer) loadMoreContainer.style.display = 'none';
            return;
        }

        hasNextFeedPage = !!response.next;
        currentFeedPage = page;

        response.results.forEach(post => {
            const card = buildPostCardElement(post);
            feedContainer.appendChild(card);
        });

        if (loadMoreContainer) {
            loadMoreContainer.style.display = hasNextFeedPage ? 'block' : 'none';
        }

    } catch (err) {
        isFeedLoading = false;
        if (page === 1) {
            feedContainer.innerHTML = '<div class="empty-state-card"><p>Could not load feed. Please pull to refresh.</p></div>';
        }
    }
}

// Post Card Component
function buildPostCardElement(post) {
    const card = document.createElement('article');
    card.className = 'post-card';
    card.id = `post-${post.id}`;

    const author = post.author_details || {};
    const authorInitial = (author.first_name?.[0] || author.employee_id?.[0] || 'B').toUpperCase();
    const deptBadge = author.department_code || 'BT';
    const relativeTime = formatRelativeTime(post.created_at);

    const authorAvatarHtml = author.avatar_url ? 
        `<img src="${author.avatar_url}" alt="${author.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;">` :
        authorInitial;

    // Responsive Media Markup
    let mediaMarkup = '';
    if (post.media_attachments && post.media_attachments.length > 0) {
        if (post.media_attachments.length === 1) {
            const item = post.media_attachments[0];
            if (item.file_type === 'IMAGE') {
                mediaMarkup = `
                    <div class="post-media-stage">
                        <img src="${item.view_url}" alt="Attached media" loading="lazy" onerror="this.parentElement.style.display='none'">
                    </div>`;
            } else {
                mediaMarkup = `
                    <div class="post-media-stage">
                        <video src="${item.view_url}" controls playsinline preload="metadata"></video>
                    </div>`;
            }
        } else {
            // Multi-photo collage grid (Facebook style)
            const imgItems = post.media_attachments.filter(m => m.file_type === 'IMAGE');
            mediaMarkup = `
                <div class="media-grid-2">
                    ${imgItems.slice(0, 2).map(m => `<img src="${m.view_url}" alt="Gallery photo" loading="lazy">`).join('')}
                </div>`;
        }
    }

    // Reaction details
    const activeReaction = post.user_reaction;
    const currentReactionInfo = activeReaction ? REACTION_MAP[activeReaction] : null;
    const reactionLabel = currentReactionInfo ? currentReactionInfo.label : 'Like';
    const reactionClass = currentReactionInfo ? `active ${currentReactionInfo.cls}` : '';
    const reactionIconMarkup = currentReactionInfo ? 
        `<span style="font-size:1.15rem; line-height:1; margin-right:4px;">${currentReactionInfo.emoji}</span>` :
        `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
        </svg>`;
    const statsTopEmoji = currentReactionInfo ? currentReactionInfo.emoji : '👍';

    card.innerHTML = `
        <!-- Post Header -->
        <div class="post-header">
            <div class="post-author-block" style="cursor:pointer;" title="View employee profile">
                <div class="avatar-round avatar-sm user-avatar-item">${authorAvatarHtml}</div>
                <div class="post-meta-col">
                    <span class="post-author-title">${escapeHTML(author.full_name)}</span>
                    <div class="post-author-subtitle">
                        <time datetime="${post.created_at}" title="${new Date(post.created_at).toLocaleString()}">${relativeTime}</time>
                        <span>•</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" title="Company private">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                    </div>
                </div>
            </div>

            <!-- Options Menu -->
            <button class="post-options-btn" data-post-id="${post.id}" aria-label="Post options" title="More options">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="2"></circle>
                    <circle cx="19" cy="12" r="2"></circle>
                    <circle cx="5" cy="12" r="2"></circle>
                </svg>
            </button>
        </div>

        <!-- Post Body -->
        ${post.content ? `<div class="post-body-text">${escapeHTML(post.content)}</div>` : ''}

        <!-- Media Stage -->
        ${mediaMarkup}

        <!-- Post Stats Row -->
        <div class="post-stats-row">
            <div class="reaction-counter-pill" id="reaction-counter-${post.id}" style="cursor:pointer;" title="View who reacted">
                <span class="like-circle-icon">${statsTopEmoji}</span>
                <span id="stat-like-${post.id}">${post.like_count}</span>
            </div>
            <div>
                <span id="stat-comments-${post.id}">${post.comment_count} ${post.comment_count === 1 ? 'comment' : 'comments'}</span>
            </div>
        </div>

        <!-- Action Bar (Facebook 3-Button Pattern with Reaction Dock) -->
        <div class="post-action-bar">
            <div class="reaction-trigger-wrap" data-post-id="${post.id}">
                <div class="reaction-dock" id="reaction-dock-${post.id}">
                    <button type="button" class="reaction-dock-item" data-reaction="LIKE" data-post-id="${post.id}" title="Like">
                        <span class="reaction-dock-emoji">👍</span>
                    </button>
                    <button type="button" class="reaction-dock-item" data-reaction="LOVE" data-post-id="${post.id}" title="Love">
                        <span class="reaction-dock-emoji">❤️</span>
                    </button>
                    <button type="button" class="reaction-dock-item" data-reaction="HAHA" data-post-id="${post.id}" title="Haha">
                        <span class="reaction-dock-emoji">😂</span>
                    </button>
                    <button type="button" class="reaction-dock-item" data-reaction="WOW" data-post-id="${post.id}" title="Wow">
                        <span class="reaction-dock-emoji">😮</span>
                    </button>
                    <button type="button" class="reaction-dock-item" data-reaction="SAD" data-post-id="${post.id}" title="Sad">
                        <span class="reaction-dock-emoji">😢</span>
                    </button>
                    <button type="button" class="reaction-dock-item" data-reaction="ANGRY" data-post-id="${post.id}" title="Angry">
                        <span class="reaction-dock-emoji">😡</span>
                    </button>
                </div>

                <button class="feed-action-btn btn-action-like ${reactionClass}" data-post-id="${post.id}" data-current-reaction="${activeReaction || ''}">
                    <span class="reaction-btn-icon">${reactionIconMarkup}</span>
                    <span class="reaction-btn-label">${reactionLabel}</span>
                </button>
            </div>

            <button class="feed-action-btn btn-action-comment" data-post-id="${post.id}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                </svg>
                <span>Comment</span>
            </button>

            <button class="feed-action-btn btn-action-share" data-post-id="${post.id}">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="18" cy="5" r="3"></circle>
                    <circle cx="6" cy="12" r="3"></circle>
                    <circle cx="18" cy="19" r="3"></circle>
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                </svg>
                <span>Share</span>
            </button>
        </div>

        <!-- Inline Comments Drawer -->
        <div class="comments-drawer" id="comments-drawer-${post.id}" style="display:none;">
            <!-- Write comment row -->
            <div class="comment-input-wrap">
                <div class="avatar-round avatar-sm user-avatar-placeholder" style="width:32px; height:32px; min-width:32px; font-size:0.8rem;">B</div>
                <div class="comment-input-container">
                    <div class="comment-input-box">
                        <input 
                            type="text" 
                            class="comment-input-field" 
                            id="comment-field-${post.id}" 
                            placeholder="Write a comment..." 
                            maxlength="2000"
                            aria-label="Write a comment"
                        >
                        <div class="comment-input-tools">
                            <button type="button" class="btn-comment-tool btn-comment-emoji" title="Insert emoji" aria-label="Emoji">😀</button>
                            <button type="button" class="btn-comment-tool btn-comment-gif" title="Post GIF" aria-label="GIF">GIF</button>
                        </div>
                        <button class="btn-send-comment" data-post-id="${post.id}" title="Send comment" aria-label="Send">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                        </button>
                    </div>
                    <!-- Emojis & GIFs Trays (Floating popups anchored above input box) -->
                    <div class="comment-emoji-tray" id="comment-emoji-tray-${post.id}" style="display:none;"></div>
                    <div class="comment-gif-tray" id="comment-gif-tray-${post.id}" style="display:none;"></div>
                </div>
            </div>

            <!-- Comments List -->
            <div class="comments-list" id="comments-list-${post.id}"></div>
        </div>
    `;

    // Click author to open profile
    const authorBlock = card.querySelector('.post-author-block');
    authorBlock?.addEventListener('click', () => {
        if (author.id) openEmployeeProfile(author.id);
    });

    // Hook reaction interactions (Facebook pattern: single tap = like/unlike, long press = emoji dock)
    const likeBtn = card.querySelector('.btn-action-like');
    const triggerWrap = card.querySelector('.reaction-trigger-wrap');
    const dock = card.querySelector('.reaction-dock');

    let pressTimer = null;
    let isLongPress = false;
    let touchStartTime = 0;

    const startLongPress = () => {
        isLongPress = false;
        touchStartTime = Date.now();
        clearTimeout(pressTimer);
        pressTimer = setTimeout(() => {
            isLongPress = true;
            // Close any other open reaction docks
            document.querySelectorAll('.reaction-dock.show-dock').forEach(d => {
                if (d !== dock) d.classList.remove('show-dock');
            });
            dock.classList.add('show-dock');
            if (navigator.vibrate) {
                try { navigator.vibrate(40); } catch (_) {}
            }
        }, 400); // 400ms long-press threshold
    };

    const cancelLongPress = () => {
        clearTimeout(pressTimer);
    };

    // Mobile touch events on like button
    likeBtn.addEventListener('touchstart', (e) => {
        startLongPress();
    }, { passive: true });

    likeBtn.addEventListener('touchmove', () => {
        cancelLongPress();
    }, { passive: true });

    likeBtn.addEventListener('touchend', () => {
        cancelLongPress();
        if (isLongPress) {
            // Long press completed and dock opened; prevent click from toggling like
            setTimeout(() => { isLongPress = false; }, 350);
        }
    });

    likeBtn.addEventListener('touchcancel', () => {
        cancelLongPress();
        isLongPress = false;
    });

    // Desktop mouse events (hold left mouse button to open dock)
    likeBtn.addEventListener('mousedown', (e) => {
        if (e.button === 0) {
            startLongPress();
        }
    });

    likeBtn.addEventListener('mouseup', () => {
        cancelLongPress();
    });

    likeBtn.addEventListener('mouseleave', () => {
        cancelLongPress();
    });

    // Like button click (single click / quick tap)
    likeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isLongPress || (Date.now() - touchStartTime > 380 && isLongPress)) {
            // Was a long press to open the dock; don't toggle like on release!
            isLongPress = false;
            return;
        }

        // If dock was open, close it
        if (dock.classList.contains('show-dock')) {
            dock.classList.remove('show-dock');
            return;
        }

        const current = likeBtn.dataset.currentReaction;
        if (current) {
            sendReaction(post.id, current, likeBtn);
        } else {
            sendReaction(post.id, 'LIKE', likeBtn);
        }
    });

    // Reaction dock emoji buttons
    let emojiSelectedRecently = false;
    card.querySelectorAll('.reaction-dock-item').forEach(item => {
        const handleEmojiSelect = (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (emojiSelectedRecently) return;
            emojiSelectedRecently = true;
            setTimeout(() => { emojiSelectedRecently = false; }, 400);

            const rType = item.dataset.reaction;

            // Immediately close dock
            dock.classList.remove('show-dock');
            document.querySelectorAll('.reaction-dock.show-dock').forEach(d => d.classList.remove('show-dock'));
            item.blur();

            sendReaction(post.id, rType, likeBtn);
        };

        item.addEventListener('touchend', handleEmojiSelect);
        item.addEventListener('click', handleEmojiSelect);
    });

    // Dismiss dock when tapping anywhere outside
    const handleOutsideReactionTap = (e) => {
        if (!triggerWrap.contains(e.target)) {
            dock.classList.remove('show-dock');
        }
    };
    document.addEventListener('touchstart', handleOutsideReactionTap, { passive: true });
    document.addEventListener('click', handleOutsideReactionTap);

    // Reaction counter pill: click to see who reacted
    const reactionCounter = card.querySelector(`#reaction-counter-${post.id}`);
    reactionCounter?.addEventListener('click', () => {
        openPostReactionsModal(post.id);
    });

    const commentBtn = card.querySelector('.btn-action-comment');
    commentBtn?.addEventListener('click', () => toggleCommentsDrawer(post.id));

    const shareBtn = card.querySelector('.btn-action-share');
    shareBtn?.addEventListener('click', () => handleSharePost(post.id));

    const sendCommentBtn = card.querySelector('.btn-send-comment');
    sendCommentBtn?.addEventListener('click', () => submitNewComment(post.id));

    const commentInputField = card.querySelector(`#comment-field-${post.id}`);
    commentInputField?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') submitNewComment(post.id);
    });

    // Comment Emoji & GIF Trays
    const emojiBtn = card.querySelector('.btn-comment-emoji');
    const gifBtn = card.querySelector('.btn-comment-gif');
    const emojiTray = card.querySelector(`#comment-emoji-tray-${post.id}`);
    const gifTray = card.querySelector(`#comment-gif-tray-${post.id}`);

    if (emojiTray) {
        emojiTray.innerHTML = REACTION_EMOJIS.map(em => `
            <button type="button" class="comment-emoji-item" data-emoji="${em}">${em}</button>
        `).join('');

        emojiTray.querySelectorAll('.comment-emoji-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (commentInputField) {
                    commentInputField.value += btn.dataset.emoji;
                    commentInputField.focus();
                }
            });
        });
    }

    if (gifTray) {
        gifTray.innerHTML = REACTION_GIFS.map(g => `
            <div class="comment-gif-item" data-gif-url="${g.url}" title="${escapeHTML(g.label)}">
                <img src="${g.url}" alt="${escapeHTML(g.label)}" loading="lazy">
            </div>
        `).join('');

        gifTray.querySelectorAll('.comment-gif-item').forEach(item => {
            item.addEventListener('click', async (e) => {
                e.stopPropagation();
                const url = item.dataset.gifUrl;
                gifTray.style.display = 'none';
                await submitNewComment(post.id, url);
            });
        });
    }

    emojiBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (gifTray) gifTray.style.display = 'none';
        if (emojiTray) {
            emojiTray.style.display = emojiTray.style.display === 'none' ? 'grid' : 'none';
        }
    });

    gifBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (emojiTray) emojiTray.style.display = 'none';
        if (gifTray) {
            gifTray.style.display = gifTray.style.display === 'none' ? 'grid' : 'none';
        }
    });

    const optionsBtn = card.querySelector('.post-options-btn');
    optionsBtn?.addEventListener('click', () => handlePostOptions(post));

    return card;
}

// -------------------------------------------------------------
// POST ACTIONS (Multi-Emoji Reactions / Comments / Share)
// -------------------------------------------------------------
async function sendReaction(postId, reactionType, button) {
    try {
        const result = await BalajiAPI.toggleReaction(postId, reactionType);
        const countSpan = document.getElementById(`stat-like-${postId}`);
        if (countSpan) countSpan.innerText = result.like_count;

        // Hide floating dock
        const dock = document.getElementById(`reaction-dock-${postId}`);
        if (dock) dock.classList.remove('show-dock');

        // Clean previous reaction classes
        Object.values(REACTION_MAP).forEach(r => button.classList.remove(r.cls));

        if (result.liked && result.user_reaction) {
            const info = REACTION_MAP[result.user_reaction] || REACTION_MAP.LIKE;
            button.classList.add('active', info.cls);
            button.dataset.currentReaction = result.user_reaction;
            button.querySelector('.reaction-btn-icon').innerHTML = `<span style="font-size:1.15rem; line-height:1; margin-right:4px;">${info.emoji}</span>`;
            button.querySelector('.reaction-btn-label').innerText = info.label;

            const iconPill = document.querySelector(`#post-${postId} .like-circle-icon`);
            if (iconPill) iconPill.innerText = info.emoji;

            const iconEl = button.querySelector('.reaction-btn-icon');
            if (iconEl) {
                iconEl.classList.remove('pop');
                void iconEl.offsetWidth;
                iconEl.classList.add('pop');
            }
        } else {
            button.classList.remove('active');
            button.dataset.currentReaction = '';
            button.querySelector('.reaction-btn-icon').innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>`;
            button.querySelector('.reaction-btn-label').innerText = 'Like';

            const iconPill = document.querySelector(`#post-${postId} .like-circle-icon`);
            if (iconPill) iconPill.innerText = '👍';

            const iconEl = button.querySelector('.reaction-btn-icon');
            if (iconEl) {
                iconEl.classList.remove('pop');
                void iconEl.offsetWidth;
                iconEl.classList.add('pop');
            }
        }
    } catch (err) {
        // Handled in apiFetch
    }
}

async function toggleCommentsDrawer(postId) {
    const drawer = document.getElementById(`comments-drawer-${postId}`);
    if (!drawer) return;

    if (drawer.style.display === 'none') {
        drawer.style.display = 'flex';
        loadPostComments(postId);
        const inputField = document.getElementById(`comment-field-${postId}`);
        inputField?.focus();
    } else {
        drawer.style.display = 'none';
    }
}

async function loadPostComments(postId) {
    const container = document.getElementById(`comments-list-${postId}`);
    if (!container) return;

    container.innerHTML = '<div style="font-size:0.8rem; color:var(--text-muted); padding:0.25rem 0;">Loading comments...</div>';

    try {
        const response = await BalajiAPI.getComments(postId);
        container.innerHTML = '';
        if (!response.results || response.results.length === 0) {
            container.innerHTML = '<div style="font-size:0.8rem; color:var(--text-muted); padding:0.25rem 0;">No comments yet.</div>';
            return;
        }

        response.results.forEach(comment => {
            const author = comment.author_details || {};
            const initial = (author.first_name?.[0] || 'B').toUpperCase();
            const relTime = formatRelativeTime(comment.created_at);
            const avatarHtml = author.avatar_url ?
                `<img src="${author.avatar_url}" alt="${author.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;">` :
                initial;

            // Check if comment contains a GIF URL
            const gifMatch = comment.content.match(/https?:\/\/[^\s]+(?:\.gif|giphy\.com[^\s]+)/i);
            let commentBodyHtml = '';
            if (gifMatch) {
                const gifUrl = gifMatch[0];
                const textWithoutGif = comment.content.replace(gifUrl, '').trim();
                commentBodyHtml = `
                    ${textWithoutGif ? `<div class="comment-bubble-text">${escapeHTML(textWithoutGif)}</div>` : ''}
                    <div style="margin-top:4px;">
                        <img src="${gifUrl}" alt="GIF" style="max-width:220px; width:100%; border-radius:10px; display:block;" loading="lazy">
                    </div>
                `;
            } else {
                commentBodyHtml = `<div class="comment-bubble-text">${escapeHTML(comment.content)}</div>`;
            }

            const row = document.createElement('div');
            row.style.marginBottom = '0.5rem';
            row.id = `comment-item-${comment.id}`;

            const userReactionEmoji = comment.user_reaction ? (REACTION_MAP[comment.user_reaction]?.emoji || '👍') : null;

            row.innerHTML = `
                <div class="comment-bubble-row">
                    <div class="avatar-round avatar-sm comment-author-avatar" style="width:28px; height:28px; min-width:28px; font-size:0.75rem; cursor:pointer;" title="View profile">${avatarHtml}</div>
                    <div class="comment-bubble-content" data-comment-id="${comment.id}" ${comment.is_owner ? 'title="Long press to manage"' : ''}>
                        <div class="comment-bubble-author" style="cursor:pointer;" title="View profile">${escapeHTML(author.full_name)}</div>
                        ${commentBodyHtml}
                        ${comment.is_owner ? `
                            <button type="button" class="comment-options-trigger" data-comment-id="${comment.id}" title="Comment options">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                                    <circle cx="12" cy="12" r="2"></circle>
                                    <circle cx="19" cy="12" r="2"></circle>
                                    <circle cx="5" cy="12" r="2"></circle>
                                </svg>
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div class="comment-meta-actions">
                    <span>${relTime}</span>
                    <button type="button" class="comment-react-btn ${comment.user_reaction ? 'active' : ''}" data-comment-id="${comment.id}">
                        ${userReactionEmoji || 'Like'}
                    </button>
                    ${comment.like_count > 0 ? `<span class="comment-like-badge" id="comment-likes-${comment.id}">👍 ${comment.like_count}</span>` : `<span class="comment-like-badge" id="comment-likes-${comment.id}" style="display:none;"></span>`}
                </div>
            `;

            // Author profile click
            row.querySelector('.comment-bubble-author')?.addEventListener('click', () => {
                if (author.id) openEmployeeProfile(author.id);
            });
            row.querySelector('.comment-author-avatar')?.addEventListener('click', () => {
                if (author.id) openEmployeeProfile(author.id);
            });

            // Comment reaction toggle
            const reactBtn = row.querySelector('.comment-react-btn');
            reactBtn?.addEventListener('click', async (e) => {
                e.stopPropagation();
                try {
                    const res = await BalajiAPI.toggleCommentReaction(comment.id, 'LIKE');
                    const badge = row.querySelector(`#comment-likes-${comment.id}`);
                    if (res.liked) {
                        reactBtn.classList.add('active');
                        reactBtn.innerText = REACTION_MAP[res.reaction_type]?.emoji || '👍';
                    } else {
                        reactBtn.classList.remove('active');
                        reactBtn.innerText = 'Like';
                    }
                    if (badge) {
                        badge.innerText = `👍 ${res.like_count}`;
                        badge.style.display = res.like_count > 0 ? 'inline-flex' : 'none';
                    }
                } catch (err) {
                    console.error('Comment reaction error:', err);
                }
            });

            // Long press and options click for Instagram-style delete action modal
            if (comment.is_owner) {
                const bubble = row.querySelector('.comment-bubble-content');
                const triggerBtn = row.querySelector('.comment-options-trigger');

                let pressTimer = null;
                bubble?.addEventListener('touchstart', (e) => {
                    pressTimer = setTimeout(() => {
                        if (navigator.vibrate) navigator.vibrate(35);
                        openCommentActionModal(comment.id, comment.content, postId);
                    }, 350);
                }, { passive: true });

                bubble?.addEventListener('touchend', () => {
                    clearTimeout(pressTimer);
                });
                bubble?.addEventListener('touchmove', () => {
                    clearTimeout(pressTimer);
                });

                triggerBtn?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    openCommentActionModal(comment.id, comment.content, postId);
                });
            }

            container.appendChild(row);
        });
    } catch (err) {
        container.innerHTML = '<div style="font-size:0.8rem; color:var(--danger);">Error loading comments.</div>';
    }
}

async function submitNewComment(postId, explicitText = null) {
    const input = document.getElementById(`comment-field-${postId}`);
    const text = explicitText !== null ? explicitText : input?.value.trim();
    if (!text) return;

    if (input && explicitText === null) input.value = '';

    try {
        await BalajiAPI.createComment(postId, text);
        loadPostComments(postId);

        const countSpan = document.getElementById(`stat-comments-${postId}`);
        if (countSpan) {
            const current = parseInt(countSpan.innerText) || 0;
            const updated = current + 1;
            countSpan.innerText = `${updated} ${updated === 1 ? 'comment' : 'comments'}`;
        }
    } catch (err) {
        // Handled in apiFetch
    }
}

async function deleteCommentItem(commentId, postId = null) {
    try {
        await BalajiAPI.deleteComment(commentId);
        showToast('Comment deleted.', 'info');
        if (postId) {
            loadPostComments(postId);
            const countSpan = document.getElementById(`stat-comments-${postId}`);
            if (countSpan) {
                const current = parseInt(countSpan.innerText) || 1;
                const updated = Math.max(0, current - 1);
                countSpan.innerText = `${updated} ${updated === 1 ? 'comment' : 'comments'}`;
            }
        }
    } catch (err) {
        // Handled in apiFetch
    }
}

// -------------------------------------------------------------
// POST REACTIONS VIEWER & COMMENT ACTION MODALS
// -------------------------------------------------------------
let currentReactionsPostId = null;
let currentReactionsBreakdown = {};

function setupPostReactionsModal() {
    const modal = document.getElementById('post-reactions-modal');
    if (!modal) return;
    modal.querySelectorAll('.modal-close-btn').forEach(btn => {
        btn.addEventListener('click', () => modal.classList.remove('active'));
    });
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });
}

async function openPostReactionsModal(postId, activeFilter = 'ALL') {
    currentReactionsPostId = postId;
    const modal = document.getElementById('post-reactions-modal');
    const tabsBar = document.getElementById('post-reactions-tabs-bar');
    const list = document.getElementById('post-reactions-list');
    if (!modal || !tabsBar || !list) return;

    modal.classList.add('active');
    list.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted); font-size:0.85rem;">Loading reactions...</div>';

    try {
        const typeParam = (activeFilter === 'ALL') ? '' : activeFilter;
        const res = await BalajiAPI.getPostReactions(postId, typeParam, true);
        if (res.breakdown) {
            currentReactionsBreakdown = res.breakdown;
        }

        // Render Tabs
        const totalCount = res.count !== undefined ? res.count : (res.results ? res.results.length : 0);
        let tabsHtml = `
            <button type="button" class="reaction-tab-pill ${activeFilter === 'ALL' ? 'active' : ''}" data-type="ALL">
                All ${totalCount}
            </button>
        `;
        Object.entries(currentReactionsBreakdown).forEach(([rType, count]) => {
            const info = REACTION_MAP[rType];
            const emoji = info ? info.emoji : rType;
            tabsHtml += `
                <button type="button" class="reaction-tab-pill ${activeFilter === rType ? 'active' : ''}" data-type="${rType}">
                    ${emoji} ${count}
                </button>
            `;
        });
        tabsBar.innerHTML = tabsHtml;

        tabsBar.querySelectorAll('.reaction-tab-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                const selectedType = btn.dataset.type;
                openPostReactionsModal(postId, selectedType);
            });
        });

        // Render List
        if (!res.results || res.results.length === 0) {
            list.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted); font-size:0.85rem;">No reactions found.</div>';
            return;
        }

        list.innerHTML = '';
        res.results.forEach(item => {
            const u = item.user_details || {};
            const info = REACTION_MAP[item.reaction_type] || { emoji: '👍' };
            const initial = (u.first_name?.[0] || 'B').toUpperCase();
            const avatarMarkup = u.avatar_url ?
                `<img src="${u.avatar_url}" alt="${escapeHTML(u.full_name)}">` :
                initial;

            const row = document.createElement('div');
            row.className = 'reaction-user-row';
            row.innerHTML = `
                <div class="reaction-user-avatar-wrap">
                    <div class="avatar-round avatar-sm reaction-user-avatar">${avatarMarkup}</div>
                    <span class="reaction-user-emoji-badge">${info.emoji}</span>
                </div>
                <div class="reaction-user-info">
                    <div class="reaction-user-name">${escapeHTML(u.full_name)}</div>
                    <div class="reaction-user-meta">@${escapeHTML(u.username || '')} • ${escapeHTML(u.department_name || 'Balaji Transports')}</div>
                </div>
            `;
            row.addEventListener('click', () => {
                modal.classList.remove('active');
                if (u.id) openEmployeeProfile(u.id);
            });
            list.appendChild(row);
        });

    } catch (err) {
        list.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--danger); font-size:0.85rem;">Failed to load reactions.</div>';
    }
}

let pendingDeleteCommentId = null;
let pendingDeleteCommentPostId = null;

function setupCommentActionModal() {
    const modal = document.getElementById('comment-action-modal');
    if (!modal) return;

    const cancelBtn = document.getElementById('btn-cancel-comment-action');
    cancelBtn?.addEventListener('click', () => modal.classList.remove('active'));

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });

    const confirmBtn = document.getElementById('btn-confirm-delete-comment');
    confirmBtn?.addEventListener('click', async () => {
        if (!pendingDeleteCommentId) return;
        const commentId = pendingDeleteCommentId;
        const postId = pendingDeleteCommentPostId;
        modal.classList.remove('active');

        try {
            await BalajiAPI.deleteComment(commentId);
            showToast('Comment deleted.', 'info');
            if (postId) {
                loadPostComments(postId);
                const countSpan = document.getElementById(`stat-comments-${postId}`);
                if (countSpan) {
                    const current = parseInt(countSpan.innerText) || 1;
                    const updated = Math.max(0, current - 1);
                    countSpan.innerText = `${updated} ${updated === 1 ? 'comment' : 'comments'}`;
                }
            } else if (currentProfileUser) {
                loadProfileComments(currentProfileUser.id);
            }
        } catch (err) {
            // Handled in apiFetch
        }
    });
}

function openCommentActionModal(commentId, snippet, postId = null) {
    pendingDeleteCommentId = commentId;
    pendingDeleteCommentPostId = postId;
    const modal = document.getElementById('comment-action-modal');
    const snippetEl = document.getElementById('comment-action-snippet');
    if (!modal) return;

    if (snippetEl) {
        let cleanText = snippet ? snippet.replace(/https?:\/\/[^\s]+(?:\.gif|giphy\.com[^\s]+)/i, '[GIF]').trim() : '';
        snippetEl.innerText = cleanText.length > 50 ? cleanText.substring(0, 50) + '...' : cleanText;
    }
    modal.classList.add('active');
}

// -------------------------------------------------------------
// POST SHARING VIA DIRECT MESSAGES (INSTAGRAM STYLE)
// -------------------------------------------------------------
let currentSharePostId = null;
let selectedShareRecipients = new Set();
let cachedShareEmployees = [];

async function handleSharePost(postId) {
    currentSharePostId = postId;
    selectedShareRecipients.clear();

    const modal = document.getElementById('share-modal');
    const snippetEl = document.getElementById('share-post-snippet');
    const authorEl = document.getElementById('share-post-author-name');
    const noteInput = document.getElementById('share-custom-note');
    const searchInput = document.getElementById('share-search-input');
    const countEl = document.getElementById('share-selected-count');
    const sendBtn = document.getElementById('btn-confirm-share');
    const listEl = document.getElementById('share-recipients-list');

    if (!modal) return;

    if (noteInput) noteInput.value = '';
    if (searchInput) searchInput.value = '';
    if (countEl) countEl.innerText = '0 selected';
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = `
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
            <span>Send</span>
        `;
    }

    const postEl = document.getElementById(`post-${postId}`);
    if (postEl) {
        const authorTitle = postEl.querySelector('.post-author-title')?.innerText || 'Employee';
        const bodyText = postEl.querySelector('.post-body-text')?.innerText || '[Media Post]';
        if (authorEl) authorEl.innerText = authorTitle;
        if (snippetEl) snippetEl.innerText = bodyText;
    } else {
        if (authorEl) authorEl.innerText = `Post #${postId}`;
        if (snippetEl) snippetEl.innerText = 'Loading post details...';
        BalajiAPI.getPost(postId).then(p => {
            if (authorEl) authorEl.innerText = p.author_details?.full_name || 'Employee';
            if (snippetEl) snippetEl.innerText = p.content || (p.media_attachments?.length ? '[Media Post]' : '');
        }).catch(() => {});
    }

    openModal(modal);

    if (listEl) {
        listEl.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.85rem;">Loading colleagues...</div>';
    }

    try {
        const emps = await BalajiAPI.getEmployees();
        const empList = Array.isArray(emps) ? emps : (emps.results || []);
        cachedShareEmployees = empList.filter(e => !currentUser || e.id !== currentUser.id);
        renderShareRecipients(cachedShareEmployees);
    } catch (err) {
        if (listEl) {
            listEl.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--danger); font-size:0.85rem;">Failed to load employees.</div>';
        }
    }
}

function renderShareRecipients(employees) {
    const listEl = document.getElementById('share-recipients-list');
    if (!listEl) return;

    if (!employees || employees.length === 0) {
        listEl.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.85rem;">No colleagues found.</div>';
        return;
    }

    listEl.innerHTML = employees.map(emp => {
        const isSelected = selectedShareRecipients.has(emp.id);
        const name = emp.full_name || emp.username || 'Colleague';
        const init = (emp.first_name?.[0] || emp.username?.[0] || 'B').toUpperCase();
        const avatar = emp.avatar_url 
            ? `<img src="${escapeHTML(emp.avatar_url)}" alt="${escapeHTML(name)}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">`
            : init;
        const userHandle = emp.username ? `@${emp.username}` : '';

        return `
            <div class="share-emp-row ${isSelected ? 'selected' : ''}" data-emp-id="${emp.id}" style="display:flex; align-items:center; gap:0.75rem; padding:0.6rem 0.75rem; border-radius:var(--radius-md); cursor:pointer; margin-bottom:0.35rem; transition:background-color 0.15s ease;">
                <div class="avatar-round avatar-sm" style="width:38px; height:38px; min-width:38px; font-size:0.9rem;">${avatar}</div>
                <div style="flex:1; min-width:0; line-height:1.25;">
                    <div style="font-size:0.875rem; font-weight:600; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHTML(name)}</div>
                    <div style="font-size:0.78rem; color:var(--text-muted); font-weight:500;">${escapeHTML(userHandle)}</div>
                </div>
                <div class="ig-check-circle ${isSelected ? 'checked' : ''}">
                    ${isSelected ? '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>' : ''}
                </div>
            </div>
        `;
    }).join('');

    listEl.querySelectorAll('.share-emp-row').forEach(row => {
        row.addEventListener('click', () => {
            const empId = parseInt(row.dataset.empId);
            const checkCircle = row.querySelector('.ig-check-circle');
            if (selectedShareRecipients.has(empId)) {
                selectedShareRecipients.delete(empId);
                row.classList.remove('selected');
                if (checkCircle) {
                    checkCircle.classList.remove('checked');
                    checkCircle.innerHTML = '';
                }
            } else {
                selectedShareRecipients.add(empId);
                row.classList.add('selected');
                if (checkCircle) {
                    checkCircle.classList.add('checked');
                    checkCircle.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                }
            }

            const countEl = document.getElementById('share-selected-count');
            const sendBtn = document.getElementById('btn-confirm-share');
            const count = selectedShareRecipients.size;

            if (countEl) countEl.innerText = `${count} selected`;
            if (sendBtn) {
                sendBtn.disabled = (count === 0);
                const sendLabel = count > 1 ? `Send (${count})` : 'Send';
                sendBtn.innerHTML = `
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                    <span>${sendLabel}</span>
                `;
            }
        });
    });
}

function setupShareModal() {
    const searchInput = document.getElementById('share-search-input');
    const sendBtn = document.getElementById('btn-confirm-share');
    const noteInput = document.getElementById('share-custom-note');

    searchInput?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) {
            renderShareRecipients(cachedShareEmployees);
            return;
        }
        const filtered = cachedShareEmployees.filter(emp => {
            const name = (emp.full_name || '').toLowerCase();
            const username = (emp.username || '').toLowerCase();
            return name.includes(query) || username.includes(query);
        });
        renderShareRecipients(filtered);
    });

    sendBtn?.addEventListener('click', async () => {
        if (!currentSharePostId || selectedShareRecipients.size === 0) return;

        sendBtn.disabled = true;
        sendBtn.innerText = 'Sending...';

        const recipientIds = Array.from(selectedShareRecipients);
        const note = noteInput ? noteInput.value.trim() : '';

        try {
            const resp = await BalajiAPI.sharePost(currentSharePostId, recipientIds, note);
            closeAllModals();
            showToast(resp.detail || `Post shared with ${recipientIds.length} colleague(s) via Direct Message!`, 'success');
        } catch (err) {
            showToast(err.message || 'Could not share post.', 'error');
            sendBtn.disabled = false;
            sendBtn.innerHTML = `
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
                <span>Send</span>
            `;
        }
    });
}

// -------------------------------------------------------------
// POST OPTIONS (INSTAGRAM-STYLE MODAL)
// -------------------------------------------------------------
let currentOptionsPost = null;

function setupPostActionModal() {
    const modal = document.getElementById('post-action-modal');
    if (!modal) return;

    modal.querySelectorAll('.modal-close-btn').forEach(btn => {
        btn.addEventListener('click', () => modal.classList.remove('active'));
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });

    // Delete post action
    const deleteBtn = document.getElementById('btn-post-action-delete');
    deleteBtn?.addEventListener('click', async () => {
        if (!currentOptionsPost) return;
        const post = currentOptionsPost;
        modal.classList.remove('active');

        try {
            await BalajiAPI.deletePost(post.id);
            showToast('Post deleted successfully.', 'info');
            const postCard = document.getElementById(`post-${post.id}`);
            if (postCard) {
                postCard.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                postCard.style.opacity = '0';
                postCard.style.transform = 'scale(0.95)';
                setTimeout(() => postCard.remove(), 250);
            }
        } catch (err) {
            showToast(err.message || 'Could not delete post.', 'error');
        }
    });

    // Share post action
    const shareBtn = document.getElementById('btn-post-action-share');
    shareBtn?.addEventListener('click', () => {
        if (!currentOptionsPost) return;
        const postId = currentOptionsPost.id;
        modal.classList.remove('active');
        handleSharePost(postId);
    });

    // Archive / Unarchive post action (Admin only)
    const archiveBtn = document.getElementById('btn-post-action-archive');
    archiveBtn?.addEventListener('click', async () => {
        if (!currentOptionsPost) return;
        const post = currentOptionsPost;
        modal.classList.remove('active');
        try {
            if (post.is_archived) {
                await BalajiAPI.unarchivePost(post.id);
                showToast(`Post #${post.id} restored to public feed.`, 'success');
            } else {
                await BalajiAPI.archivePost(post.id);
                showToast(`Post #${post.id} moved to archive.`, 'success');
            }
            loadSocialFeed(1);
        } catch (err) {
            // Handled in apiFetch
        }
    });

    // Report post action
    const reportBtn = document.getElementById('btn-post-action-report');
    reportBtn?.addEventListener('click', () => {
        if (!currentOptionsPost) return;
        const postId = currentOptionsPost.id;
        modal.classList.remove('active');
        openReportModal('post', postId);
    });
}

function handlePostOptions(post) {
    currentOptionsPost = post;
    const modal = document.getElementById('post-action-modal');
    const snippetEl = document.getElementById('post-action-snippet');
    const deleteBtn = document.getElementById('btn-post-action-delete');
    const archiveBtn = document.getElementById('btn-post-action-archive');
    const archiveText = document.getElementById('post-action-archive-text');
    const reportBtn = document.getElementById('btn-post-action-report');
    if (!modal) return;

    if (snippetEl) {
        const text = post.content ? post.content.trim() : (post.media_attachments?.length ? '[Photo/Video Post]' : 'Post');
        snippetEl.innerText = text.length > 50 ? text.substring(0, 50) + '...' : text;
    }

    const isAdmin = currentUser && (currentUser.role === 'ADMIN' || currentUser.is_administrator);
    const canDelete = post.is_owner || isAdmin;

    if (deleteBtn) deleteBtn.style.display = canDelete ? 'flex' : 'none';

    if (archiveBtn) {
        if (isAdmin) {
            archiveBtn.style.display = 'flex';
            if (archiveText) {
                archiveText.innerText = post.is_archived ? 'Restore to Feed' : 'Archive Post';
            }
        } else {
            archiveBtn.style.display = 'none';
        }
    }

    if (reportBtn) reportBtn.style.display = !canDelete ? 'flex' : 'none';

    modal.classList.add('active');
}

// -------------------------------------------------------------
// NAVIGATION TABS CONTROLLER (Facebook Pattern)
// -------------------------------------------------------------
function setupNavigationTabs() {
    const feedTab = document.getElementById('tab-nav-feed');
    const directoryTab = document.getElementById('tab-nav-directory');
    const notifsTab = document.getElementById('tab-nav-notifs');
    const adminTab = document.getElementById('tab-nav-admin');
    const profileTab = document.getElementById('tab-nav-profile');

    const directoryModal = document.getElementById('directory-modal');
    const notifsModal = document.getElementById('notifications-modal');
    const adminModal = document.getElementById('admin-modal');
    const profileModal = document.getElementById('profile-menu-modal');

    const brandLink = document.getElementById('brand-logo-link') || document.querySelector('.brand-wordmark');
    brandLink?.addEventListener('click', (e) => {
        e.preventDefault();
        closeAllModals();
        showFeedView();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    feedTab?.addEventListener('click', (e) => {
        e.preventDefault();
        showFeedView();
    });

    notifsTab?.addEventListener('click', (e) => {
        e.preventDefault();
        openModal(notifsModal);
        loadNotificationsStream();
    });

    adminTab?.addEventListener('click', (e) => {
        e.preventDefault();
        openModal(adminModal);
        loadAdminModerationReports();
        loadAdminArchivedPosts();
    });

    profileTab?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleAccountMenu();
    });

    // Header buttons (Desktop)
    document.getElementById('btn-quick-search')?.addEventListener('click', () => {
        openModal(directoryModal);
        searchEmployeeDirectory('');
    });

    document.getElementById('btn-header-notifs')?.addEventListener('click', () => {
        openModal(notifsModal);
        loadNotificationsStream();
    });

    document.getElementById('btn-header-admin')?.addEventListener('click', () => {
        openModal(adminModal);
        loadAdminModerationReports();
        loadAdminArchivedPosts();
    });

    document.getElementById('btn-header-profile')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleAccountMenu();
    });

    // Sidebar navigation buttons (Desktop)
    document.getElementById('sidebar-nav-feed')?.addEventListener('click', () => {
        showFeedView();
    });
    document.getElementById('sidebar-nav-directory')?.addEventListener('click', () => {
        openModal(directoryModal);
        searchEmployeeDirectory('');
    });
    document.getElementById('sidebar-nav-notifs')?.addEventListener('click', () => {
        openModal(notifsModal);
        loadNotificationsStream();
    });
    document.getElementById('sidebar-nav-admin')?.addEventListener('click', () => {
        openModal(adminModal);
        loadAdminModerationReports();
        loadAdminArchivedPosts();
    });
    document.getElementById('sidebar-nav-profile')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleAccountMenu();
    });

    // Load more feed button
    document.getElementById('btn-load-more')?.addEventListener('click', () => {
        if (hasNextFeedPage && !isFeedLoading) {
            loadSocialFeed(currentFeedPage + 1);
        }
    });
}

function setActiveTab(activeElement) {
    document.querySelectorAll('.nav-tab-item').forEach(el => el.classList.remove('active'));
    activeElement.classList.add('active');
}

// -------------------------------------------------------------
// NOTIFICATIONS ENGINE
// -------------------------------------------------------------
function setupNotificationsEngine() {
    async function updateUnreadCount() {
        try {
            const res = await BalajiAPI.getUnreadNotificationCount();
            const headerBadge = document.getElementById('header-notif-badge');
            const tabBadge = document.getElementById('tab-notif-badge');

            const count = res?.unread_count || 0;
            const display = count > 9 ? '9+' : String(count);

            if (headerBadge) {
                headerBadge.innerText = display;
                headerBadge.style.display = count > 0 ? 'flex' : 'none';
            }
            if (tabBadge) {
                tabBadge.innerText = display;
                tabBadge.style.display = count > 0 ? 'flex' : 'none';
            }
        } catch (e) {}
    }

    updateUnreadCount();
    setInterval(updateUnreadCount, 30000); // 30-sec polling

    document.getElementById('btn-mark-all-read')?.addEventListener('click', async () => {
        await BalajiAPI.markAllNotificationsRead();
        showToast('All notifications marked as read.', 'success');
        updateUnreadCount();
        loadNotificationsStream();
    });
}

async function loadNotificationsStream() {
    const list = document.getElementById('notifications-stream-list');
    if (!list) return;

    list.innerHTML = '<div class="empty-state-card"><p>Loading notifications...</p></div>';

    try {
        const res = await BalajiAPI.getNotifications();
        list.innerHTML = '';
        if (!res.results || res.results.length === 0) {
            list.innerHTML = '<div class="empty-state-card"><p>No notifications. You are all caught up!</p></div>';
            return;
        }

        res.results.forEach(notif => {
            const item = document.createElement('div');
            item.style.padding = '0.75rem';
            item.style.borderRadius = 'var(--radius-md)';
            item.style.backgroundColor = notif.is_read ? 'var(--bg-card)' : 'var(--primary-light)';
            item.style.border = '1px solid var(--border-light)';
            if (notif.notification_type === 'BIRTHDAY') {
                item.style.borderLeft = '4px solid #f59e0b';
            }
            item.style.cursor = 'pointer';

            const relTime = formatRelativeTime(notif.created_at);

            item.innerHTML = `
                <div style="font-weight:700; font-size:0.875rem; color:var(--text-primary);">${escapeHTML(notif.title)}</div>
                <div style="font-size:0.85rem; color:var(--text-secondary); margin-top:0.15rem;">${escapeHTML(notif.message)}</div>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.3rem;">${relTime}</div>
            `;

            item.addEventListener('click', async () => {
                if (!notif.is_read) {
                    await BalajiAPI.markNotificationRead(notif.id);
                    item.style.backgroundColor = 'var(--bg-card)';
                }
                if (notif.notification_type === 'BIRTHDAY') {
                    closeAllModals();
                    // Once clicked, hide birthday banner from company feed
                    const banner = document.getElementById('birthday-banner');
                    if (banner) banner.style.display = 'none';
                    const todayKey = new Date().toDateString();
                    sessionStorage.setItem('balaji_birthday_dismissed_' + todayKey, '1');
                    localStorage.setItem('balaji_birthday_dismissed_' + todayKey, '1');

                    const celebrantId = notif.sender_details?.id;
                    const celebrantName = notif.sender_details?.full_name || 'Colleague';
                    if (celebrantId && (!currentUser || celebrantId !== currentUser.id)) {
                        openDirectMessageWith(celebrantId, celebrantName);
                    } else if (celebrantId) {
                        openEmployeeProfile(celebrantId);
                    }
                }
            });

            list.appendChild(item);
        });
    } catch (err) {
        list.innerHTML = '<div class="empty-state-card"><p>Failed to load notifications.</p></div>';
    }
}

// -------------------------------------------------------------
// EMPLOYEE DIRECTORY ENGINE
// -------------------------------------------------------------
function setupDirectoryEngine() {
    const searchInput = document.getElementById('directory-search-input');
    const headerSearch = document.getElementById('header-search-input');
    const directoryModal = document.getElementById('directory-modal');
    const quickSearchBtn = document.getElementById('btn-quick-search');
    const sidebarSearchBtn = document.getElementById('sidebar-nav-directory');

    let debounceTimer;
    function handleSearch(val) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            searchEmployeeDirectory(val);
        }, 220);
    }

    searchInput?.addEventListener('input', (e) => handleSearch(e.target.value));

    headerSearch?.addEventListener('input', (e) => {
        openModal(directoryModal);
        if (searchInput) {
            searchInput.value = e.target.value;
            searchInput.focus();
        }
        handleSearch(e.target.value);
    });

    quickSearchBtn?.addEventListener('click', () => {
        openModal(directoryModal);
        if (searchInput) {
            searchInput.focus();
            if (!searchInput.value) searchEmployeeDirectory('');
        }
    });

    sidebarSearchBtn?.addEventListener('click', () => {
        openModal(directoryModal);
        if (searchInput) {
            searchInput.focus();
            if (!searchInput.value) searchEmployeeDirectory('');
        }
    });
}

async function searchEmployeeDirectory(query = '') {
    const list = document.getElementById('directory-results-list');
    if (!list) return;

    list.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.85rem;">Searching users...</div>';

    try {
        const res = await BalajiAPI.getEmployees(query);
        list.innerHTML = '';
        const users = Array.isArray(res) ? res : (res.results || []);

        if (!users || users.length === 0) {
            list.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.85rem;">No users found.</div>';
            return;
        }

        users.forEach(emp => {
            const row = document.createElement('div');
            row.className = 'search-user-item';
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.gap = '0.75rem';
            row.style.padding = '0.65rem 0.85rem';
            row.style.backgroundColor = 'var(--bg-card)';
            row.style.borderRadius = 'var(--radius-md)';
            row.style.border = '1px solid var(--border-light)';
            row.style.cursor = 'pointer';
            row.style.marginBottom = '0.35rem';
            row.style.transition = 'background-color 0.15s ease, transform 0.1s ease';

            const name = emp.full_name || emp.username || 'Colleague';
            const initial = (emp.first_name?.[0] || emp.username?.[0] || 'B').toUpperCase();
            const avatarHtml = emp.avatar_url
                ? `<img src="${escapeHTML(emp.avatar_url)}" alt="${escapeHTML(name)}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;">`
                : initial;

            row.innerHTML = `
                <div class="avatar-round avatar-sm" style="width:38px; height:38px; min-width:38px; font-size:0.9rem;">${avatarHtml}</div>
                <div style="flex:1; min-width:0; line-height:1.25;">
                    <div style="font-weight:600; font-size:0.9rem; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHTML(name)}</div>
                    <div style="font-size:0.8rem; color:var(--text-muted); font-weight:500;">@${escapeHTML(emp.username || '')}</div>
                </div>
            `;

            row.addEventListener('mouseenter', () => {
                row.style.backgroundColor = 'var(--bg-hover)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.backgroundColor = 'var(--bg-card)';
            });

            row.addEventListener('click', () => {
                closeAllModals();
                if (emp.id) openEmployeeProfile(emp.id);
            });

            list.appendChild(row);
        });
    } catch (err) {
        list.innerHTML = '<div style="text-align:center; padding:1.5rem; color:var(--danger); font-size:0.85rem;">Error searching users.</div>';
    }
}

// -------------------------------------------------------------
// CONTENT REPORTING & MODERATION ENGINE
// -------------------------------------------------------------
let pendingReportTarget = null; // { type, id }

function openReportModal(type, id) {
    pendingReportTarget = { type, id };
    openModal(document.getElementById('report-modal'));
}

function setupModerationEngine() {
    const reportForm = document.getElementById('report-form');
    reportForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!pendingReportTarget) return;

        const reason = document.getElementById('report-reason').value;
        const desc = document.getElementById('report-description').value;

        const payload = {
            reason,
            description: desc,
            post: pendingReportTarget.type === 'post' ? pendingReportTarget.id : null,
            comment: pendingReportTarget.type === 'comment' ? pendingReportTarget.id : null,
        };

        try {
            await BalajiAPI.reportContent(payload);
            showToast('Thank you. Content submitted for moderation review.', 'success');
            closeAllModals();
        } catch (err) {
            // Handled in apiFetch
        }
    });
}

async function loadAdminModerationReports() {
    const list = document.getElementById('admin-reports-list');
    const badge = document.getElementById('badge-admin-reports-count');
    if (!list) return;

    list.innerHTML = '<div class="empty-state-card"><p>Loading pending reports...</p></div>';

    try {
        const res = await BalajiAPI.getReports('PENDING');
        list.innerHTML = '';
        const count = res.results ? res.results.length : 0;
        if (badge) {
            badge.innerText = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }

        if (!res.results || res.results.length === 0) {
            list.innerHTML = '<div class="empty-state-card"><p>No pending content reports. All clear! 🎉</p></div>';
            return;
        }

        res.results.forEach(rep => {
            const card = document.createElement('div');
            card.style.border = '1px solid var(--border-light)';
            card.style.borderRadius = 'var(--radius-md)';
            card.style.padding = '0.95rem';
            card.style.backgroundColor = 'var(--bg-card)';
            card.style.boxShadow = '0 2px 8px rgba(0,0,0,0.05)';

            const isPost = rep.target_summary?.type === 'POST' || rep.post;
            const targetId = rep.post || rep.comment || rep.target_summary?.id;
            const targetAuthor = rep.target_summary?.author || 'Unknown';
            const targetContent = rep.target_summary?.content || '';
            const mediaList = rep.target_summary?.media_urls || [];

            let mediaPreviewHtml = '';
            if (mediaList.length > 0) {
                mediaPreviewHtml = `
                    <div style="display:flex; gap:6px; margin-top:8px; overflow-x:auto; padding-bottom:4px;">
                        ${mediaList.map(url => `<img src="${url}" style="width:72px; height:72px; object-fit:cover; border-radius:6px; border:1px solid var(--border-light);" loading="lazy" alt="Media attachment">`).join('')}
                    </div>
                `;
            }

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <span style="font-weight:700; color:#ef4444; font-size:0.85rem; background:rgba(239,68,68,0.1); padding:2px 8px; border-radius:12px;">⚠️ ${escapeHTML(rep.reason)}</span>
                    <span style="font-size:0.75rem; color:var(--text-muted);">${formatRelativeTime(rep.created_at)}</span>
                </div>

                <!-- Reporter Info -->
                <div style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:0.6rem; padding:6px 10px; background:var(--bg-input); border-radius:6px;">
                    <strong>Reported by:</strong> ${escapeHTML(rep.reporter_details?.full_name || 'Employee')}
                    ${rep.description ? `<br><span style="font-style:italic; color:var(--text-primary);">"${escapeHTML(rep.description)}"</span>` : ''}
                </div>

                <!-- Full Reported Item Inspection Box -->
                <div style="border:1px solid var(--border-light); border-radius:8px; padding:0.75rem; background:var(--bg-card); margin-bottom:0.75rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                        <span style="font-weight:700; font-size:0.85rem; color:var(--text-primary);">${isPost ? '📝 Post' : '💬 Comment'} #${targetId} by <strong>${escapeHTML(targetAuthor)}</strong></span>
                        ${isPost ? `<button type="button" class="btn btn-secondary btn-open-target-post" data-post-id="${targetId}" style="min-height:28px; padding:0.2rem 0.6rem; font-size:0.75rem; display:inline-flex; align-items:center; gap:4px; font-weight:700; border-color:var(--primary); color:var(--primary);">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                            🔍 Open Post
                        </button>` : (rep.target_summary?.post_id ? `<button type="button" class="btn btn-secondary btn-open-target-post" data-post-id="${rep.target_summary.post_id}" style="min-height:28px; padding:0.2rem 0.6rem; font-size:0.75rem; display:inline-flex; align-items:center; gap:4px; font-weight:700; border-color:var(--primary); color:var(--primary);">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                            🔍 Open Post
                        </button>` : '')}
                    </div>
                    <div style="font-size:0.875rem; color:var(--text-primary); line-height:1.45; word-break:break-word; max-height:160px; overflow-y:auto; background:var(--bg-input); padding:0.6rem; border-radius:6px;">
                        ${escapeHTML(targetContent) || '<em style="color:var(--text-muted);">[Media Only / No text]</em>'}
                    </div>
                    ${mediaPreviewHtml}
                </div>

                <!-- Admin Action Buttons -->
                <div style="display:flex; gap:0.5rem; justify-content:flex-end; flex-wrap:wrap;">
                    <button type="button" class="btn btn-secondary btn-dismiss-report" data-id="${rep.id}" style="min-height:32px; padding:0.3rem 0.75rem; font-size:0.8rem; font-weight:600;">Dismiss Report</button>
                    ${isPost ? `<button type="button" class="btn btn-secondary btn-archive-target" data-id="${rep.id}" style="min-height:32px; padding:0.3rem 0.75rem; font-size:0.8rem; font-weight:600; color:var(--primary); border-color:var(--primary);">📦 Archive Post</button>` : ''}
                    <button type="button" class="btn btn-danger btn-remove-target" data-id="${rep.id}" style="min-height:32px; padding:0.3rem 0.75rem; font-size:0.8rem; font-weight:600;">Remove Content</button>
                </div>
            `;

            // Open post action
            card.querySelectorAll('.btn-open-target-post').forEach(btn => {
                btn.addEventListener('click', () => {
                    const postId = btn.dataset.postId;
                    openReportedPost(postId);
                });
            });

            card.querySelector('.btn-dismiss-report')?.addEventListener('click', () => submitModerationReview(rep.id, 'DISMISSED', false, false));
            card.querySelector('.btn-archive-target')?.addEventListener('click', () => submitModerationReview(rep.id, 'RESOLVED', false, true));
            card.querySelector('.btn-remove-target')?.addEventListener('click', () => submitModerationReview(rep.id, 'RESOLVED', true, false));
            list.appendChild(card);
        });
    } catch (err) {
        list.innerHTML = '<div class="empty-state-card"><p>Error loading reports.</p></div>';
    }
}

async function openReportedPost(postId) {
    if (!postId) return;
    closeAllModals();
    showFeedView();

    let postEl = document.getElementById(`post-${postId}`);
    if (!postEl) {
        // Load feed first if post is not currently visible in DOM
        await loadSocialFeed(1);
        postEl = document.getElementById(`post-${postId}`);
    }

    if (postEl) {
        postEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        postEl.classList.remove('highlight-post-pulse');
        void postEl.offsetWidth;
        postEl.classList.add('highlight-post-pulse');
        setTimeout(() => {
            postEl.classList.remove('highlight-post-pulse');
        }, 5500);
    } else {
        showToast(`Navigated to feed for Post #${postId}.`, 'info');
    }
}

async function submitModerationReview(reportId, status, removeContent, archiveContent = false) {
    try {
        await BalajiAPI.reviewReport(reportId, {
            status,
            remove_content: removeContent,
            archive_content: archiveContent,
            admin_notes: `Processed by administrator (${status}${archiveContent ? ' - Archived' : ''})`
        });
        showToast(`Report ${status.toLowerCase()} successfully.${archiveContent ? ' Post archived.' : ''}`, 'success');
        loadAdminModerationReports();
        loadAdminArchivedPosts();
        loadSocialFeed(1);
    } catch (err) {
        // Handled in apiFetch
    }
}

async function loadAdminArchivedPosts() {
    const list = document.getElementById('admin-archived-list');
    const badge = document.getElementById('badge-admin-archived-count');
    if (!list) return;

    list.innerHTML = '<div class="empty-state-card"><p>Loading archived posts...</p></div>';

    try {
        const res = await BalajiAPI.getArchivedPosts();
        list.innerHTML = '';
        const posts = res.results || res;
        const count = Array.isArray(posts) ? posts.length : 0;
        if (badge) {
            badge.innerText = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }

        if (!posts || posts.length === 0) {
            list.innerHTML = '<div class="empty-state-card"><p>No archived posts in the system.</p></div>';
            return;
        }

        posts.forEach(post => {
            const card = document.createElement('div');
            card.style.border = '1px solid var(--border-light)';
            card.style.borderRadius = 'var(--radius-md)';
            card.style.padding = '0.95rem';
            card.style.backgroundColor = 'var(--bg-card)';
            card.style.boxShadow = '0 2px 8px rgba(0,0,0,0.05)';

            const authorName = post.author_details?.full_name || post.author_details?.username || 'Employee';
            const mediaList = post.media_attachments || [];

            let mediaPreviewHtml = '';
            if (mediaList.length > 0) {
                mediaPreviewHtml = `
                    <div style="display:flex; gap:6px; margin-top:8px; overflow-x:auto;">
                        ${mediaList.map(m => `<img src="${m.file_url}" style="width:68px; height:68px; object-fit:cover; border-radius:6px; border:1px solid var(--border-light);" loading="lazy" alt="Media attachment">`).join('')}
                    </div>
                `;
            }

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <div style="display:flex; align-items:center; gap:0.4rem;">
                        <span style="font-weight:700; font-size:0.9rem; color:var(--text-primary);">${escapeHTML(authorName)}</span>
                        <span class="badge" style="background:#64748b; color:#fff; font-size:0.7rem; padding:1px 6px; border-radius:10px;">📦 Archived</span>
                    </div>
                    <span style="font-size:0.75rem; color:var(--text-muted);">${formatRelativeTime(post.created_at)}</span>
                </div>

                <div style="font-size:0.875rem; color:var(--text-primary); line-height:1.4; word-break:break-word; margin-bottom:0.6rem; background:var(--bg-input); padding:0.6rem; border-radius:6px;">
                    ${escapeHTML(post.content) || '<em style="color:var(--text-muted);">[Media Only]</em>'}
                </div>
                ${mediaPreviewHtml}

                <div style="display:flex; gap:0.5rem; justify-content:flex-end; margin-top:0.75rem;">
                    <button type="button" class="btn btn-primary btn-unarchive-post" data-id="${post.id}" style="min-height:32px; padding:0.3rem 0.8rem; font-size:0.8rem; font-weight:700;">
                        ♻️ Restore to Feed
                    </button>
                    <button type="button" class="btn btn-danger btn-delete-archived-post" data-id="${post.id}" style="min-height:32px; padding:0.3rem 0.8rem; font-size:0.8rem; font-weight:700;">
                        🗑️ Delete
                    </button>
                </div>
            `;

            card.querySelector('.btn-unarchive-post')?.addEventListener('click', async () => {
                try {
                    await BalajiAPI.unarchivePost(post.id);
                    showToast(`Post #${post.id} restored to public feed.`, 'success');
                    loadAdminArchivedPosts();
                    loadSocialFeed(1);
                } catch (e) {}
            });

            card.querySelector('.btn-delete-archived-post')?.addEventListener('click', async () => {
                if (!confirm(`Are you sure you want to permanently delete post #${post.id}?`)) return;
                try {
                    await BalajiAPI.deletePost(post.id);
                    showToast(`Post #${post.id} permanently deleted.`, 'success');
                    loadAdminArchivedPosts();
                } catch (e) {}
            });

            list.appendChild(card);
        });
    } catch (err) {
        list.innerHTML = '<div class="empty-state-card"><p>Error loading archived posts.</p></div>';
    }
}

function setupAdminModalTabs() {
    const tabReports = document.getElementById('tab-btn-admin-reports');
    const tabArchived = document.getElementById('tab-btn-admin-archived');
    const panelReports = document.getElementById('admin-panel-reports');
    const panelArchived = document.getElementById('admin-panel-archived');

    tabReports?.addEventListener('click', () => {
        tabReports.style.color = 'var(--primary)';
        tabReports.style.borderBottom = '2px solid var(--primary)';
        tabReports.style.fontWeight = '700';

        if (tabArchived) {
            tabArchived.style.color = 'var(--text-secondary)';
            tabArchived.style.borderBottom = 'none';
            tabArchived.style.fontWeight = '600';
        }

        if (panelReports) panelReports.style.display = 'block';
        if (panelArchived) panelArchived.style.display = 'none';

        loadAdminModerationReports();
    });

    tabArchived?.addEventListener('click', () => {
        tabArchived.style.color = 'var(--primary)';
        tabArchived.style.borderBottom = '2px solid var(--primary)';
        tabArchived.style.fontWeight = '700';

        if (tabReports) {
            tabReports.style.color = 'var(--text-secondary)';
            tabReports.style.borderBottom = 'none';
            tabReports.style.fontWeight = '600';
        }

        if (panelArchived) panelArchived.style.display = 'block';
        if (panelReports) panelReports.style.display = 'none';

        loadAdminArchivedPosts();
    });
}

// -------------------------------------------------------------
// PROFILE & SECURITY (Change Password & Logout)
// -------------------------------------------------------------
function setupProfileAndSecurity() {
    const changePwModal = document.getElementById('change-pw-modal');
    document.getElementById('btn-open-change-pw')?.addEventListener('click', () => {
        closeAllModals();
        openModal(changePwModal);
    });

    const changePwForm = document.getElementById('change-pw-form');
    changePwForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const oldPw = document.getElementById('pw-current').value;
        const newPw = document.getElementById('pw-new').value;
        const confirmPw = document.getElementById('pw-confirm').value;

        if (newPw !== confirmPw) {
            showToast('New passwords do not match.', 'error');
            return;
        }

        try {
            await BalajiAPI.changePassword(oldPw, newPw);
            showToast('Password updated successfully.', 'success');
            changePwForm.reset();
            closeAllModals();
        } catch (err) {
            // Handled in apiFetch
        }
    });

    document.getElementById('btn-profile-logout')?.addEventListener('click', () => {
        performSignOut();
    });
}

// -------------------------------------------------------------
// DIRECT MESSAGING HELPER
// -------------------------------------------------------------
function openDirectMessageWith(empId, empName) {
    if (!empId) return;
    if (window.BalajiChat && typeof window.BalajiChat.startWith === 'function') {
        window.BalajiChat.startWith(empId, empName);
    } else if (window.BalajiChat && typeof window.BalajiChat.openConversationWith === 'function') {
        window.BalajiChat.openConversationWith(empId, empName);
    } else {
        const dmsTab = document.querySelector('[data-view="messages"]') || document.getElementById('tab-nav-messages') || document.getElementById('btn-header-messages');
        if (dmsTab) dmsTab.click();
    }
}

// -------------------------------------------------------------
// BIRTHDAY FEATURE
// -------------------------------------------------------------
async function loadBirthdaysBanner() {
    const banner = document.getElementById('birthday-banner');
    const list = document.getElementById('birthday-employees-list');
    if (!banner || !list) return;

    const todayKey = new Date().toDateString();
    const dismissKey = 'balaji_birthday_dismissed_' + todayKey;
    if (sessionStorage.getItem(dismissKey) || localStorage.getItem(dismissKey)) {
        banner.style.display = 'none';
        return;
    }

    const dismissBtn = document.getElementById('btn-dismiss-birthday-banner');
    if (dismissBtn && !dismissBtn.dataset.hooked) {
        dismissBtn.dataset.hooked = 'true';
        dismissBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            banner.style.display = 'none';
            sessionStorage.setItem(dismissKey, '1');
            localStorage.setItem(dismissKey, '1');
        });
    }

    try {
        const birthdays = await BalajiAPI.getBirthdays();
        if (birthdays && birthdays.length > 0) {
            list.innerHTML = '';
            birthdays.forEach(emp => {
                const badge = document.createElement('div');
                badge.className = 'birthday-badge-item';
                badge.style.cursor = 'pointer';
                const init = (emp.first_name?.[0] || emp.employee_id?.[0] || 'B').toUpperCase();
                const avatarMarkup = emp.avatar_url ?
                    `<img src="${emp.avatar_url}" alt="${emp.full_name}" style="width:24px; height:24px; border-radius:50%; object-fit:cover;">` :
                    `<span style="width:24px; height:24px; border-radius:50%; background:var(--primary); color:#fff; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem;">${init}</span>`;
                
                const isSelf = currentUser && currentUser.id === emp.id;
                badge.innerHTML = `
                    ${avatarMarkup}
                    <span style="font-weight:600;">${escapeHTML(emp.full_name)}</span>
                    ${!isSelf ? `<span style="font-size:0.75rem; color:var(--primary); font-weight:600; display:inline-flex; align-items:center; gap:2px; margin-left:4px;">💬 Wish them</span>` : `<span style="font-size:0.75rem; color:var(--text-muted); margin-left:4px;">(You)</span>`}
                `;
                badge.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // Once clicked, immediately disappear from company feed
                    banner.style.display = 'none';
                    sessionStorage.setItem(dismissKey, '1');
                    localStorage.setItem(dismissKey, '1');

                    if (!isSelf) {
                        openDirectMessageWith(emp.id, emp.full_name);
                    } else {
                        openEmployeeProfile(emp.id);
                    }
                });
                list.appendChild(badge);
            });
            banner.style.display = 'block';
        } else {
            banner.style.display = 'none';
        }
    } catch (err) {
        banner.style.display = 'none';
    }
}

// -------------------------------------------------------------
// DEDICATED PROFILE SCREEN & NAVIGATION
// -------------------------------------------------------------
function showFeedView() {
    const profileView = document.getElementById('profile-view-section');
    const feedView = document.getElementById('feed-view-section');
    if (profileView) profileView.style.display = 'none';
    if (feedView) feedView.style.display = 'block';

    const feedTab = document.getElementById('tab-nav-feed');
    if (feedTab) setActiveTab(feedTab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function setupProfileScreen() {
    const backBtn = document.getElementById('btn-back-to-feed');
    backBtn?.addEventListener('click', () => showFeedView());

    const postsSubtab = document.getElementById('btn-subtab-posts');
    const commentsSubtab = document.getElementById('btn-subtab-comments');
    const postsContainer = document.getElementById('profile-posts-container');
    const commentsContainer = document.getElementById('profile-comments-container');

    postsSubtab?.addEventListener('click', () => {
        postsSubtab.classList.add('active');
        commentsSubtab?.classList.remove('active');
        if (postsContainer) postsContainer.style.display = 'flex';
        if (commentsContainer) commentsContainer.style.display = 'none';
        if (currentProfileUser) loadProfilePosts(currentProfileUser.id);
    });

    commentsSubtab?.addEventListener('click', () => {
        commentsSubtab.classList.add('active');
        postsSubtab?.classList.remove('active');
        if (postsContainer) postsContainer.style.display = 'none';
        if (commentsContainer) commentsContainer.style.display = 'flex';
        if (currentProfileUser) loadProfileComments(currentProfileUser.id);
    });

    // Profile actions
    document.getElementById('btn-profile-edit-action')?.addEventListener('click', () => {
        openEditProfileModal();
    });

    document.getElementById('btn-profile-view-full')?.addEventListener('click', () => {
        closeAllModals();
        if (currentUser) openEmployeeProfile(currentUser.id);
    });
}

async function openEmployeeProfile(employeeId) {
    const feedView = document.getElementById('feed-view-section');
    const profileView = document.getElementById('profile-view-section');
    if (!profileView) return;

    closeAllModals();
    if (feedView) feedView.style.display = 'none';
    profileView.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });

    try {
        history.pushState({ screen: 'profile', empId: employeeId }, '', '#profile');
    } catch (_) {}

    try {
        const emp = (currentUser && currentUser.id === employeeId) ?
            currentUser :
            await BalajiAPI.getEmployee(employeeId);
        currentProfileUser = emp;

        // Populate avatar
        const avatarContainer = document.getElementById('profile-avatar-container');
        if (avatarContainer) {
            if (emp.avatar_url) {
                avatarContainer.innerHTML = `<img src="${emp.avatar_url}" alt="${emp.full_name}">`;
            } else {
                const init = (emp.first_name?.[0] || emp.employee_id?.[0] || 'B').toUpperCase();
                avatarContainer.innerHTML = `<span>${init}</span>`;
            }
        }

        // Name & ID (Hide employee_id in frontend)
        const nameEl = document.getElementById('profile-display-name');
        if (nameEl) nameEl.innerText = emp.full_name;

        const idEl = document.getElementById('profile-emp-id');
        if (idEl) {
            idEl.innerText = emp.id;
            idEl.style.display = 'none';
        }

        const deptEl = document.getElementById('profile-dept-pill');
        if (deptEl) deptEl.style.display = 'none';

        // Action buttons
        const isSelf = currentUser && currentUser.id === emp.id;
        const isAdmin = currentUser && currentUser.role === 'ADMIN';
        const canEdit = isSelf || isAdmin;

        // Populate Bio (in place of designation/role)
        const bioEl = document.getElementById('profile-bio-text');
        const bioContainer = document.getElementById('profile-bio-container');
        if (bioEl) {
            if (emp.bio && emp.bio.trim()) {
                bioEl.innerText = emp.bio;
                bioEl.style.display = 'block';
                bioEl.style.color = 'var(--text-primary)';
                bioEl.style.fontStyle = 'normal';
                bioEl.style.cursor = 'default';
                bioEl.onclick = null;
                if (bioContainer) bioContainer.style.display = 'flex';
            } else if (isSelf) {
                bioEl.innerText = '+ Add a bio to tell colleagues about yourself...';
                bioEl.style.color = 'var(--primary)';
                bioEl.style.fontStyle = 'italic';
                bioEl.style.cursor = 'pointer';
                bioEl.style.display = 'block';
                bioEl.onclick = () => openEditProfileModal();
                if (bioContainer) bioContainer.style.display = 'flex';
            } else {
                bioEl.style.display = 'none';
                if (bioContainer) bioContainer.style.display = 'none';
            }
        }

        const editBtn = document.getElementById('btn-profile-edit-action');
        if (editBtn) editBtn.style.display = canEdit ? 'inline-flex' : 'none';

        // Small message icon next to employee name
        const nameMsgBtn = document.getElementById('btn-profile-name-msg');
        if (nameMsgBtn) {
            if (!isSelf) {
                nameMsgBtn.style.display = 'inline-flex';
                nameMsgBtn.onclick = () => openDirectMessageWith(emp.id, emp.full_name);
            } else {
                nameMsgBtn.style.display = 'none';
            }
        }

        // Direct Message button in action bar
        const msgBtn = document.getElementById('btn-profile-message-action') || document.getElementById('btn-profile-dm-action');
        if (msgBtn) {
            if (!isSelf) {
                msgBtn.style.display = 'inline-flex';
                msgBtn.onclick = () => openDirectMessageWith(emp.id, emp.full_name);
            } else {
                msgBtn.style.display = 'none';
            }
        }

        // Reset to Posts subtab
        const postsSubtab = document.getElementById('btn-subtab-posts');
        const commentsSubtab = document.getElementById('btn-subtab-comments');
        const postsContainer = document.getElementById('profile-posts-container');
        const commentsContainer = document.getElementById('profile-comments-container');

        postsSubtab?.classList.add('active');
        commentsSubtab?.classList.remove('active');
        if (postsContainer) postsContainer.style.display = 'flex';
        if (commentsContainer) commentsContainer.style.display = 'none';

        loadProfilePosts(emp.id);

    } catch (err) {
        showToast('Could not load employee profile.', 'error');
    }
}

async function loadProfilePosts(employeeId) {
    const container = document.getElementById('profile-posts-container');
    if (!container) return;

    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '1rem';
    container.innerHTML = '<div class="empty-state-card"><p>Loading posts...</p></div>';

    try {
        const response = await BalajiAPI.getEmployeePosts(employeeId);
        container.innerHTML = '';

        if (!response.results || response.results.length === 0) {
            container.innerHTML = `
                <div class="empty-state-card">
                    <p>No posts published yet by this employee.</p>
                </div>`;
            return;
        }

        response.results.forEach(post => {
            const card = buildPostCardElement(post);
            container.appendChild(card);
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state-card"><p>Error loading posts.</p></div>';
    }
}

async function loadProfileComments(employeeId) {
    const container = document.getElementById('profile-comments-container');
    if (!container) return;

    container.innerHTML = '<div class="empty-state-card"><p>Loading comments...</p></div>';

    try {
        const response = await BalajiAPI.getEmployeeComments(employeeId);
        container.innerHTML = '';

        if (!response.results || response.results.length === 0) {
            container.innerHTML = `
                <div class="empty-state-card">
                    <p>No comments written yet by this employee.</p>
                </div>`;
            return;
        }

        response.results.forEach(comment => {
            const card = document.createElement('div');
            card.className = 'profile-comment-card';
            card.id = `profile-comment-${comment.id}`;

            const relTime = formatRelativeTime(comment.created_at);
            const postSnippet = comment.post_snippet || 'Company Post';

            card.innerHTML = `
                <div class="profile-comment-header">
                    <span>${relTime}</span>
                    ${comment.is_owner ? `
                        <button class="comment-delete-link" data-comment-id="${comment.id}">Delete</button>
                    ` : ''}
                </div>
                <div class="profile-comment-body">
                    ${escapeHTML(comment.content)}
                </div>
                <div class="profile-comment-postlink" title="On post #${comment.post_id}">
                    💬 On: "${escapeHTML(postSnippet)}"
                </div>
            `;

            card.querySelector('.comment-delete-link')?.addEventListener('click', async () => {
                if (!confirm('Are you sure you want to delete this comment?')) return;
                try {
                    await BalajiAPI.deleteComment(comment.id);
                    showToast('Comment deleted.', 'info');
                    card.remove();
                } catch (err) {}
            });

            container.appendChild(card);
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state-card"><p>Error loading comments.</p></div>';
    }
}

// -------------------------------------------------------------
// EDIT PROFILE MODAL CONTROLLER
// -------------------------------------------------------------
function openEditProfileModal() {
    const modal = document.getElementById('edit-profile-modal');
    if (!modal || !currentUser) return;

    // Fill current values
    const displayNameInput = document.getElementById('edit-display-name');
    if (displayNameInput) displayNameInput.value = currentUser.display_name || currentUser.full_name || '';

    const bioInput = document.getElementById('edit-bio');
    if (bioInput) bioInput.value = currentUser.bio || '';

    const dobInput = document.getElementById('edit-date-of-birth');
    if (dobInput) dobInput.value = currentUser.date_of_birth || '';

    const phoneInput = document.getElementById('edit-phone-number');
    if (phoneInput) phoneInput.value = currentUser.phone_number || '';

    updateEditAvatarPreview(currentUser.avatar_url, currentUser.full_name);
    openModal(modal);
}

function updateEditAvatarPreview(avatarUrl, fullName) {
    const previewBox = document.getElementById('edit-avatar-preview-box');
    if (!previewBox) return;

    if (avatarUrl) {
        previewBox.innerHTML = `<img src="${avatarUrl}" alt="${fullName || 'Avatar'}">`;
    } else {
        const init = (fullName?.[0] || 'B').toUpperCase();
        previewBox.innerHTML = `<span>${init}</span>`;
    }
}

function setupEditProfileModal() {
    const fileInput = document.getElementById('edit-avatar-file-input');
    const removeBtn = document.getElementById('btn-remove-avatar');
    const form = document.getElementById('edit-profile-form');

    fileInput?.addEventListener('change', async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Size check (max 5 MB)
        if (file.size > 5 * 1024 * 1024) {
            showToast('Image file exceeds maximum limit of 5 MB.', 'error');
            fileInput.value = '';
            return;
        }

        try {
            showToast('Uploading profile picture...', 'info');
            const result = await BalajiAPI.uploadAvatar(file);
            currentUser.avatar_url = result.avatar_url;
            updateEditAvatarPreview(result.avatar_url, currentUser.full_name);
            setupUserSessionUI(currentUser);
            if (currentProfileUser && currentProfileUser.id === currentUser.id) {
                currentProfileUser.avatar_url = result.avatar_url;
                const pBox = document.getElementById('profile-avatar-container');
                if (pBox) pBox.innerHTML = `<img src="${result.avatar_url}" alt="${currentUser.full_name}">`;
            }
            showToast('Profile picture updated successfully!', 'success');
        } catch (err) {
            // Handled in apiFetch
        } finally {
            fileInput.value = '';
        }
    });

    removeBtn?.addEventListener('click', async () => {
        if (!confirm('Remove your profile picture?')) return;
        try {
            await BalajiAPI.removeAvatar();
            currentUser.avatar_url = '';
            updateEditAvatarPreview('', currentUser.full_name);
            setupUserSessionUI(currentUser);
            if (currentProfileUser && currentProfileUser.id === currentUser.id) {
                currentProfileUser.avatar_url = '';
                const pBox = document.getElementById('profile-avatar-container');
                const init = (currentUser.first_name?.[0] || 'B').toUpperCase();
                if (pBox) pBox.innerHTML = `<span>${init}</span>`;
            }
            showToast('Profile picture removed.', 'info');
        } catch (err) {}
    });

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const saveBtn = document.getElementById('btn-save-profile');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerText = 'Saving...';
        }

        const displayName = document.getElementById('edit-display-name')?.value.trim();
        const bio = document.getElementById('edit-bio')?.value.trim() ?? '';
        const dateOfBirth = document.getElementById('edit-date-of-birth')?.value || null;
        const phone = document.getElementById('edit-phone-number')?.value.trim();

        try {
            const updated = await BalajiAPI.updateProfile({
                display_name: displayName,
                bio: bio,
                date_of_birth: dateOfBirth,
                phone_number: phone
            });

            // Update currentUser state
            currentUser = updated;
            setupUserSessionUI(currentUser);

            // If viewing own profile, refresh details
            if (currentProfileUser && currentProfileUser.id === currentUser.id) {
                currentProfileUser = updated;
                const nameEl = document.getElementById('profile-display-name');
                if (nameEl) nameEl.innerText = updated.full_name;

                const bioEl = document.getElementById('profile-bio-text');
                const bioContainer = document.getElementById('profile-bio-container');
                if (bioEl) {
                    if (updated.bio && updated.bio.trim()) {
                        bioEl.innerText = updated.bio;
                        bioEl.style.display = 'block';
                        bioEl.style.color = 'var(--text-primary)';
                        bioEl.style.fontStyle = 'normal';
                        bioEl.style.cursor = 'default';
                        bioEl.onclick = null;
                        if (bioContainer) bioContainer.style.display = 'flex';
                    } else {
                        bioEl.innerText = '+ Add a bio to tell colleagues about yourself...';
                        bioEl.style.color = 'var(--primary)';
                        bioEl.style.fontStyle = 'italic';
                        bioEl.style.cursor = 'pointer';
                        bioEl.style.display = 'block';
                        bioEl.onclick = () => openEditProfileModal();
                        if (bioContainer) bioContainer.style.display = 'flex';
                    }
                }

                const dobBadge = document.getElementById('profile-dob-badge');
                if (dobBadge) {
                    if (updated.date_of_birth) {
                        dobBadge.style.display = 'inline-flex';
                        dobBadge.innerText = `🎂 DOB: ${updated.date_of_birth}`;
                    } else {
                        dobBadge.style.display = 'none';
                    }
                }
            }

            showToast('Profile updated successfully!', 'success');
            closeAllModals();
        } catch (err) {
            // Handled in apiFetch
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerText = 'Save Changes';
            }
        }
    });
}

// -------------------------------------------------------------
// ACCOUNT OPTIONS TOGGLE MENU (Facebook Pattern)
// -------------------------------------------------------------
function openAccountMenu() {
    const menu = document.getElementById('account-toggle-menu');
    if (!menu || !currentUser) return;

    // Populate user details in menu header
    const nameEl = menu.querySelector('.account-menu-name');
    if (nameEl) nameEl.innerText = currentUser.full_name;

    const subEl = menu.querySelector('.account-menu-sub');
    if (subEl) {
        const dept = currentUser.department_details?.code || currentUser.department_details?.name || 'Balaji Transports';
        subEl.innerHTML = `ID: <span class="user-employee-id">${currentUser.employee_id}</span> • <span class="user-department">${escapeHTML(dept)}</span>`;
    }

    const avatarBox = document.getElementById('account-menu-avatar');
    if (avatarBox) {
        if (currentUser.avatar_url) {
            avatarBox.innerHTML = `<img src="${currentUser.avatar_url}" alt="${currentUser.full_name}" style="width:100%; height:100%; object-fit:cover; border-radius:inherit;">`;
        } else {
            const init = (currentUser.first_name?.[0] || currentUser.employee_id?.[0] || 'B').toUpperCase();
            avatarBox.innerText = init;
        }
    }

    // Reveal admin option if administrator
    if (currentUser.role === 'ADMIN') {
        const adminOpt = document.getElementById('menu-opt-admin');
        if (adminOpt) adminOpt.style.display = 'flex';
    }

    menu.style.display = 'block';
    document.getElementById('tab-nav-profile')?.setAttribute('aria-expanded', 'true');
    document.getElementById('btn-header-profile')?.setAttribute('aria-expanded', 'true');
    document.getElementById('tab-nav-profile')?.classList.add('active');
}

function closeAccountMenu() {
    const menu = document.getElementById('account-toggle-menu');
    if (!menu) return;
    menu.style.display = 'none';
    document.getElementById('tab-nav-profile')?.setAttribute('aria-expanded', 'false');
    document.getElementById('btn-header-profile')?.setAttribute('aria-expanded', 'false');

    // If profile section is not visible, restore active tab to feed
    const profileSection = document.getElementById('profile-view-section');
    if (!profileSection || profileSection.style.display === 'none') {
        const feedTab = document.getElementById('tab-nav-feed');
        if (feedTab) setActiveTab(feedTab);
    }
}

function toggleAccountMenu() {
    const menu = document.getElementById('account-toggle-menu');
    if (!menu) return;
    if (menu.style.display === 'none' || !menu.style.display) {
        openAccountMenu();
    } else {
        closeAccountMenu();
    }
}

function setupAccountToggleMenu() {
    // Menu Options
    document.getElementById('menu-opt-view-profile')?.addEventListener('click', () => {
        closeAccountMenu();
        if (currentUser) openEmployeeProfile(currentUser.id);
    });

    document.getElementById('menu-opt-edit-profile')?.addEventListener('click', () => {
        closeAccountMenu();
        openEditProfileModal();
    });

    document.getElementById('menu-opt-change-pw')?.addEventListener('click', () => {
        closeAccountMenu();
        const modal = document.getElementById('change-pw-modal');
        if (modal) {
            openModal(modal);
            document.getElementById('pw-current')?.focus();
        }
    });

    document.getElementById('menu-opt-admin')?.addEventListener('click', () => {
        closeAccountMenu();
        const modal = document.getElementById('admin-modal');
        if (modal) {
            openModal(modal);
            loadAdminModerationReports();
            loadAdminArchivedPosts();
        }
    });

    document.getElementById('menu-opt-logout')?.addEventListener('click', () => {
        closeAccountMenu();
        performSignOut();
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
        const menu = document.getElementById('account-toggle-menu');
        const toggleTab = document.getElementById('tab-nav-profile');
        const headerProfile = document.getElementById('btn-header-profile');
        const sidebarProfile = document.getElementById('sidebar-nav-profile');

        if (menu && menu.style.display !== 'none') {
            if (!menu.contains(e.target) &&
                !toggleTab?.contains(e.target) &&
                !headerProfile?.contains(e.target) &&
                !sidebarProfile?.contains(e.target)) {
                closeAccountMenu();
            }
        }

        // Close open comment emoji & gif trays when clicking outside
        if (!e.target.closest('.comment-emoji-tray') && !e.target.closest('.btn-comment-emoji')) {
            document.querySelectorAll('.comment-emoji-tray').forEach(tray => {
                if (tray.style.display !== 'none') tray.style.display = 'none';
            });
        }
        if (!e.target.closest('.comment-gif-tray') && !e.target.closest('.btn-comment-gif')) {
            document.querySelectorAll('.comment-gif-tray').forEach(tray => {
                if (tray.style.display !== 'none') tray.style.display = 'none';
            });
        }
    });

    // Close when Escape key is pressed on desktop
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const menu = document.getElementById('account-toggle-menu');
            if (menu && menu.style.display !== 'none') {
                closeAccountMenu();
            }
        }
    });
}

async function performSignOut() {
    if (!confirm('Are you sure you want to sign out of Balaji Connect?')) {
        return;
    }

    try {
        await BalajiAPI.logout();
    } catch (err) {
        console.warn('Logout request completed with notice:', err);
    }

    // Clear session & local storage
    try { sessionStorage.clear(); } catch (_) {}
    try { localStorage.removeItem('auth_token'); } catch (_) {}

    // Invalidate state and cleanly redirect to /logout/ which guarantees server-side cookie deletion
    currentUser = null;
    window.location.replace('/logout/');
}

// -------------------------------------------------------------
// MODAL & UTILITY HELPERS
// -------------------------------------------------------------
function openModal(modal) {
    if (!modal) return;
    modal.classList.add('active');
    const modalId = modal.id || 'dialog';
    try {
        history.pushState({ modal: modalId }, '', '#' + modalId);
    } catch (_) {}
}

function closeAllModals() {
    document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('active'));
    if (window.location.hash && window.location.hash !== '#feed') {
        try {
            history.replaceState({ view: 'feed' }, '', window.location.pathname);
        } catch (_) {}
    }
}

document.querySelectorAll('.modal-close-btn').forEach(btn => {
    btn.addEventListener('click', closeAllModals);
});

// Close modal when tapping backdrop
document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeAllModals();
    });
});

// Global Mobile Back Navigation Handler
// When users swipe back on phone or press the browser back button,
// safely close open modals/chat/stories and return to the company feed instead of exiting the website.
window.addEventListener('popstate', (e) => {
    // 1. If Chat modal is open
    const chatModal = document.getElementById('chat-modal');
    if (chatModal && chatModal.classList.contains('active')) {
        const layout = document.getElementById('chat-modal-layout');
        // If on mobile and in active thread, step back to conversation list
        if (window.innerWidth <= 640 && layout && layout.classList.contains('active-chat')) {
            const backBtn = document.getElementById('btn-chat-back-to-list');
            if (backBtn && backBtn.style.display !== 'none') {
                backBtn.click();
                return;
            }
        }
        if (window.BalajiChat && typeof window.BalajiChat.close === 'function') {
            window.BalajiChat.close();
        }
        showFeedView();
        return;
    }

    // 2. If Story Viewer is open, close it cleanly
    const storyViewer = document.getElementById('story-viewer-modal');
    if (storyViewer && storyViewer.style.display !== 'none') {
        closeStoryViewer();
        showFeedView();
        return;
    }

    // 3. Close any open dialogs/modals
    document.querySelectorAll('.modal-backdrop.active').forEach(m => m.classList.remove('active'));

    // 4. Close account menu dropdown
    const accountMenu = document.getElementById('account-toggle-menu');
    if (accountMenu && accountMenu.style.display !== 'none') {
        if (typeof closeAccountMenu === 'function') closeAccountMenu();
    }

    // 5. Always safely redirect to the company feed
    showFeedView();
});

// Initialize base history state on startup with back-stop
try {
    if (!history.state || history.state.view !== 'feed') {
        history.replaceState({ view: 'feed' }, '', window.location.pathname);
    }
} catch (_) {}

// -------------------------------------------------------------
// EPHEMERAL 12-HOUR STORIES FEATURE CONTROLLER
// -------------------------------------------------------------
let storiesFeed = [];
let currentStoryGroupIndex = 0;
let currentStoryItemIndex = 0;
let storyTimer = null;
let storyProgressInterval = null;
let storyStartTime = 0;
let storyDurationMs = 5000;
let isStoryPaused = false;
let pendingStoryFile = null;
let activeStoryMode = 'media'; // 'media' or 'text'
let activeStoryGradient = 'gradient-blue';

async function loadStoriesTray() {
    const colleaguesContainer = document.getElementById('colleagues-stories-container');
    const myRing = document.getElementById('my-story-ring');
    const myBadge = document.getElementById('my-story-add-badge');
    const myLabel = document.getElementById('my-story-tray-label');
    const myAvatarBox = document.getElementById('my-story-avatar-box');

    if (!currentUser) return;

    // Hydrate current user's avatar in tray
    if (myAvatarBox) {
        if (currentUser.avatar_url) {
            myAvatarBox.innerHTML = `<img src="${currentUser.avatar_url}" alt="${escapeHTML(currentUser.full_name)}">`;
        } else {
            const init = (currentUser.first_name?.[0] || 'B').toUpperCase();
            myAvatarBox.innerText = init;
        }
    }

    try {
        storiesFeed = await BalajiAPI.getStories();
        if (!Array.isArray(storiesFeed)) storiesFeed = [];

        // Check if current user has an active story
        const myStoryGroupIndex = storiesFeed.findIndex(g => {
            const authorId = g.author?.id ?? g.author_id;
            return authorId === currentUser.id;
        });
        const myStoryGroup = myStoryGroupIndex !== -1 ? storiesFeed[myStoryGroupIndex] : null;

        if (myStoryGroup && myStoryGroup.stories && myStoryGroup.stories.length > 0) {
            myRing?.classList.add('has-story');
            if (myStoryGroup.has_unseen) {
                myRing?.classList.add('has-unseen');
                myRing?.classList.remove('all-seen');
            } else {
                myRing?.classList.add('all-seen');
                myRing?.classList.remove('has-unseen');
            }
            if (myBadge) myBadge.style.display = 'none';
            if (myLabel) myLabel.innerText = 'Your Story';
        } else {
            myRing?.classList.remove('has-story', 'has-unseen', 'all-seen');
            if (myBadge) myBadge.style.display = 'flex';
            if (myLabel) myLabel.innerText = 'Add Story';
        }

        // Render colleagues' stories (filter out current user from the right side)
        if (colleaguesContainer) {
            colleaguesContainer.innerHTML = '';
            storiesFeed.forEach((group, index) => {
                const authorId = group.author?.id ?? group.author_id;
                if (authorId === currentUser.id) return; // Shown in "Your Story" slot
                if (!group.stories || group.stories.length === 0) return;

                const authorName = group.author?.full_name || group.author_name || 'Colleague';
                const authorFirst = group.author?.first_name || authorName.split(' ')[0] || authorName;
                const authorAvatar = group.author?.avatar_url || group.author_avatar;
                const ringClass = group.has_unseen ? 'has-unseen' : 'all-seen';
                const initial = (authorFirst[0] || 'B').toUpperCase();
                const avatarMarkup = authorAvatar ?
                    `<img src="${authorAvatar}" alt="${escapeHTML(authorName)}">` :
                    `<span>${initial}</span>`;

                const item = document.createElement('div');
                item.className = 'story-tray-item';
                item.title = `${authorName}'s Story`;
                item.innerHTML = `
                    <div class="story-avatar-ring ${ringClass}">
                        <div class="avatar-round story-avatar">${avatarMarkup}</div>
                    </div>
                    <span class="story-tray-name">${escapeHTML(authorFirst)}</span>
                `;
                item.addEventListener('click', () => {
                    openStoryViewer(index, 0);
                });
                colleaguesContainer.appendChild(item);
            });
        }
    } catch (err) {
        console.warn('Could not load stories tray:', err);
    }
}

function setupStoriesFeature() {
    loadStoriesTray();

    // User Story Slot click
    const userSlot = document.getElementById('btn-user-story-slot');
    userSlot?.addEventListener('click', (e) => {
        // If clicking on the "+" badge directly, or if user has no story, open creator
        const myIndex = storiesFeed.findIndex(g => {
            const authorId = g.author?.id ?? g.author_id;
            return authorId === currentUser.id;
        });
        const myGroup = myIndex !== -1 ? storiesFeed[myIndex] : null;

        if (e.target.closest('#my-story-add-badge') || !myGroup || !myGroup.stories || myGroup.stories.length === 0) {
            openStoryCreator();
        } else {
            // View own story
            openStoryViewer(myIndex, 0);
        }
    });

    // Story Creator Modal
    setupStoryCreator();

    // Story Viewer Modal controls
    setupStoryViewerControls();
}

function openStoryCreator() {
    const modal = document.getElementById('story-creator-modal');
    resetStoryCreator();
    if (modal) openModal(modal);
}

function resetStoryCreator() {
    activeStoryMode = 'media';
    activeStoryGradient = 'gradient-blue';
    pendingStoryFile = null;

    const fileInput = document.getElementById('story-file-input');
    if (fileInput) fileInput.value = '';
    const captionInput = document.getElementById('story-caption-input');
    if (captionInput) captionInput.value = '';
    const textInput = document.getElementById('story-text-input');
    if (textInput) textInput.value = '';
    const textCharCount = document.getElementById('story-text-char-count');
    if (textCharCount) textCharCount.innerText = '0';
    const textCanvasContent = document.getElementById('story-text-canvas-content');
    if (textCanvasContent) textCanvasContent.innerText = 'Type a status...';
    const textCanvasPreview = document.getElementById('story-text-canvas-preview');
    if (textCanvasPreview) textCanvasPreview.className = 'story-text-canvas-preview gradient-blue';

    // Reset color dots
    document.querySelectorAll('.story-color-dot').forEach((dot, idx) => {
        if (idx === 0) dot.classList.add('active');
        else dot.classList.remove('active');
    });

    // Reset tabs
    const tabMedia = document.getElementById('tab-story-media');
    const tabText = document.getElementById('tab-story-text');
    const mediaSection = document.getElementById('story-media-mode-section');
    const textSection = document.getElementById('story-text-mode-section');
    if (tabMedia) tabMedia.className = 'btn btn-primary story-mode-tab active';
    if (tabText) tabText.className = 'btn btn-secondary story-mode-tab';
    if (mediaSection) mediaSection.style.display = 'block';
    if (textSection) textSection.style.display = 'none';

    const placeholder = document.getElementById('story-upload-placeholder');
    const previewContainer = document.getElementById('story-media-preview-container');
    const previewBox = document.getElementById('story-media-preview-box');
    const publishBtn = document.getElementById('btn-publish-story');

    if (placeholder) placeholder.style.display = 'flex';
    if (previewContainer) previewContainer.style.display = 'none';
    if (previewBox) previewBox.innerHTML = '';
    if (publishBtn) {
        publishBtn.disabled = true;
        publishBtn.innerText = 'Share Story';
    }
}

function setupStoryCreator() {
    const tabMedia = document.getElementById('tab-story-media');
    const tabText = document.getElementById('tab-story-text');
    const mediaSection = document.getElementById('story-media-mode-section');
    const textSection = document.getElementById('story-text-mode-section');
    const textInput = document.getElementById('story-text-input');
    const textCharCount = document.getElementById('story-text-char-count');
    const textCanvasPreview = document.getElementById('story-text-canvas-preview');
    const textCanvasContent = document.getElementById('story-text-canvas-content');
    const paletteDots = document.querySelectorAll('.story-color-dot');
    const browseBtn = document.getElementById('btn-browse-story-media');
    const fileInput = document.getElementById('story-file-input');
    const dropZone = document.getElementById('story-upload-zone');
    const removeBtn = document.getElementById('btn-remove-story-media');
    const form = document.getElementById('story-creator-form');
    const publishBtn = document.getElementById('btn-publish-story');

    // Tab switcher: Photo/Video vs Text Status
    tabMedia?.addEventListener('click', () => {
        activeStoryMode = 'media';
        tabMedia.className = 'btn btn-primary story-mode-tab active';
        if (tabText) tabText.className = 'btn btn-secondary story-mode-tab';
        if (mediaSection) mediaSection.style.display = 'block';
        if (textSection) textSection.style.display = 'none';
        if (publishBtn) {
            publishBtn.disabled = !pendingStoryFile;
            publishBtn.innerText = 'Share Story';
        }
    });

    tabText?.addEventListener('click', () => {
        activeStoryMode = 'text';
        tabText.className = 'btn btn-primary story-mode-tab active';
        if (tabMedia) tabMedia.className = 'btn btn-secondary story-mode-tab';
        if (mediaSection) mediaSection.style.display = 'none';
        if (textSection) textSection.style.display = 'block';
        if (publishBtn) {
            const hasText = !!textInput?.value.trim();
            publishBtn.disabled = !hasText;
            publishBtn.innerText = 'Share Text Story';
        }
        textInput?.focus();
    });

    // Text story live input & char counter
    textInput?.addEventListener('input', () => {
        const val = textInput.value;
        if (textCharCount) textCharCount.innerText = val.length;
        if (textCanvasContent) {
            textCanvasContent.innerText = val.trim() ? val : 'Type a status...';
        }
        if (publishBtn && activeStoryMode === 'text') {
            publishBtn.disabled = !val.trim();
        }
    });

    // Gradient background palette
    paletteDots.forEach(dot => {
        dot.addEventListener('click', () => {
            paletteDots.forEach(d => d.classList.remove('active'));
            dot.classList.add('active');
            const color = dot.dataset.color || 'gradient-blue';
            activeStoryGradient = color;
            if (textCanvasPreview) {
                textCanvasPreview.className = `story-text-canvas-preview ${color}`;
            }
        });
    });

    browseBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput?.click();
    });

    dropZone?.addEventListener('click', () => {
        if (!pendingStoryFile) fileInput?.click();
    });

    removeBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        resetStoryCreator();
    });

    fileInput?.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (file) handleStoryFileSelection(file);
    });

    // Drag & drop
    dropZone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
    });
    dropZone?.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '';
    });
    dropZone?.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '';
        const file = e.dataTransfer?.files?.[0];
        if (file) handleStoryFileSelection(file);
    });

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Mode 1: Text Story Submission
        if (activeStoryMode === 'text') {
            const text = textInput?.value.trim();
            if (!text) {
                showToast('Please type a text status for your story.', 'warning');
                return;
            }

            if (publishBtn) {
                publishBtn.disabled = true;
                publishBtn.innerText = 'Publishing...';
            }

            try {
                showToast('Publishing text story (12-hour status)...', 'info');
                await BalajiAPI.createStory(null, text, activeStoryGradient);
                showToast('Text story published! Visible across the company for 12 hours.', 'success');
                closeAllModals();
                resetStoryCreator();
                await loadStoriesTray();
            } catch (err) {
                showToast(err.message || 'Failed to publish text story.', 'error');
            } finally {
                if (publishBtn) {
                    publishBtn.disabled = false;
                    publishBtn.innerText = 'Share Text Story';
                }
            }
            return;
        }

        // Mode 2: Media Story Submission (Photo/Video)
        if (!pendingStoryFile) {
            showToast('Please select a photo or video for your story.', 'warning');
            return;
        }

        if (publishBtn) {
            publishBtn.disabled = true;
            publishBtn.innerText = 'Publishing...';
        }

        const caption = document.getElementById('story-caption-input')?.value.trim() || '';

        try {
            showToast('Uploading story (12-hour status)...', 'info');
            await BalajiAPI.createStory(pendingStoryFile, caption);
            showToast('Story published! Available for 12 hours.', 'success');
            closeAllModals();
            resetStoryCreator();
            await loadStoriesTray();
        } catch (err) {
            showToast(err.message || 'Failed to upload story.', 'error');
        } finally {
            if (publishBtn) {
                publishBtn.disabled = false;
                publishBtn.innerText = 'Share Story';
            }
        }
    });
}

function handleStoryFileSelection(file) {
    if (file.size > 25 * 1024 * 1024) {
        showToast('Story media must not exceed 25MB.', 'error');
        return;
    }

    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');

    if (!isImage && !isVideo) {
        showToast('Only JPEG, PNG, WEBP, GIF, and MP4 videos are supported.', 'error');
        return;
    }

    pendingStoryFile = file;
    const url = URL.createObjectURL(file);
    const placeholder = document.getElementById('story-upload-placeholder');
    const previewContainer = document.getElementById('story-media-preview-container');
    const previewBox = document.getElementById('story-media-preview-box');
    const publishBtn = document.getElementById('btn-publish-story');

    if (placeholder) placeholder.style.display = 'none';
    if (previewContainer) previewContainer.style.display = 'flex';
    if (previewBox) {
        if (isImage) {
            previewBox.innerHTML = `<img src="${url}" alt="Story preview">`;
        } else {
            previewBox.innerHTML = `<video src="${url}" controls autoplay muted playsinline></video>`;
        }
    }
    if (publishBtn) publishBtn.disabled = false;
}

// -------------------------------------------------------------
// STORY VIEWER CONTROLLER (Fullscreen Player)
// -------------------------------------------------------------
function setupStoryViewerControls() {
    const viewer = document.getElementById('story-viewer-modal');
    const closeBtn = document.getElementById('btn-close-story-viewer');
    const tapPrev = document.getElementById('story-tap-prev');
    const tapNext = document.getElementById('story-tap-next');
    const deleteBtn = document.getElementById('btn-delete-active-story');
    const viewersPill = document.getElementById('btn-toggle-story-viewers');
    const closeSheetBtn = document.getElementById('btn-close-viewers-sheet');

    closeBtn?.addEventListener('click', closeStoryViewer);
    tapPrev?.addEventListener('click', prevStoryItem);
    tapNext?.addEventListener('click', nextStoryItem);

    deleteBtn?.addEventListener('click', async () => {
        const group = storiesFeed[currentStoryGroupIndex];
        const story = group?.stories?.[currentStoryItemIndex];
        if (!story) return;

        if (!confirm('Delete this story? It will be permanently removed.')) return;

        pauseStoryTimer();
        try {
            await BalajiAPI.deleteStory(story.id);
            showToast('Story deleted.', 'info');

            // Remove story from local cache
            group.stories.splice(currentStoryItemIndex, 1);
            if (group.stories.length === 0) {
                storiesFeed.splice(currentStoryGroupIndex, 1);
                closeStoryViewer();
            } else {
                if (currentStoryItemIndex >= group.stories.length) {
                    currentStoryItemIndex = group.stories.length - 1;
                }
                renderActiveStory();
            }
            loadStoriesTray();
        } catch (err) {
            showToast(err.message || 'Failed to delete story.', 'error');
            resumeStoryTimer();
        }
    });

    viewersPill?.addEventListener('click', () => {
        toggleStoryViewersSheet();
    });

    closeSheetBtn?.addEventListener('click', () => {
        const sheet = document.getElementById('story-viewers-sheet');
        if (sheet) sheet.style.display = 'none';
        resumeStoryTimer();
    });
}

function openStoryViewer(groupIndex, storyIndex = 0) {
    if (!storiesFeed || storiesFeed.length === 0) return;
    currentStoryGroupIndex = Math.max(0, Math.min(groupIndex, storiesFeed.length - 1));
    currentStoryItemIndex = storyIndex;

    const viewer = document.getElementById('story-viewer-modal');
    if (!viewer) return;

    viewer.style.display = 'flex';
    try {
        history.pushState({ modal: 'story-viewer' }, '', '#story');
    } catch (_) {}

    renderActiveStory();
}

function closeStoryViewer() {
    clearTimeout(storyTimer);
    clearInterval(storyProgressInterval);
    const viewer = document.getElementById('story-viewer-modal');
    if (viewer) viewer.style.display = 'none';

    const sheet = document.getElementById('story-viewers-sheet');
    if (sheet) sheet.style.display = 'none';

    // Stop any playing video
    const mediaDisplay = document.getElementById('story-media-display');
    if (mediaDisplay) {
        const vid = mediaDisplay.querySelector('video');
        if (vid) {
            vid.pause();
            vid.src = '';
        }
        mediaDisplay.innerHTML = '';
    }

    if (window.location.hash === '#story') {
        try {
            history.replaceState({ view: 'feed' }, '', window.location.pathname);
        } catch (_) {}
    }

    loadStoriesTray();
}

function renderActiveStory() {
    clearTimeout(storyTimer);
    clearInterval(storyProgressInterval);

    const group = storiesFeed[currentStoryGroupIndex];
    if (!group || !group.stories || group.stories.length === 0) {
        closeStoryViewer();
        return;
    }

    if (currentStoryItemIndex < 0) currentStoryItemIndex = 0;
    if (currentStoryItemIndex >= group.stories.length) {
        // Advanced past author's last story: advance to next group
        if (currentStoryGroupIndex < storiesFeed.length - 1) {
            currentStoryGroupIndex++;
            currentStoryItemIndex = 0;
            renderActiveStory();
            return;
        } else {
            closeStoryViewer();
            return;
        }
    }

    const story = group.stories[currentStoryItemIndex];
    const authorId = group.author?.id ?? group.author_id;
    const authorName = group.author?.full_name || group.author_name || 'Balaji Employee';
    const authorFirst = group.author?.first_name || authorName.split(' ')[0] || authorName;
    const authorAvatar = group.author?.avatar_url || group.author_avatar;
    const isOwner = currentUser && authorId === currentUser.id;
    const isAdmin = currentUser && (currentUser.role === 'ADMIN' || currentUser.role === 'SUPER_ADMIN');

    // 1. Render Segment Progress Bars
    const progressBarsContainer = document.getElementById('story-progress-bars');
    if (progressBarsContainer) {
        progressBarsContainer.innerHTML = '';
        group.stories.forEach((_, sIdx) => {
            const seg = document.createElement('div');
            seg.className = 'story-progress-seg';
            const fill = document.createElement('div');
            fill.className = 'story-progress-fill';
            fill.id = `story-prog-fill-${sIdx}`;
            if (sIdx < currentStoryItemIndex) {
                fill.classList.add('filled');
            }
            seg.appendChild(fill);
            progressBarsContainer.appendChild(seg);
        });
    }

    // 2. Render Header
    const avatarEl = document.getElementById('story-header-avatar');
    const nameEl = document.getElementById('story-header-name');
    const timeEl = document.getElementById('story-header-time');
    const deleteBtn = document.getElementById('btn-delete-active-story');

    if (avatarEl) {
        if (authorAvatar) {
            avatarEl.innerHTML = `<img src="${authorAvatar}" alt="${escapeHTML(authorName)}">`;
        } else {
            const init = (authorFirst[0] || 'B').toUpperCase();
            avatarEl.innerText = init;
        }
    }
    if (nameEl) nameEl.innerText = authorName;
    if (timeEl) timeEl.innerText = formatRelativeTime(story.created_at);

    if (deleteBtn) {
        deleteBtn.style.display = (isOwner || isAdmin) ? 'flex' : 'none';
    }

    // 3. Render Media & Caption
    const mediaDisplay = document.getElementById('story-media-display');
    const captionOverlay = document.getElementById('story-caption-overlay');

    if (captionOverlay) {
        if (story.caption && story.caption.trim()) {
            captionOverlay.innerText = story.caption;
            captionOverlay.style.display = 'block';
        } else {
            captionOverlay.style.display = 'none';
        }
    }

    storyDurationMs = 5000; // default 5s for images

    if (mediaDisplay) {
        mediaDisplay.innerHTML = '';
        if (story.media_type === 'VIDEO') {
            const video = document.createElement('video');
            video.src = story.media_url;
            video.autoplay = true;
            video.playsInline = true;
            video.muted = false;
            video.controls = false;
            video.style.maxWidth = '100%';
            video.style.maxHeight = '100%';

            video.onloadedmetadata = () => {
                if (video.duration && !isNaN(video.duration) && video.duration > 0) {
                    storyDurationMs = Math.min(Math.round(video.duration * 1000), 20000);
                }
                startStoryProgressAnimation(storyDurationMs);
            };
            video.onerror = () => {
                startStoryProgressAnimation(5000);
            };
            mediaDisplay.appendChild(video);
            video.play().catch(() => {
                video.muted = true;
                video.play();
            });
        } else if (story.media_type === 'TEXT') {
            const slide = document.createElement('div');
            const bgClass = story.background || 'gradient-blue';
            slide.className = `story-text-slide ${bgClass}`;
            slide.innerHTML = `<div class="story-text-slide-content">${escapeHTML(story.caption || '')}</div>`;
            mediaDisplay.appendChild(slide);
            if (captionOverlay) captionOverlay.style.display = 'none';
            startStoryProgressAnimation(5000);
        } else {
            const img = document.createElement('img');
            img.src = story.media_url;
            img.alt = 'Story media';
            mediaDisplay.appendChild(img);
            startStoryProgressAnimation(5000);
        }
    }

    // 4. Viewers pill & sheet for author
    const footerBar = document.getElementById('story-footer-bar');
    const viewsCountText = document.getElementById('story-views-count-text');
    if (footerBar) {
        if (isOwner) {
            footerBar.style.display = 'flex';
            if (viewsCountText) {
                const count = story.seen_by_count || 0;
                viewsCountText.innerText = `${count} ${count === 1 ? 'view' : 'views'}`;
            }
        } else {
            footerBar.style.display = 'none';
            // Mark as viewed for viewer
            if (!story.has_seen) {
                story.has_seen = true;
                group.has_unseen = group.stories.some(s => !s.has_seen);
                BalajiAPI.recordStoryView(story.id);
            }
        }
    }

    // Hide sheet on slide change
    const sheet = document.getElementById('story-viewers-sheet');
    if (sheet) sheet.style.display = 'none';
}

function startStoryProgressAnimation(durationMs) {
    clearTimeout(storyTimer);
    clearInterval(storyProgressInterval);

    storyStartTime = Date.now();
    storyDurationMs = durationMs;
    const fillEl = document.getElementById(`story-prog-fill-${currentStoryItemIndex}`);

    storyProgressInterval = setInterval(() => {
        if (isStoryPaused) return;
        const elapsed = Date.now() - storyStartTime;
        const pct = Math.min(100, (elapsed / storyDurationMs) * 100);
        if (fillEl) fillEl.style.width = `${pct}%`;
    }, 40);

    storyTimer = setTimeout(() => {
        clearInterval(storyProgressInterval);
        if (fillEl) fillEl.style.width = '100%';
        nextStoryItem();
    }, durationMs);
}

function pauseStoryTimer() {
    isStoryPaused = true;
    clearTimeout(storyTimer);
    clearInterval(storyProgressInterval);
    const vid = document.getElementById('story-media-display')?.querySelector('video');
    if (vid) vid.pause();
}

function resumeStoryTimer() {
    isStoryPaused = false;
    const vid = document.getElementById('story-media-display')?.querySelector('video');
    if (vid) vid.play().catch(() => {});
    startStoryProgressAnimation(storyDurationMs);
}

function prevStoryItem() {
    if (currentStoryItemIndex > 0) {
        currentStoryItemIndex--;
        renderActiveStory();
    } else if (currentStoryGroupIndex > 0) {
        currentStoryGroupIndex--;
        const prevGroup = storiesFeed[currentStoryGroupIndex];
        currentStoryItemIndex = prevGroup.stories.length - 1;
        renderActiveStory();
    } else {
        renderActiveStory(); // Restart current story
    }
}

function nextStoryItem() {
    const group = storiesFeed[currentStoryGroupIndex];
    if (group && currentStoryItemIndex < group.stories.length - 1) {
        currentStoryItemIndex++;
        renderActiveStory();
    } else if (currentStoryGroupIndex < storiesFeed.length - 1) {
        currentStoryGroupIndex++;
        currentStoryItemIndex = 0;
        renderActiveStory();
    } else {
        closeStoryViewer();
    }
}

function toggleStoryViewersSheet() {
    const sheet = document.getElementById('story-viewers-sheet');
    if (!sheet) return;

    if (sheet.style.display === 'flex') {
        sheet.style.display = 'none';
        resumeStoryTimer();
    } else {
        pauseStoryTimer();
        sheet.style.display = 'flex';

        const group = storiesFeed[currentStoryGroupIndex];
        const story = group?.stories?.[currentStoryItemIndex];
        const countSpan = document.getElementById('story-sheet-count');
        const listContainer = document.getElementById('story-viewers-list');

        if (countSpan) countSpan.innerText = story?.seen_by_count ?? story?.view_count ?? 0;
        if (listContainer) {
            if (!story?.viewers || story.viewers.length === 0) {
                listContainer.innerHTML = '<div style="padding:1.5rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">No views yet.</div>';
            } else {
                listContainer.innerHTML = '';
                story.viewers.forEach(v => {
                    const viewer = v.viewer || v;
                    const vName = viewer.full_name || viewer.username || 'Colleague';
                    const init = (viewer.first_name?.[0] || vName[0] || 'B').toUpperCase();
                    const avatarMarkup = viewer.avatar_url ?
                        `<img src="${viewer.avatar_url}" alt="${escapeHTML(vName)}">` :
                        `<span>${init}</span>`;

                    const row = document.createElement('div');
                    row.className = 'story-viewer-row';
                    row.innerHTML = `
                        <div class="avatar-round avatar-sm" style="width:34px; height:34px; min-width:34px; font-size:0.85rem;">${avatarMarkup}</div>
                        <div style="flex:1;">
                            <div class="story-viewer-name">${escapeHTML(vName)}</div>
                            <div class="story-viewer-time">${formatRelativeTime(v.viewed_at)}</div>
                        </div>
                    `;
                    listContainer.appendChild(row);
                });
            }
        }
    }
}

// Relative Time Formatter (Facebook Style)
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    if (diffSeconds < 60) return 'Just now';
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function escapeHTML(str) {
    if (!str) return '';
    return String(str).replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
