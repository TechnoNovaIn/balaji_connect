package com.balajitransports.connect.data.api

import com.balajitransports.connect.data.security.TokenManager
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val tokenManager: TokenManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val token = tokenManager.getToken()

        val requestBuilder = originalRequest.newBuilder()
        if (!token.isNullOrBlank()) {
            requestBuilder.addHeader("Authorization", "Token $token")
        }

        val response = chain.proceed(requestBuilder.build())

        // Disabled employees or invalidated sessions immediately lose access
        if (response.code == 401 || response.code == 403) {
            tokenManager.clear()
        }

        return response
    }
}

