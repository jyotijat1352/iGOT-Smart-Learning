package in.igot.smartlearning

import android.app.Activity
import android.os.Bundle
import android.graphics.Typeface
import android.view.Gravity
import android.widget.*
import android.graphics.Color

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24, 32, 24, 24); setBackgroundColor(Color.rgb(247,248,252)) }
        val title = TextView(this).apply { text = "iGOT Smart Learning"; textSize = 26f; setTextColor(Color.rgb(25,45,80)); typeface = Typeface.DEFAULT_BOLD }
        val subtitle = TextView(this).apply { text = "आपका सीखने और समझने का साथी"; textSize = 17f; setPadding(0,8,0,24); setTextColor(Color.DKGRAY) }
        val intro = TextView(this).apply { text = "किसी कोर्स के प्रश्न या विषय को यहाँ लिखें। यह ऐप आपको विषय समझने और अभ्यास करने में मदद करेगा। आधिकारिक परीक्षा में उत्तर चुनना और Submit करना आपका अपना निर्णय रहेगा।"; textSize = 16f; setTextColor(Color.DKGRAY) }
        val question = EditText(this).apply { hint = "यहाँ प्रश्न या विषय लिखें…"; minLines = 4; gravity = Gravity.TOP; textSize = 16f }
        val explain = Button(this).apply { text = "समझने में मदद करें" }
        val result = TextView(this).apply { text = "आपका अध्ययन नोट यहाँ दिखाई देगा।"; textSize = 16f; setPadding(0,20,0,0); setTextColor(Color.BLACK) }
        explain.setOnClickListener { result.text = if (question.text.isNullOrBlank()) "पहले कोई प्रश्न या विषय लिखें।" else "आपका प्रश्न दर्ज हो गया है। अगले चरण में सुरक्षित AI व्याख्या सुविधा जोड़ी जाएगी।\n\nप्रश्न: ${question.text}" }
        root.addView(title); root.addView(subtitle); root.addView(intro); root.addView(question, LinearLayout.LayoutParams(-1, 0, 1f)); root.addView(explain); root.addView(result)
        setContentView(root)
    }
}
