package in.igot.smartlearning

import android.app.*
import android.content.*
import android.graphics.*
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.provider.Settings
import android.view.*
import android.widget.*
import androidx.core.app.NotificationCompat
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.google.mlkit.vision.text.devanagari.DevanagariTextRecognizerOptions

class ScreenReaderService : Service() {
    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var overlay: View? = null
    private var windowManager: WindowManager? = null
    private val handler = Handler(Looper.getMainLooper())
    private var busy = false

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createChannel()
        startForeground(71, notification(), if (Build.VERSION.SDK_INT >= 29) android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION else 0)
        val code = intent?.getIntExtra("resultCode", Activity.RESULT_CANCELED) ?: Activity.RESULT_CANCELED
        val data = if (Build.VERSION.SDK_INT >= 33) intent?.getParcelableExtra("data", Intent::class.java) else @Suppress("DEPRECATION") intent?.getParcelableExtra("data")
        if (code == Activity.RESULT_OK && data != null && projection == null) {
            val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            projection = manager.getMediaProjection(code, data)
            startCapture()
            showOverlay()
        } else if (projection != null) showOverlay()
        return START_NOT_STICKY
    }

    private fun startCapture() {
        val metrics = resources.displayMetrics
        val width = metrics.widthPixels
        val height = metrics.heightPixels
        reader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        display = projection?.createVirtualDisplay("iGOT-screen-reader", width, height, metrics.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, reader?.surface, null, handler)
    }

    private fun showOverlay() {
        if (!Settings.canDrawOverlays(this) || overlay != null) return
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(16, 12, 16, 12)
            setBackgroundColor(Color.rgb(25, 45, 80))
        }
        val read = Button(this).apply { text = "iGOT स्क्रीन पढ़ें"; setOnClickListener { captureAndRead() } }
        val stop = Button(this).apply { text = "बंद करें"; setOnClickListener { stopSelf() } }
        panel.addView(read); panel.addView(stop)
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= 26) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { gravity = Gravity.TOP or Gravity.END; x = 10; y = 180 }
        overlay = panel
        windowManager?.addView(panel, params)
    }

    private fun captureAndRead() {
        if (busy) return
        busy = true
        handler.postDelayed({
            val img = reader?.acquireLatestImage()
            if (img == null) { busy = false; Toast.makeText(this, "स्क्रीन फ्रेम नहीं मिला, फिर कोशिश करें।", Toast.LENGTH_SHORT).show(); return@postDelayed }
            val plane = img.planes[0]
            val buffer = plane.buffer
            val pixelStride = plane.pixelStride
            val rowStride = plane.rowStride
            val rowPadding = rowStride - pixelStride * img.width
            val bitmap = Bitmap.createBitmap(img.width + rowPadding / pixelStride, img.height, Bitmap.Config.ARGB_8888)
            bitmap.copyPixelsFromBuffer(buffer)
            img.close()
            val cropped = Bitmap.createBitmap(bitmap, 0, 0, img.width, img.height)
            bitmap.recycle()
            val input = InputImage.fromBitmap(cropped, 0)
            val latin = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
            val hindi = TextRecognition.getClient(DevanagariTextRecognizerOptions.Builder().build())
            latin.process(input).addOnSuccessListener { en ->
                hindi.process(input).addOnSuccessListener { hi ->
                    val text = listOf(en.text, hi.text).filter { it.isNotBlank() }.distinct().joinToString("\n")
                    getSharedPreferences("screen_capture", MODE_PRIVATE).edit().putString("last_text", text).apply()
                    cropped.recycle(); latin.close(); hindi.close(); busy = false
                    val open = Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP).putExtra("captured_question", text)
                    val result = Button(this).apply { this.text = if (text.isBlank()) "टेक्स्ट नहीं मिला — दोबारा पढ़ें" else "टेक्स्ट पढ़ लिया — समझाएँ"; setOnClickListener { startActivity(open) } }
                    (overlay as? LinearLayout)?.let { if (it.childCount > 2) it.removeViewAt(2); it.addView(result) }
                }.addOnFailureListener { cropped.recycle(); latin.close(); hindi.close(); busy = false }
            }.addOnFailureListener { cropped.recycle(); latin.close(); hindi.close(); busy = false }
        }, 350)
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val channel = NotificationChannel("screen_reader", "Screen reader", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }
    private fun notification() = NotificationCompat.Builder(this, "screen_reader")
        .setContentTitle("iGOT Smart Learning चालू है")
        .setContentText("स्क्रीन पढ़ने के लिए फ्लोटिंग बटन दबाएँ")
        .setSmallIcon(android.R.drawable.ic_menu_view).setOngoing(true).build()

    override fun onDestroy() {
        try { overlay?.let { windowManager?.removeView(it) } } catch (_: Exception) {}
        display?.release(); reader?.close(); projection?.stop()
        overlay = null; display = null; reader = null; projection = null
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder? = null
}