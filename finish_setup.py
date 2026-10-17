import os

print(">>> Đang hoàn tất nốt các file giao diện còn lại...")

# 1. Tạo TranslationBoxDetailOverlay.kt
detail_overlay_path = "app/src/main/java/com/playtranslate/ui/TranslationBoxDetailOverlay.kt"
os.makedirs(os.path.dirname(detail_overlay_path), exist_ok=True)
with open(detail_overlay_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import com.playtranslate.OverlayColors
import com.playtranslate.PlayTranslateAccessibilityService
import com.playtranslate.tts.TtsManager

class TranslationBoxDetailOverlay(
    private val context: Context,
    private val wm: WindowManager,
    private val displayId: Int,
    private val rawText: String,
    private val translatedText: String
) {
    private var scrimView: View? = null

    fun show() {
        dismiss()
        val dp = context.resources.displayMetrics.density
        val oc = OverlayColors

        val scrim = FrameLayout(context).apply {
            setBackgroundColor(Color.argb(160, 0, 0, 0))
            setOnClickListener { dismiss() }
        }

        val card = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(oc.surface(context))
                setStroke((1 * dp).toInt(), oc.divider(context))
                cornerRadius = 16 * dp
            }
            setPadding((20 * dp).toInt(), (20 * dp).toInt(), (20 * dp).toInt(), (16 * dp).toInt())
            setOnClickListener { }
        }

        // Header
        val header = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (14 * dp).toInt() }
        }
        val title = TextView(context).apply {
            text = "Chi tiết bản dịch"
            textSize = 17f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(oc.text(context))
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        val btnSpeak = ImageButton(context).apply {
            setImageResource(android.R.drawable.ic_lock_silent_mode_off)
            setColorFilter(oc.accent(context))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener {
                TtsManager.getInstance(context).speak(translatedText, force = true)
            }
            layoutParams = LinearLayout.LayoutParams((36 * dp).toInt(), (36 * dp).toInt())
        }
        val btnClose = ImageButton(context).apply {
            setImageResource(android.R.drawable.ic_menu_close_clear_cancel)
            setColorFilter(oc.textMuted(context))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener { dismiss() }
            layoutParams = LinearLayout.LayoutParams((36 * dp).toInt(), (36 * dp).toInt())
        }
        header.addView(title)
        header.addView(btnSpeak)
        header.addView(btnClose)
        card.addView(header)

        // Raw Box
        val rawCard = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(oc.card(context))
                setStroke((1 * dp).toInt(), oc.divider(context))
                cornerRadius = 12 * dp
            }
            setPadding((12 * dp).toInt(), (12 * dp).toInt(), (12 * dp).toInt(), (10 * dp).toInt())
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (12 * dp).toInt() }
        }
        rawCard.addView(TextView(context).apply {
            text = "ORIGINAL TEXT"
            textSize = 10f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(oc.textMuted(context))
        })
        rawCard.addView(TextView(context).apply {
            text = rawText
            textSize = 15f
            setTextColor(oc.text(context))
            setPadding(0, (6 * dp).toInt(), 0, (6 * dp).toInt())
        })
        val btnCopyRaw = Button(context).apply {
            text = "Copy Original"
            textSize = 12f
            isAllCaps = false
            setTextColor(oc.accent(context))
            setBackgroundColor(Color.TRANSPARENT)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { gravity = Gravity.END }
            setOnClickListener {
                copy(rawText, "Raw text copied")
            }
        }
        rawCard.addView(btnCopyRaw)
        card.addView(rawCard)

        // Translated Box
        val transCard = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(oc.card(context))
                setStroke((1 * dp).toInt(), oc.divider(context))
                cornerRadius = 12 * dp
            }
            setPadding((12 * dp).toInt(), (12 * dp).toInt(), (12 * dp).toInt(), (10 * dp).toInt())
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
        transCard.addView(TextView(context).apply {
            text = "TRANSLATION"
            textSize = 10f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(oc.accent(context))
        })
        transCard.addView(TextView(context).apply {
            text = translatedText
            textSize = 16f
            setTextColor(oc.text(context))
            setPadding(0, (6 * dp).toInt(), 0, (6 * dp).toInt())
        })
        val btnCopyTrans = Button(context).apply {
            text = "Copy Translation"
            textSize = 12f
            isAllCaps = false
            setTextColor(oc.accent(context))
            setBackgroundColor(Color.TRANSPARENT)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { gravity = Gravity.END }
            setOnClickListener {
                copy(translatedText, "Translation copied")
            }
        }
        transCard.addView(btnCopyTrans)
        card.addView(transCard)

        val maxW = (320 * dp).toInt()
        val cardLp = FrameLayout.LayoutParams(maxW, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            gravity = Gravity.CENTER
        }
        scrim.addView(card, cardLp)

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        if (PlayTranslateAccessibilityService.addOverlay(scrim, wm, params, displayId)) {
            scrimView = scrim
        }
    }

    private fun copy(text: String, label: String) {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("PlayTranslate", text))
        Toast.makeText(context, label, Toast.LENGTH_SHORT).show()
    }

    fun dismiss() {
        val v = scrimView ?: return
        PlayTranslateAccessibilityService.removeOverlay(v, wm)
        scrimView = null
    }
}
""")
print(f"  + Đã tạo: {detail_overlay_path}")

# 2. Cập nhật PlayTranslateAccessibilityService.kt dùng TranslationBoxDetailOverlay
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
if os.path.exists(a11y_path):
    with open(a11y_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_on_box = """            onBoxClicked = { box ->
                val intent = Intent(this@PlayTranslateAccessibilityService, com.playtranslate.ui.WordAnkiReviewActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    putExtra(com.playtranslate.ui.WordAnkiReviewActivity.EXTRA_WORD, box.sourceText)
                    putExtra(com.playtranslate.ui.WordAnkiReviewActivity.EXTRA_DEFINITION, box.translatedText)
                }
                startActivity(intent)
            }"""

    new_on_box = """            onBoxClicked = { box ->
                com.playtranslate.ui.TranslationBoxDetailOverlay(
                    this@PlayTranslateAccessibilityService,
                    wm,
                    displayId,
                    box.sourceText,
                    box.translatedText
                ).show()
            }"""
    if old_on_box in content:
        content = content.replace(old_on_box, new_on_box)
        with open(a11y_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  * Đã cập nhật Overlay click trong: {a11y_path}")

# 3. Cập nhật FloatingIconMenu.kt
menu_path = "app/src/main/java/com/playtranslate/ui/FloatingIconMenu.kt"
if os.path.exists(menu_path):
    with open(menu_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Thêm callbacks nếu chưa có
    if "var onToggleInspectMode" not in content:
        content = content.replace(
            "var onCaptureRegion: (() -> Unit)? = null",
            "var onCaptureRegion: (() -> Unit)? = null\n    var onSetTtsZone: (() -> Unit)? = null\n    var onToggleInspectMode: (() -> Unit)? = null"
        )

    # Thêm nút Inspect và nút TTS Zone vào menu
    menu_buttons = """
        // Inspect Mode Toggle Button
        val isInspectOn = com.playtranslate.Prefs(context).inspectModeEnabled
        val inspectGroup = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (10 * dp).toInt() }
        }
        val inspectBtn = FrameLayout(context).apply {
            background = GradientDrawable().apply {
                setColor(if (isInspectOn) accentColor else cardColor)
                cornerRadius = 14 * dp
            }
            elevation = 4 * dp
            layoutParams = LinearLayout.LayoutParams(btnSize, btnSize).apply {
                gravity = Gravity.CENTER_HORIZONTAL
            }
            setOnClickListener { onToggleInspectMode?.invoke() }
        }
        val inspectIcon = ImageView(context).apply {
            setImageResource(R.drawable.ic_edit)
            imageTintList = android.content.res.ColorStateList.valueOf(if (isInspectOn) onAccentColor else textColor)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            setPadding(iconPad, iconPad, iconPad, iconPad)
        }
        inspectBtn.addView(inspectIcon, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        val inspectLabel = TextView(context).apply {
            text = if (isInspectOn) "Inspect: ON" else "Inspect: OFF"
            setTextColor(textColor)
            textSize = 9f
            gravity = Gravity.CENTER_HORIZONTAL
            setTypeface(null, Typeface.BOLD)
            maxWidth = btnSize
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { topMargin = (4 * dp).toInt() }
        }
        inspectGroup.addView(inspectBtn)
        inspectGroup.addView(inspectLabel)
        menuCard.addView(inspectGroup)

        // TTS Zone Button
        val ttsZoneGroup = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (10 * dp).toInt() }
        }
        val ttsZoneBtn = FrameLayout(context).apply {
            background = GradientDrawable().apply {
                setColor(cardColor)
                cornerRadius = 14 * dp
            }
            elevation = 4 * dp
            layoutParams = LinearLayout.LayoutParams(btnSize, btnSize).apply {
                gravity = Gravity.CENTER_HORIZONTAL
            }
            setOnClickListener { onSetTtsZone?.invoke() }
        }
        val ttsZoneIcon = ImageView(context).apply {
            setImageResource(R.drawable.ic_crop)
            imageTintList = android.content.res.ColorStateList.valueOf(accentColor)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            setPadding(iconPad, iconPad, iconPad, iconPad)
        }
        ttsZoneBtn.addView(ttsZoneIcon, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        val ttsZoneLabel = TextView(context).apply {
            text = "TTS Zone"
            setTextColor(textColor)
            textSize = 9f
            gravity = Gravity.CENTER_HORIZONTAL
            setTypeface(null, Typeface.BOLD)
            maxWidth = btnSize
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { topMargin = (4 * dp).toInt() }
        }
        ttsZoneGroup.addView(ttsZoneBtn)
        ttsZoneGroup.addView(ttsZoneLabel)
        menuCard.addView(ttsZoneGroup)
"""
        
    target_anchor = "menuCard.addView(liveGroup)\n"
    if "Inspect: ON" not in content and target_anchor in content:
        content = content.replace(target_anchor, target_anchor + menu_buttons)

    with open(menu_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  * Đã cập nhật: {menu_path}")

print(">>> Hoàn tất toàn bộ 100%!")
