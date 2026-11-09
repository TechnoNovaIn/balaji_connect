package com.balajitransports.connect.data.models

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    @SerializedName("identifier") val identifier: String,
    @SerializedName("password") val password: String
)

data class LoginResponse(
    @SerializedName("detail") val detail: String?,
    @SerializedName("token") val token: String,
    @SerializedName("employee") val employee: EmployeeDto
)

data class EmployeeDto(
    @SerializedName("id") val id: Long,
    @SerializedName("employee_id") val employeeId: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("department_name") val departmentName: String?,
    @SerializedName("department_code") val departmentCode: String?,
    @SerializedName("designation") val designation: String?,
    @SerializedName("avatar_url") val avatarUrl: String?,
    @SerializedName("role") val role: String,
    @SerializedName("is_active") val isActive: Boolean
)

data class PaginatedResponse<T>(
    @SerializedName("count") val count: Int,
    @SerializedName("next") val next: String?,
    @SerializedName("previous") val previous: String?,
    @SerializedName("results") val results: List<T>
)

data class MediaAttachmentDto(
    @SerializedName("id") val id: Long,
    @SerializedName("original_filename") val originalFilename: String,
    @SerializedName("file_type") val fileType: String,
    @SerializedName("mime_type") val mimeType: String,
    @SerializedName("file_size_bytes") val fileSizeBytes: Long,
    @SerializedName("view_url") val viewUrl: String
)

data class PostDto(
    @SerializedName("id") val id: Long,
    @SerializedName("author") val authorId: Long,
    @SerializedName("author_details") val authorDetails: EmployeeDto,
    @SerializedName("content") val content: String,
    @SerializedName("media_attachments") val mediaAttachments: List<MediaAttachmentDto>,
    @SerializedName("like_count") val likeCount: Int,
    @SerializedName("comment_count") val commentCount: Int,
    @SerializedName("has_reacted") val hasReacted: Boolean,
    @SerializedName("is_owner") val isOwner: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class CreatePostRequest(
    @SerializedName("content") val content: String,
    @SerializedName("media_ids") val mediaIds: List<Long> = emptyList()
)

data class ReactionResponse(
    @SerializedName("liked") val liked: Boolean,
    @SerializedName("like_count") val likeCount: Int
)

data class CommentDto(
    @SerializedName("id") val id: Long,
    @SerializedName("author_details") val authorDetails: EmployeeDto,
    @SerializedName("content") val content: String,
    @SerializedName("is_owner") val isOwner: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class CreateCommentRequest(
    @SerializedName("content") val content: String
)

data class UnreadCountResponse(
    @SerializedName("unread_count") val unreadCount: Int
)

