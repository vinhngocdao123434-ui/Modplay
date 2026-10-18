package com.playtranslate.ui

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
            setOnClickListener { copy(rawText, "Raw text copied") }
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
            setOnClickListener { copy(translatedText, "Translation copied") }
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
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
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
