import io
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Employee, Department
from media_vault.models import MediaAttachment
from .models import Post, PostReaction, Comment

def create_image_attachment(uploader):
    return MediaAttachment.objects.create(
        uploader=uploader,
        storage_provider='local',
        storage_file_id='test-uuid.png',
        original_filename='pic.png',
        file_type='IMAGE',
        mime_type='image/png',
        file_size_bytes=1024,
        file_hash='testhash1234'
    )

class PostFeatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = Department.objects.create(name="Logistics", code="LOG")

        self.author = Employee.objects.create_user(
            employee_id="BT-3001",
            first_name="Anil",
            last_name="Sharma",
            password="Password123!",
            department=self.dept
        )

        self.colleague = Employee.objects.create_user(
            employee_id="BT-3002",
            first_name="Pooja",
            last_name="Patel",
            password="Password123!",
            department=self.dept
        )

        self.admin = Employee.objects.create_superuser(
            employee_id="BT-0001",
            first_name="Admin",
            last_name="User",
            password="AdminPassword123!",
            role=Employee.Role.ADMIN
        )

    def test_create_text_post_success(self):
        self.client.force_authenticate(user=self.author)
        url = reverse('post-list')
        response = self.client.post(url, {'content': 'Our fleet completed 500 deliveries today!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().author, self.author)

    def test_create_media_post_success(self):
        self.client.force_authenticate(user=self.author)
        media = create_image_attachment(self.author)

        url = reverse('post-list')
        response = self.client.post(url, {
            'content': 'Check out the new electric trucks',
            'media_ids': [media.id]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.first()
        self.assertEqual(post.media_attachments.count(), 1)

    def test_empty_post_rejected(self):
        self.client.force_authenticate(user=self.author)
        url = reverse('post-list')
        response = self.client.post(url, {'content': '   ', 'media_ids': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feed_chronological_ordering(self):
        self.client.force_authenticate(user=self.colleague)
        p1 = Post.objects.create(author=self.author, content="First post")
        p2 = Post.objects.create(author=self.author, content="Second post")

        url = reverse('post-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Newest post first
        results = response.data['results']
        self.assertEqual(results[0]['id'], p2.id)
        self.assertEqual(results[1]['id'], p1.id)

    def test_non_author_cannot_edit_post(self):
        post = Post.objects.create(author=self.author, content="Original content")
        self.client.force_authenticate(user=self.colleague)

        url = reverse('post-detail', kwargs={'pk': post.pk})
        response = self.client.patch(url, {'content': 'Hacked content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_edit_post(self):
        post = Post.objects.create(author=self.author, content="Original content")
        self.client.force_authenticate(user=self.author)

        url = reverse('post-detail', kwargs={'pk': post.pk})
        response = self.client.patch(url, {'content': 'Updated content'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.content, 'Updated content')

    def test_soft_delete_post(self):
        post = Post.objects.create(author=self.author, content="To be deleted")
        self.client.force_authenticate(user=self.author)

        url = reverse('post-detail', kwargs={'pk': post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        post.refresh_from_db()
        self.assertTrue(post.is_deleted)

        # Excluded from feed
        feed_resp = self.client.get(reverse('post-list'))
        self.assertEqual(len(feed_resp.data['results']), 0)

    def test_reaction_toggle_and_counter(self):
        post = Post.objects.create(author=self.author, content="React to me")
        self.client.force_authenticate(user=self.colleague)
        url = reverse('post-toggle-reaction', kwargs={'pk': post.pk})

        # Like
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertTrue(r1.data['liked'])
        self.assertEqual(r1.data['like_count'], 1)

        # Unlike
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertFalse(r2.data['liked'])
        self.assertEqual(r2.data['like_count'], 0)

    def test_comments_and_counter(self):
        post = Post.objects.create(author=self.author, content="Comment on me")
        self.client.force_authenticate(user=self.colleague)
        url = reverse('post-comments', kwargs={'pk': post.pk})

        # Add comment
        resp = self.client.post(url, {'content': 'Great job team!'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        post.refresh_from_db()
        self.assertEqual(post.comment_count, 1)

        # List comments
        list_resp = self.client.get(url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data['results']), 1)
        self.assertEqual(list_resp.data['results'][0]['content'], 'Great job team!')

        # Delete comment
        comment_id = resp.data['id']
        del_url = reverse('comment-detail', kwargs={'pk': comment_id})
        del_resp = self.client.delete(del_url)
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)

        post.refresh_from_db()
        self.assertEqual(post.comment_count, 0)

    def test_multi_emoji_reactions_and_switching(self):
        post = Post.objects.create(author=self.author, content="Multi emoji reaction test")
        self.client.force_authenticate(user=self.colleague)
        url = reverse('post-toggle-reaction', kwargs={'pk': post.pk})

        # React with LOVE
        r_love = self.client.post(url, {'reaction_type': 'LOVE'}, format='json')
        self.assertEqual(r_love.status_code, status.HTTP_200_OK)
        self.assertTrue(r_love.data['liked'])
        self.assertEqual(r_love.data['like_count'], 1)
        self.assertEqual(r_love.data['user_reaction'], 'LOVE')

        # Switch reaction to HAHA (Count should stay 1, type changes)
        r_haha = self.client.post(url, {'reaction_type': 'HAHA'}, format='json')
        self.assertEqual(r_haha.status_code, status.HTTP_200_OK)
        self.assertTrue(r_haha.data['liked'])
        self.assertEqual(r_haha.data['like_count'], 1)
        self.assertEqual(r_haha.data['user_reaction'], 'HAHA')

        # Click HAHA again (Toggle off -> count becomes 0)
        r_off = self.client.post(url, {'reaction_type': 'HAHA'}, format='json')
        self.assertEqual(r_off.status_code, status.HTTP_200_OK)
        self.assertFalse(r_off.data['liked'])
        self.assertEqual(r_off.data['like_count'], 0)
        self.assertIsNone(r_off.data['user_reaction'])

    def test_non_owner_cannot_delete_post(self):
        post = Post.objects.create(author=self.author, content="Author's private post")
        self.client.force_authenticate(user=self.colleague)
        url = reverse('post-detail', kwargs={'pk': post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        post.refresh_from_db()
        self.assertFalse(post.is_deleted)

    def test_non_owner_cannot_delete_comment(self):
        post = Post.objects.create(author=self.author, content="Post for comment test")
        comment = Comment.objects.create(post=post, author=self.author, content="Author's comment")
        self.client.force_authenticate(user=self.colleague)
        url = reverse('comment-detail', kwargs={'pk': comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        comment.refresh_from_db()
        self.assertFalse(comment.is_deleted)

    def test_admin_can_delete_any_post(self):
        post = Post.objects.create(author=self.author, content="Post to be moderated")
        self.client.force_authenticate(user=self.admin)
        url = reverse('post-detail', kwargs={'pk': post.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        post.refresh_from_db()
        self.assertTrue(post.is_deleted)

    def test_admin_can_delete_any_comment(self):
        post = Post.objects.create(author=self.author, content="Post for moderation", comment_count=1)
        comment = Comment.objects.create(post=post, author=self.author, content="Inappropriate comment")
        self.client.force_authenticate(user=self.admin)
        url = reverse('comment-detail', kwargs={'pk': comment.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
        post.refresh_from_db()
        self.assertEqual(post.comment_count, 0)

    def test_filter_comments_by_author(self):
        post = Post.objects.create(author=self.author, content="Post with comments")
        c1 = Comment.objects.create(post=post, author=self.author, content="Author comment")
        c2 = Comment.objects.create(post=post, author=self.colleague, content="Colleague comment")

        self.client.force_authenticate(user=self.author)
        url = f"{reverse('comment-list')}?author={self.author.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], c1.id)

    def test_post_reactions_breakdown_and_filtering(self):
        post = Post.objects.create(author=self.author, content="Post for reaction list test")
        PostReaction.objects.create(post=post, user=self.author, reaction_type=PostReaction.ReactionType.LIKE)
        PostReaction.objects.create(post=post, user=self.colleague, reaction_type=PostReaction.ReactionType.LOVE)

        self.client.force_authenticate(user=self.author)
        url = reverse('post-reactions', kwargs={'pk': post.pk})
        response = self.client.get(f"{url}?all=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['breakdown']['LIKE'], 1)
        self.assertEqual(response.data['breakdown']['LOVE'], 1)
        self.assertEqual(len(response.data['results']), 2)

        # Test filtering by reaction type
        response_like = self.client.get(f"{url}?type=LIKE&all=true")
        self.assertEqual(response_like.status_code, status.HTTP_200_OK)
        self.assertEqual(response_like.data['count'], 1)
        self.assertEqual(response_like.data['results'][0]['user'], self.author.id)
        self.assertEqual(response_like.data['results'][0]['user_details']['id'], self.author.id)

    def test_comment_toggle_reaction(self):
        post = Post.objects.create(author=self.author, content="Post for comment reaction")
        comment = Comment.objects.create(post=post, author=self.author, content="Nice comment")

        self.client.force_authenticate(user=self.colleague)
        url = reverse('comment-toggle-reaction', kwargs={'pk': comment.pk})

        # Add reaction
        response = self.client.post(url, {'reaction_type': 'LOVE'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['liked'])
        self.assertEqual(response.data['reaction_type'], 'LOVE')
        self.assertEqual(response.data['like_count'], 1)

        # Switch reaction to HAHA
        response = self.client.post(url, {'reaction_type': 'HAHA'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['liked'])
        self.assertEqual(response.data['reaction_type'], 'HAHA')
        self.assertEqual(response.data['like_count'], 1)

        # Remove reaction (toggle off)
        response = self.client.post(url, {'reaction_type': 'HAHA'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['liked'])
        self.assertIsNone(response.data['reaction_type'])
        self.assertEqual(response.data['like_count'], 0)

