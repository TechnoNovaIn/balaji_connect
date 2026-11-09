package com.balajitransports.connect.data.api

import android.content.Context
import com.balajitransports.connect.data.security.TokenManager
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    // 10.0.2.2 points to host localhost in Android Emulator
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/"

    private var retrofit: Retrofit? = null

    fun getService(context: Context, baseUrl: String = DEFAULT_BASE_URL): BalajiApiService {
        if (retrofit == null) {
            val tokenManager = TokenManager(context.applicationContext)

            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor(tokenManager))
                .addInterceptor(logging)
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .build()

            retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }

        return retrofit!!.create(BalajiApiService::class.java)
    }
}

