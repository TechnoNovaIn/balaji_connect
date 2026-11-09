from django.urls import path
from .views import MediaUploadView, MediaStreamView, MediaDetailView

urlpatterns = [
    path('upload/', MediaUploadView.as_view(), name='media-upload'),
    path('<int:pk>/', MediaDetailView.as_view(), name='media-detail'),
    path('<int:pk>/view/', MediaStreamView.as_view(), name='media-view'),
]

