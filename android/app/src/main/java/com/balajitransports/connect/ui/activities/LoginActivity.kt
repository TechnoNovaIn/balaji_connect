package com.balajitransports.connect.ui.activities

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.balajitransports.connect.R
import com.balajitransports.connect.data.api.ApiClient
import com.balajitransports.connect.data.models.LoginRequest
import com.balajitransports.connect.data.security.TokenManager
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var tokenManager: TokenManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokenManager = TokenManager(this)

        // Check if already authenticated
        if (tokenManager.isLoggedIn()) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        setContentView(R.layout.activity_login)

        val etEmployeeId = findViewById<EditText>(R.id.etEmployeeId)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val btnLogin = findViewById<Button>(R.id.btnLogin)
        val progressBar = findViewById<ProgressBar>(R.id.progressBar)
        val tvError = findViewById<TextView>(R.id.tvError)

        btnLogin.setOnClickListener {
            val identifier = etEmployeeId.text.toString().trim()
            val password = etPassword.text.toString()

            if (identifier.isEmpty() || password.isEmpty()) {
                tvError.text = "Please enter both Employee ID and password."
                tvError.visibility = View.VISIBLE
                return@setOnClickListener
            }

            btnLogin.isEnabled = false
            progressBar.visibility = View.VISIBLE
            tvError.visibility = View.GONE

            lifecycleScope.launch {
                try {
                    val api = ApiClient.getService(this@LoginActivity)
                    val response = api.login(LoginRequest(identifier, password))

                    if (response.isSuccessful && response.body() != null) {
                        val body = response.body()!!
                        tokenManager.saveToken(body.token)

                        startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                        finish()
                    } else {
                        tvError.text = "Invalid credentials or deactivated account."
                        tvError.visibility = View.VISIBLE
                    }
                } catch (e: Exception) {
                    tvError.text = "Network error: ${e.localizedMessage ?: "Failed to connect"}"
                    tvError.visibility = View.VISIBLE
                } finally {
                    btnLogin.isEnabled = true
                    progressBar.visibility = View.GONE
                }
            }
        }
    }
}

