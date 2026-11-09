from django.urls import path
from .views import (
    ConversationListCreateView,
    ConversationDetailView,
    MessageListCreateView,
    MarkConversationReadView,
    SharePostToDirectMessageView,
)

app_name = 'chat'

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list-create'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('conversations/<int:conversation_id>/read/', MarkConversationReadView.as_view(), name='conversation-mark-read'),
    path('share-post/', SharePostToDirectMessageView.as_view(), name='share-post'),
]

