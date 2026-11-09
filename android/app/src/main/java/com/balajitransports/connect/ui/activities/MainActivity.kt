package com.balajitransports.connect.ui.activities

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.balajitransports.connect.R
import com.balajitransports.connect.data.api.ApiClient
import com.balajitransports.connect.data.models.PostDto
import com.balajitransports.connect.data.security.TokenManager
import com.google.android.material.button.MaterialButton
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var tokenManager: TokenManager
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: PostAdapter
    private val postsList = mutableListOf<PostDto>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokenManager = TokenManager(this)

        if (!tokenManager.isLoggedIn()) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        setContentView(R.layout.activity_main)

        recyclerView = findViewById(R.id.recyclerViewFeed)
        recyclerView.layoutManager = LinearLayoutManager(this)
        adapter = PostAdapter(postsList) { post ->
            toggleReaction(post)
        }
        recyclerView.adapter = adapter

        findViewById<FloatingActionButton>(R.id.fabCreatePost).setOnClickListener {
            Toast.makeText(this, "Create post feature opened", Toast.LENGTH_SHORT).show()
        }

        loadFeed()
    }

    private fun loadFeed() {
        lifecycleScope.launch {
            try {
                val api = ApiClient.getService(this@MainActivity)
                val response = api.getFeed()
                if (response.isSuccessful && response.body() != null) {
                    postsList.clear()
                    postsList.addAll(response.body()!!.results)
                    adapter.notifyDataSetChanged()
                } else if (response.code() == 401 || response.code() == 403) {
                    tokenManager.clear()
                    startActivity(Intent(this@MainActivity, LoginActivity::class.java))
                    finish()
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Error loading feed: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun toggleReaction(post: PostDto) {
        lifecycleScope.launch {
            try {
                val api = ApiClient.getService(this@MainActivity)
                val res = api.toggleReaction(post.id)
                if (res.isSuccessful && res.body() != null) {
                    val updated = post.copy(
                        hasReacted = res.body()!!.liked,
                        likeCount = res.body()!!.likeCount
                    )
                    val index = postsList.indexOfFirst { it.id == post.id }
                    if (index != -1) {
                        postsList[index] = updated
                        adapter.notifyItemChanged(index)
                    }
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Failed to react: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    inner class PostAdapter(
        private val items: List<PostDto>,
        private val onLikeClick: (PostDto) -> Unit
    ) : RecyclerView.Adapter<PostAdapter.PostViewHolder>() {

        inner class PostViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
            val tvAuthorAvatar: TextView = itemView.findViewById(R.id.tvAuthorAvatar)
            val tvAuthorName: TextView = itemView.findViewById(R.id.tvAuthorName)
            val tvPostMeta: TextView = itemView.findViewById(R.id.tvPostMeta)
            val tvPostContent: TextView = itemView.findViewById(R.id.tvPostContent)
            val ivPostImage: ImageView = itemView.findViewById(R.id.ivPostImage)
            val btnLike: MaterialButton = itemView.findViewById(R.id.btnLike)
            val btnComment: MaterialButton = itemView.findViewById(R.id.btnComment)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PostViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_post, parent, false)
            return PostViewHolder(view)
        }

        override fun onBindViewHolder(holder: PostViewHolder, position: Int) {
            val item = items[position]
            holder.tvAuthorName.text = item.authorDetails.fullName
            holder.tvPostMeta.text = "${item.authorDetails.departmentCode ?: "BT"} • ${item.createdAt.take(10)}"
            holder.tvAuthorAvatar.text = item.authorDetails.fullName.firstOrNull()?.toString()?.uppercase() ?: "B"

            if (item.content.isNotBlank()) {
                holder.tvPostContent.text = item.content
                holder.tvPostContent.visibility = View.VISIBLE
            } else {
                holder.tvPostContent.visibility = View.GONE
            }

            if (item.mediaAttachments.isNotEmpty()) {
                val media = item.mediaAttachments.first()
                if (media.fileType == "IMAGE") {
                    holder.ivPostImage.visibility = View.VISIBLE
                    holder.ivPostImage.load(media.viewUrl)
                } else {
                    holder.ivPostImage.visibility = View.GONE
                }
            } else {
                holder.ivPostImage.visibility = View.GONE
            }

            holder.btnLike.text = if (item.hasReacted) "Liked (${item.likeCount})" else "Like (${item.likeCount})"
            holder.btnComment.text = "Comment (${item.commentCount})"

            holder.btnLike.setOnClickListener {
                onLikeClick(item)
            }
        }

        override fun getItemCount(): Int = items.size
    }
}

