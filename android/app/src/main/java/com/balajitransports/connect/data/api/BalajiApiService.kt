package com.balajitransports.connect.data.api

import com.balajitransports.connect.data.models.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.*

interface BalajiApiService {

    @POST("api/v1/auth/login/")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @POST("api/v1/auth/logout/")
    suspend fun logout(): Response<Unit>

    @GET("api/v1/auth/me/")
    suspend fun getMe(): Response<EmployeeDto>

    @GET("api/v1/posts/")
    suspend fun getFeed(@Query("page") page: Int = 1): Response<PaginatedResponse<PostDto>>

    @POST("api/v1/posts/")
    suspend fun createPost(@Body request: CreatePostRequest): Response<PostDto>

    @DELETE("api/v1/posts/{id}/")
    suspend fun deletePost(@Path("id") id: Long): Response<Unit>

    @POST("api/v1/posts/{id}/toggle_reaction/")
    suspend fun toggleReaction(@Path("id") id: Long): Response<ReactionResponse>

    @GET("api/v1/posts/{id}/comments/")
    suspend fun getComments(@Path("id") id: Long): Response<PaginatedResponse<CommentDto>>

    @POST("api/v1/posts/{id}/comments/")
    suspend fun createComment(@Path("id") id: Long, @Body request: CreateCommentRequest): Response<CommentDto>

    @Multipart
    @POST("api/v1/media/upload/")
    suspend fun uploadMedia(@Part file: MultipartBody.Part): Response<MediaAttachmentDto>

    @GET("api/v1/notifications/unread-count/")
    suspend fun getUnreadCount(): Response<UnreadCountResponse>
}

