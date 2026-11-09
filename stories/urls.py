from django.urls import path
from .views import StoryFeedView, StoryRecordViewView, StoryDetailView

urlpatterns = [
    path('stories/', StoryFeedView.as_view(), name='story-feed'),
    path('stories/<int:pk>/', StoryDetailView.as_view(), name='story-detail'),
    path('stories/<int:pk>/view/', StoryRecordViewView.as_view(), name='story-record-view'),
]

