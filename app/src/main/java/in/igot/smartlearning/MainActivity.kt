package `in`.igot.smartlearning

import android.app.Activity
import android.os.Bundle
import android.graphics.Typeface
import android.view.Gravity
import android.view.View
import android.widget.*
import android.graphics.Color
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.io.OutputStreamWriter
import java.util.concurrent.Executors
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.provider.Settings
import android.net.Uri
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var securePrefs: android.content.SharedPreferences
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val masterKey = MasterKey.Builder(this).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        securePrefs = EncryptedSharedPreferences.create(this, "secure_settings", masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(12, 12, 12, 12); setBackgroundColor(Color.rgb(247,248,252)) }
        val title = TextView(this).apply { text = "iGOT Smart Learning"; textSize = 20f; setTextColor(Color.rgb(25,45,80)); typeface = Typeface.DEFAULT_BOLD }
        val subtitle = TextView(this).apply { text = "आपका सीखने और समझने का साथी"; textSize = 14f; setPadding(0,4,0,8); setTextColor(Color.DKGRAY) }
        val intro = TextView(this).apply { text = "Split Screen में iGOT ऊपर और यह ऐप नीचे रखें। ऊपर प्रश्न देखकर यहाँ लिखें; AI उसे समझाएगा।"; textSize = 15f; setTextColor(Color.DKGRAY) }
        val key = EditText(this).apply { hint = "Gemini API key (केवल इस मोबाइल में सेव होगी)"; setSingleLine(true); textSize = 14f; inputType = 0x00000081; setText(securePrefs.getString("gemini_api_key", "")) }
        val saveKey = Button(this).apply { text = "API Key सुरक्षित सेव करें" }
        val language = Spinner(this).apply { adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, listOf("हिंदी में समझाएँ", "Explain in English", "Hindi + English")) }
        val question = EditText(this).apply { hint = "ऊपर iGOT में दिख रहा प्रश्न यहाँ लिखें…"; minLines = 2; maxLines = 5; gravity = Gravity.TOP; textSize = 15f; setText(intent.getStringExtra("captured_question") ?: "") }
        val scan = TextView(this).apply { text = "नोट: iGOT की सुरक्षा के कारण स्क्रीन अपने-आप पढ़ना बंद हो सकता है। Split Screen में प्रश्न देखकर यहाँ लिखें।"; textSize = 12f; setTextColor(Color.DKGRAY); setPadding(0,6,0,6) }
        scan.setOnClickListener {
            if (!Settings.canDrawOverlays(this@MainActivity)) {
                startActivityForResult(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")), 310)
            } else requestScreenCapture()
        }
        val explain = Button(this).apply { text = "AI से समझें" }
        val progress = ProgressBar(this).apply { visibility = View.GONE }
        val result = TextView(this).apply { text = "AI की व्याख्या यहाँ दिखाई देगी।"; textSize = 16f; setPadding(0,14,0,0); setTextColor(Color.BLACK) }
        saveKey.setOnClickListener {
            val value = key.text.toString().trim()
            if (value.isBlank()) { result.text = "पहले API Key दर्ज करें।"; return@setOnClickListener }
            securePrefs.edit().putString("gemini_api_key", value).apply()
            result.text = "API Key इस फोन में सुरक्षित सेव हो गई है। इसे GitHub या चैट में साझा न करें।"
        }
        explain.setOnClickListener {
            val apiKey = key.text.toString().trim()
            val prompt = question.text.toString().trim()
            if (apiKey.isEmpty()) { result.text = "कृपया अपनी Gemini API key दर्ज करें। इसे किसी के साथ साझा न करें।"; return@setOnClickListener }
            if (prompt.isEmpty()) { result.text = "पहले प्रश्न या विषय लिखें।"; return@setOnClickListener }
            explain.isEnabled = false; progress.visibility = View.VISIBLE; result.text = "उत्तर तैयार हो रहा है…"
            val lang = language.selectedItem.toString()
            worker.execute {
                val answer = try { askGemini(apiKey, prompt, lang) } catch (e: Exception) { "त्रुटि: ${e.message ?: "कनेक्शन नहीं हो पाया"}. API key और इंटरनेट कनेक्शन जाँचें।" }
                runOnUiThread { result.text = answer; explain.isEnabled = true; progress.visibility = View.GONE }
            }
        }
        root.addView(title); root.addView(subtitle); root.addView(intro); root.addView(key); root.addView(saveKey)
        root.addView(language); root.addView(scan); root.addView(question, LinearLayout.LayoutParams(-1, LinearLayout.LayoutParams.WRAP_CONTENT)); root.addView(explain); root.addView(progress); root.addView(result)
        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun requestScreenCapture() {
        val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(manager.createScreenCaptureIntent(), 311)
    }

    @Deprecated("Legacy activity result callback for broad Android compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 310) {
            if (Settings.canDrawOverlays(this)) requestScreenCapture()
            else Toast.makeText(this, "फ्लोटिंग बटन के लिए स्क्रीन पर दिखाने की अनुमति जरूरी है।", Toast.LENGTH_LONG).show()
            return
        }
        if (requestCode == 311) {
            if (resultCode == RESULT_OK && data != null) {
                val service = Intent(this, ScreenReaderService::class.java).putExtra("resultCode", resultCode).putExtra("data", data)
                if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(service) else startService(service)
                Toast.makeText(this, "अब iGOT खोलें। स्क्रीन पर दिखने वाले बटन से प्रश्न पढ़ें।", Toast.LENGTH_LONG).show()
            } else Toast.makeText(this, "स्क्रीन पढ़ने की अनुमति नहीं मिली।", Toast.LENGTH_SHORT).show()
        }
    }

    private fun askGemini(apiKey: String, question: String, language: String): String {
        val safeKey = URLEncoder.encode(apiKey, "UTF-8")
        val url = URL("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$safeKey")
        val conn = (url.openConnection() as HttpURLConnection).apply { requestMethod = "POST"; connectTimeout = 20000; readTimeout = 60000; doOutput = true; setRequestProperty("Content-Type", "application/json") }
        val langInstruction = when(language) { "Explain in English" -> "Answer in clear English."; "Hindi + English" -> "Explain in both Hindi and English."; else -> "उत्तर सरल, स्पष्ट हिंदी में दें।" }
        val body = JSONObject().put("contents", org.json.JSONArray().put(JSONObject().put("parts", org.json.JSONArray().put(JSONObject().put("text", "$langInstruction\nइस प्रश्न की अवधारणा समझाएँ, तर्क और चरण दें, और जहाँ उचित हो उदाहरण दें। यदि यह किसी चल रहे आधिकारिक मूल्यांकन का प्रश्न हो, तो सीधे जमा करने योग्य उत्तर देने के बजाय अवधारणा और सीखने में मदद करें।\nप्रश्न: $question"))))).toString()
        try {
            OutputStreamWriter(conn.outputStream, Charsets.UTF_8).use { it.write(body) }
            val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
            val raw = stream.bufferedReader().use { it.readText() }
            if (conn.responseCode !in 200..299) throw IllegalStateException("Gemini API HTTP ${conn.responseCode}: ${JSONObject(raw).optString("message", raw.take(300))}")
            val json = JSONObject(raw)
            return json.getJSONArray("candidates").getJSONObject(0).getJSONObject("content").getJSONArray("parts").getJSONObject(0).getString("text")
        } finally { conn.disconnect() }
    }
}
