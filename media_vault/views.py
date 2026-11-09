from django.http import StreamingHttpResponse, Http404
from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from accounts.permissions import IsActiveEmployee
from .models import MediaAttachment
from .serializers import MediaAttachmentSerializer, MediaUploadSerializer
from .services import get_storage_service, StorageFileNotFoundException, StorageException

class MediaUploadView(views.APIView):
    permission_classes = [IsActiveEmployee]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            serializer = MediaUploadSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            attachment = serializer.save()

            data = MediaAttachmentSerializer(attachment, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)
        except StorageException as e:
            return Response(
                {"detail": f"Storage upload failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MediaStreamView(views.APIView):
    """
    Authenticated media streaming endpoint.
    Verifies that the requester is an active employee.
    Streams media content directly from the underlying storage driver without exposing
    storage keys, Google Drive URLs, or raw storage paths to the client.
    """
    permission_classes = [IsActiveEmployee]

    def get(self, request, pk):
        try:
            attachment = MediaAttachment.objects.get(pk=pk, is_deleted=False)
        except MediaAttachment.DoesNotExist:
            raise Http404("Media attachment not found or has been removed.")

        storage = get_storage_service(attachment.storage_provider)

        try:
            stream_gen, content_type, content_size = storage.get_file_stream(attachment.storage_file_id)
        except StorageFileNotFoundException:
            raise Http404("Stored media file is no longer available.")
        except StorageException as e:
            return Response(
                {"detail": "Error retrieving media stream."},
                status=status.HTTP_502_BAD_GATEWAY
            )

        response = StreamingHttpResponse(stream_gen, content_type=content_type or attachment.mime_type)
        if content_size:
            response['Content-Length'] = str(content_size)

        response['Content-Disposition'] = f'inline; filename="{attachment.original_filename}"'
        response['Cache-Control'] = 'private, max-age=3600'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class MediaDetailView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def get(self, request, pk):
        try:
            attachment = MediaAttachment.objects.get(pk=pk, is_deleted=False)
        except MediaAttachment.DoesNotExist:
            raise Http404("Media attachment not found.")

        serializer = MediaAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data)
