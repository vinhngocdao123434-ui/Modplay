package com.playtranslate

import android.graphics.Color

import android.accessibilityservice.AccessibilityService
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Settings
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.graphics.Point
import android.hardware.display.DisplayManager
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Display
import android.view.Gravity
import android.view.InputDevice
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.doOnLayout
import com.playtranslate.ui.DimController
import com.playtranslate.ui.OverlayAlert
import com.playtranslate.ui.DragLookupController
import com.playtranslate.language.HintTextKind
import com.playtranslate.language.SourceLanguageProfiles
import com.playtranslate.ui.FloatingIconMenu
import com.playtranslate.ui.FloatingOverlayIcon
import com.playtranslate.ui.MagnifierLens
import com.playtranslate.ui.OcrDebugOverlayView
import com.playtranslate.ui.RegionDragView
import com.playtranslate.ui.TranslationOverlayView
import com.playtranslate.ui.WordLookupPopup
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Minimal AccessibilityService whose only purpose is to call
 * [takeScreenshot] on a specific display.
 *
 * WHY AN ACCESSIBILITY SERVICE?
 * ─────────────────────────────
 * MediaProjection captures the display the requesting Activity runs on.
 * Launching a bridge Activity on the game display caused the whole app
 * to move there. AccessibilityService.takeScreenshot(displayId) captures
 * any display by ID with no UI, no focus change, and no app relocation.
 *
 * SETUP (one-time)
 * ─────────────────
 * Settings → Accessibility → Installed apps → PlayTranslate → Enable
 * The app detects the enabled state via [isEnabled].
 */
class PlayTranslateAccessibilityService : AccessibilityService() {

    
    private val inspectWindows = mutableListOf<View>()

    fun updateInspectClickableBoxes(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int
    ) {
        // Logic moved entirely to TranslationOverlayView to fix z-order and touch issues.
        clearInspectClickableBoxes()
    }

    fun clearInspectClickableBoxes() {
        for (v in inspectWindows) {
            removeOverlayWindow(v)
        }
        inspectWindows.clear()
    }



    
    fun showTtsZoneEditor(display: Display) {
        val prefs = Prefs(this)
        val currentZone = prefs.getTtsZone()
        val initZone = if (currentZone.isFullScreen) {
            RegionEntry("TTS Zone", 0.55f, 0.90f, 0.10f, 0.90f, id = "tts_zone_default")
        } else currentZone

        showRegionDragOverlay(display, initZone) { _ -> }
        
        val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return
        val dp = ctx.resources.displayMetrics.density

        val bar = android.widget.LinearLayout(ctx).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding((16 * dp).toInt(), (10 * dp).toInt(), (16 * dp).toInt(), (10 * dp).toInt())
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.argb(230, 30, 30, 30))
                cornerRadius = 20 * dp
                setStroke((1 * dp).toInt(), Color.parseColor("#9C27B0"))
            }
        }

        val cancelBtn = android.widget.TextView(ctx).apply {
            text = "✕ Hủy"
            setTextColor(Color.WHITE)
            textSize = 14f
            gravity = Gravity.CENTER
            setPadding((12 * dp).toInt(), 0, (12 * dp).toInt(), 0)
            setOnClickListener { hideRegionDragOverlay(); removeOverlayWindow(bar) }
        }

        val saveBtn = android.widget.TextView(ctx).apply {
            text = "✓ Lưu vùng TTS"
            setTextColor(Color.parseColor("#E1BEE7"))
            textSize = 14f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setPadding((12 * dp).toInt(), 0, (12 * dp).toInt(), 0)
            setOnClickListener {
                val dv = dragView
                if (dv != null) {
                    prefs.setTtsZone(RegionEntry("TTS Zone", dv.topFraction, dv.bottomFraction, dv.leftFraction, dv.rightFraction))
                }
                hideRegionDragOverlay()
                val wm = (if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)).getSystemService(WindowManager::class.java) ?: return
        val view = RegionDragView(ctx).apply {
            setRegion(initRegion.top, initRegion.bottom, initRegion.left, initRegion.right)
            this.onRegionChanged = onRegionChanged
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        addOverlayWindow(view, wm, params, display.displayId)
        dragWm = wm
        dragView = view
    }

    fun hideRegionDragOverlay() {
        dragView?.let { removeOverlayWindow(it) }
        dragView = null
        dragWm = null
    }

    fun getDragRegion(): RegionEntry {
        val v = dragView ?: return RegionEntry("", 0.25f, 0.75f, 0.25f, 0.75f)
        return RegionEntry("", v.topFraction, v.bottomFraction, v.leftFraction, v.rightFraction)
    }

    // ── Self-contained OCR debug overlay ─────────────────────────────────

    private val DEBUG_INTERVAL_MS = 2000L

    /**
     * Starts a self-contained loop: capture → OCR → draw bounding boxes.
     * Completely independent of the translation pipeline.
     */
    fun startDebugOcrLoop() {
        if (debugRunning) return
        debugRunning = true
        scheduleDebugCapture()
    }

    fun stopDebugOcrLoop() {
        debugRunning = false
        debugHandler.removeCallbacksAndMessages(null)
        hideDebugOverlay()
    val wm = (if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)).getSystemService(WindowManager::class.java) ?: return
        val view = OcrDebugOverlayView(ctx).apply {
            setBoxes(boxes, cropLeft, cropTop, screenshotW, screenshotH)
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        addOverlayWindow(view, wm, params, display.displayId)
        debugOverlayWm = wm
        debugOverlayView = view
    }

    fun hideDebugOverlay() {
        debugOverlayView?.let { removeOverlayWindow(it) }
        debugOverlayView = null
        debugOverlayWm = null
    }

    // ── Live translation overlay ─────────────────────────────────────────

    fun showTranslationOverlay(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int,
        pinholeMode: Boolean = false
    ) {
        // Overlay is appearing — dismiss loading spinner across all icons.
        setIconsLoading(false)

        val displayId = display.displayId
        // Reuse existing view only if it's on the same display AND was
        // constructed with the same pinhole mode; otherwise recreate so the
        // view's pinhole-related bakes (child bg opacity, dispatchDraw mask
        // punching) match what the caller expects.
        val existing = translationOverlayHandles[displayId]?.main
        if (existing != null && existing.pinholeMode == pinholeMode) {
            existing.setBoxes(boxes, cropLeft, cropTop, screenshotW, screenshotH)
            return
        }
        // Pinhole flavor mismatch (or no overlay yet) — tear down just this
        // display's pair and rebuild. Other displays' overlays are untouched.
        hideTranslationOverlayForDisplay(displayId)
        val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val themedCtx = android.view.ContextThemeWrapper(displayCtx, android.R.style.Theme_DeviceDefault)
        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return
        val view = TranslationOverlayView(themedCtx, pinholeMode = pinholeMode).apply {
            setBoxes(boxes, cropLeft, cropTop, screenshotW, screenshotH)
            onBoxClicked = { box ->
                com.playtranslate.ui.TranslationBoxDetailOverlay(
                    this@PlayTranslateAccessibilityService,
                    wm,
                    displayId,
                    box.sourceText,
                    box.translatedText
                ).show()
            }
        }
        val baseFlags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }
        addOverlayWindow(view, wm, params, displayId)

        // Create persistent dirty overlay window (always present, empty when not dirty).
        // Shares the same wm instance as the main overlay.
        val dirtyView = TranslationOverlayView(themedCtx, pinholeMode = true)
        val dirtyParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }
        addOverlayWindow(dirtyView, wm, dirtyParams, displayId)

        translationOverlayHandles[displayId] = TranslationOverlayHandle(view, dirtyView)
        updateInspectClickableBoxes(display, boxes, cropLeft, cropTop, screenshotW, screenshotH)
    }

    /**
     * Tear down a single display's translation + dirty overlay pair.
     * Idempotent — no-op when nothing is registered for [displayId].
     */
    fun hideTranslationOverlayForDisplay(displayId: Int) {
        val handle = translationOverlayHandles.remove(displayId) ?: return
        removeOverlayWindow(handle.main)
        removeOverlayWindow(handle.dirty)
    }

    /**
     * Tear down translation overlays across every display. Most existing
     * callers want this "global hide" semantic (pause / state recovery /
     * stop-live). P4's per-display modes will migrate to per-display
     * hides where they should only clear their own overlay.
     */
    fun hideTranslationOverlay() {
        if (translationOverlayHandles.isEmpty()) return
        val ids = translationOverlayHandles.keys.toList()
        for (id in ids) hideTranslationOverlayForDisplay(id)
    }

    /**
     * Remove specific overlay boxes from [displayId]'s overlay without
     * rebuilding the entire view. Defaults to the primary display so
     * existing single-display callers (e.g. FuriganaMode) keep working;
     * P4's per-display modes will pass their own [displayId].
     */
    fun removeOverlayBoxes(
        toRemove: List<TranslationOverlayView.TextBox>,
        displayId: Int = CaptureService.instance?.primaryGameDisplayId()
            ?: android.view.Display.DEFAULT_DISPLAY,
    ) {
        translationOverlayHandles[displayId]?.main?.removeBoxesByContent(toRemove)
    }

    // ── Floating overlay icon ─────────────────────────────────────────────

    // ── Input monitoring for live mode ──────────────────────────────────

    /**
     * Per-display input callbacks. Each LiveMode registers a callback for its
     * own displayId; the dispatch is per-source:
     *  - Touch (sentinel) is display-bound — only the touched display's
     *    callback fires (see [fireOnGameInputForDisplay]).
     *  - Gamepad / D-pad is NOT display-bound — controller focus is
     *    independent of touch focus, so a button press on a controller paired
     *    to display A must reach A's callback even if the user just touched
     *    display B for an unrelated reason. Fan-out is correct here (see
     *    [fireOnGameInput]).
     */
    private val onGameInputs: MutableMap<Int, () -> Unit> = mutableMapOf()
    private var lastKeyEventTime = 0L
    /** Derived from [heldKeyCodes] so a multi-key release pattern
     *  (press A → press B → release A) reports B as still held instead
     *  of incorrectly flipping to false on A's UP event. Single source
     *  of truth: only the key event handler mutates heldKeyCodes. */
    private val buttonHeld: Boolean get() = heldKeyCodes.isNotEmpty()
    private var touchActive = false
    private val TOUCH_HOLD_TIMEOUT_MS = 2000L
    private val touchTimeoutRunnable = Runnable { touchActive = false }

    /** Fan an input event out to every registered listener. Used by the
     *  gamepad/D-pad path in [onKeyEvent], where the input source isn't
     *  bound to a specific display. */
    private fun fireOnGameInput() {
        if (onGameInputs.isEmpty()) return
        onGameInputs.values.forEach { it.invoke() }
    }

    /** Dispatch an input event to a single display's listener. Used by the
     *  touch sentinel path, where the touched display is unambiguous and
     *  invalidating other displays' overlays would cause spurious flicker. */
    private fun fireOnGameInputForDisplay(displayId: Int) {
        onGameInputs[displayId]?.invoke()
    }

    /**
     * True while any input source is actively being used (button held,
     * touch down, or joystick held). CaptureService checks this to avoid
     * showing the overlay during active interaction.
     */
    val isInputActive: Boolean
        get() = buttonHeld || touchActive

    /**
     * Start monitoring gamepad buttons and screen touches on [displayId].
     * The [callback] fires on the main thread for every detected input;
     * multiple displays can have callbacks registered concurrently and all
     * will fire on each input event (see [fireOnGameInput]).
     */
    fun startInputMonitoring(displayId: Int, callback: () -> Unit) {
        onGameInputs[displayId] = callback
        lastKeyEventTime = 0L
        heldKeyCodes.clear()
        touchActive = false
        addTouchSentinel(displayId)
    }

    /** Stop monitoring input for a single display. Tears down THIS display's
     *  touch sentinel; global state (heldKeyCodes, touchActive) only
     *  resets when the last listener goes away. */
    fun stopInputMonitoring(displayId: Int) {
        onGameInputs.remove(displayId)
        removeTouchSentinelForDisplay(displayId)
        if (onGameInputs.isEmpty()) {
            heldKeyCodes.clear()
            touchActive = false
            debugHandler.removeCallbacks(touchTimeoutRunnable)
        }
    }

    /** Stop input monitoring across every display (e.g. on stopLive). */
    fun stopInputMonitoring() {
        onGameInputs.clear()
        heldKeyCodes.clear()
        touchActive = false
        debugHandler.removeCallbacks(touchTimeoutRunnable)
        removeTouchSentinel()
    }

    // ── Touch sentinel ──────────────────────────────────────────────────

    /**
     * A 1×1 transparent overlay on the game display. With FLAG_WATCH_OUTSIDE_TOUCH
     * every touch elsewhere on the screen delivers ACTION_OUTSIDE without consuming
     * the event, so the game still receives normal input.
     */
    @android.annotation.SuppressLint("ClickableViewAccessibility")
    private fun addTouchSentinel(displayId: Int) {
        if (displayId in touchSentinels) return
        val dm = getSystemService(DisplayManager::class.java)
        val display = dm.getDisplay(displayId) ?: return
        val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return
        val view = View(ctx).apply {
            setOnTouchListener { _, event ->
                if (event.actionMasked == MotionEvent.ACTION_OUTSIDE) {
                    // Mark touch as active. We can't detect touch-up from
                    // the sentinel, so use a timeout to assume lift.
                    touchActive = true
                    // Track which display the user just touched so hotkey
                    // routing lands on the right place (P5).
                    CaptureService.instance?.lastInteractedDisplayId = displayId
                    debugHandler.removeCallbacks(touchTimeoutRunnable)
                    debugHandler.postDelayed(touchTimeoutRunnable, TOUCH_HOLD_TIMEOUT_MS)
                    // Display-bound dispatch — only the touched display's
                    // overlay should be invalidated. Other displays' overlays
                    // stay put; their own scene-change detection covers any
                    // independent updates.
                    fireOnGameInputForDisplay(displayId)
                }
                false
            }
        }
        val params = WindowManager.LayoutParams(
            1, 1,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        )
        if (addOverlayWindow(view, wm, params, displayId)) {
            touchSentinels[displayId] = view
        }
    }

    /** Remove a single display's touch sentinel. */
    private fun removeTouchSentinelForDisplay(displayId: Int) {
        val view = touchSentinels.remove(displayId) ?: return
        removeOverlayWindow(view)
    }

    /** Remove every touch sentinel. */
    private fun removeTouchSentinel() {
        if (touchSentinels.isEmpty()) return
        val ids = touchSentinels.keys.toList()
        for (id in ids) removeTouchSentinelForDisplay(id)
    }


    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {
        Log.w(TAG, "onInterrupt")
    }

    /** Temporary listener for key event capture (e.g., hotkey setup dialog). Takes priority over normal handling. */
    var onKeyEventListener: ((KeyEvent) -> Boolean)? = null

    /**
     * True when the user has some visible indication the app is listening:
     * either the floating icon is on screen or MainActivity is foregrounded.
     * Used to gate hotkey activation so a user who has hidden the icon and
     * backgrounded the app doesn't get "ghost" hotkey triggers with no
     * feedback. Differs from the foreground-notification rule
     * ([CaptureService.updateForegroundState]) which intentionally omits
     * `foregrounded` — the notification is redundant while the app is on
     * screen, but hotkeys obviously must still work then.
     */
    fun isUserReachable(): Boolean =
        hasAnyFloatingIcon || MainActivity.isInForeground

    // ── Hotkey combo detection ──────────────────────────────────────────

    /**
     * Window to wait on a "shadowed" combo (one that is a proper subset of
     * another configured combo) before firing it. Prevents chord presses
     * like A+B from being misread as just A when A arrives a few ms before
     * B. Humans pressing two buttons simultaneously land within ~20-40ms of
     * each other; 60ms is comfortably above that and still below the point
     * at which players typically feel input latency.
     */
    private val HOTKEY_COMBO_WINDOW_MS = 60L

    private val heldKeyCodes = mutableSetOf<Int>()
    private var activeHotkeyMode: OverlayMode? = null
    private var pendingActivationMode: OverlayMode? = null

    /** Callback when a hotkey combo becomes fully held. */
    var onHotkeyActivated: ((OverlayMode) -> Unit)? = null
    /** Callback when the active hotkey combo is released. */
    var onHotkeyReleased: (() -> Unit)? = null

    private val pendingActivationRunnable = Runnable {
        val mode = pendingActivationMode ?: return@Runnable
        pendingActivationMode = null
        // Re-check reachability: the gate may have closed during the
        // deferral window (user backgrounded the app while mid-chord).
        if (!isUserReachable()) {
            android.util.Log.d("HotkeyDbg", "DEFERRED cancelled (gate closed): $mode")
            return@Runnable
        }
        activeHotkeyMode = mode
        android.util.Log.d("HotkeyDbg", "ACTIVATED (deferred): $mode")
        onHotkeyActivated?.invoke(mode)
    }

    private fun parseCombo(stored: String): Set<Int> {
        if (stored.isBlank()) return emptySet()
        return stored.split("+").mapNotNull { it.toIntOrNull() }.toSet()
    }

    private fun checkHotkeyCombos() {
        val prefs = Prefs(this)
        val combos = listOf(
            HotkeyCombo(parseCombo(prefs.hotkeyTranslation), OverlayMode.TRANSLATION),
            HotkeyCombo(parseCombo(prefs.hotkeyFurigana), OverlayMode.FURIGANA),
        ).filter { it.keys.isNotEmpty() }

        val state = HotkeyState(activeHotkeyMode, pendingActivationMode)
        val action = decideHotkeyAction(
            held = heldKeyCodes,
            state = state,
            combos = combos,
            reachable = isUserReachable(),
        )

        android.util.Log.d(
            "HotkeyDbg",
            "checkCombos: held=$heldKeyCodes combos=$combos state=$state → $action"
        )

        when (action) {
            is HotkeyAction.NoChange -> Unit

            is HotkeyAction.ActivateNow -> {
                debugHandler.removeCallbacks(pendingActivationRunnable)
                pendingActivationMode = null
                activeHotkeyMode = action.mode
                android.util.Log.d("HotkeyDbg", "ACTIVATED: ${action.mode}")
                onHotkeyActivated?.invoke(action.mode)
            }

            is HotkeyAction.DeferActivation -> {
                debugHandler.removeCallbacks(pendingActivationRunnable)
                pendingActivationMode = action.mode
                android.util.Log.d(
                    "HotkeyDbg",
                    "DEFERRED: ${action.mode} (waiting ${HOTKEY_COMBO_WINDOW_MS}ms for possible superset)"
                )
                debugHandler.postDelayed(pendingActivationRunnable, HOTKEY_COMBO_WINDOW_MS)
            }

            HotkeyAction.Release -> {
                val released = activeHotkeyMode
                activeHotkeyMode = null
                android.util.Log.d("HotkeyDbg", "RELEASED: $released")
                onHotkeyReleased?.invoke()
            }

            HotkeyAction.ClearPending -> {
                debugHandler.removeCallbacks(pendingActivationRunnable)
                val cleared = pendingActivationMode
                pendingActivationMode = null
                android.util.Log.d("HotkeyDbg", "PENDING CLEARED: $cleared")
            }
        }
    }

    override fun onKeyEvent(event: KeyEvent): Boolean {
        android.util.Log.d("HotkeyDbg", "onKeyEvent: keyCode=${event.keyCode} action=${event.action} source=0x${event.source.toString(16)}")

        // If a key event listener is active (e.g., hotkey setup), let it handle first
        onKeyEventListener?.let { listener ->
            if (listener(event)) return true
        }

        val src = event.source
        val isGameInput = src and InputDevice.SOURCE_GAMEPAD == InputDevice.SOURCE_GAMEPAD
            || src and InputDevice.SOURCE_DPAD == InputDevice.SOURCE_DPAD
            || KeyEvent.isGamepadButton(event.keyCode)
        if (isGameInput) {
            when (event.action) {
                KeyEvent.ACTION_DOWN -> {
                    lastKeyEventTime = System.currentTimeMillis()
                    heldKeyCodes.add(event.keyCode)
                    if (isAnyDragLookupPopupShowing) {
                        dismissAllDragLookupPopups()
                    }
                    fireOnGameInput()
                    checkHotkeyCombos()
                }
                KeyEvent.ACTION_UP -> {
                    heldKeyCodes.remove(event.keyCode)
                    lastKeyEventTime = System.currentTimeMillis()
                    fireOnGameInput()
                    checkHotkeyCombos()
                }
            }
        }
        return false // pass through to the game
    }

    /**
     * Single entry point for all icon visibility updates.
     * Called from: onServiceConnected, settings toggle, capture display change.
     *
     * Shows, hides, or relocates the icon based on current state.
     */
    /**
     * Reconcile the floating icons against [Prefs.captureDisplayIds]:
     *  - tear down icons whose display is no longer selected or has been
     *    disconnected
     *  - install icons for newly-selected, currently-connected displays
     *
     * Replaces P1's [ensureFloatingIcon] (which only knew about a single
     * primary display). Called on service connect, settings change, and
     * display hot-plug.
     */
    fun reconcileFloatingIcons() {
        val prefs = Prefs(this)
        if (!prefs.showOverlayIcon) {
            hideFloatingIcon("pref_disabled")
            return
        }
        val dm = getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        val target = prefs.captureDisplayIds

        // Snapshot before mutating — tear down icons no longer needed.
        val staleIds = iconHandles.keys.filter { id ->
            id !in target || dm.getDisplay(id) == null
        }
        for (id in staleIds) hideFloatingIconForDisplay(id, "reconcile_remove")

        // If the user has nothing selected (e.g. transient migration
        // state) OR every selected display is unreachable (the only
        // selected external display was just unplugged), fall back to the
        // legacy single-display heuristic so the app always has at least
        // one icon while it's "configured." Without the second clause the
        // user would lose every floating control after a hot-unplug of
        // their only selected display until they manually repaired prefs.
        if (target.none { dm.getDisplay(it) != null }) {
            val display = findIconDisplay(prefs) ?: return
            if (display.displayId !in iconHandles) {
                installFloatingIconForDisplay(display, prefs)
            }
            return
        }

        for (id in target) {
            if (id in iconHandles) continue
            val display = dm.getDisplay(id) ?: continue
            installFloatingIconForDisplay(display, prefs)
        }
    }

    /** Backwards-compat alias. */
    @Deprecated(
        "Use reconcileFloatingIcons() — single-display semantics are gone.",
        ReplaceWith("reconcileFloatingIcons()")
    )
    fun ensureFloatingIcon() = reconcileFloatingIcons()

    private fun installFloatingIconForDisplay(display: Display, prefs: Prefs) {
        val displayId = display.displayId
        // Idempotent: if an icon was already there for this display, tear it
        // down first so the closures and registry stay coherent.
        hideFloatingIconForDisplay(displayId, "recreating")

        val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return

        val icon = FloatingOverlayIcon(displayCtx).apply {
            this.wm = wm
            this.displayId = displayId
            compactMode = prefs.compactOverlayIcon
        }

        val params = WindowManager.LayoutParams(
            icon.viewSizePx, icon.viewSizePx,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = android.view.Gravity.TOP or android.view.Gravity.START
        }

        icon.params = params

        // Drag-end persists the icon's snap position to this display's slot.
        icon.onPositionChanged = { edge, fraction ->
            prefs.setIconPositionForDisplay(displayId, IconPosition(edge, fraction))
        }
        icon.onTap = {
            showFloatingMenu(display, icon)
        }

        // Drag-to-lookup: independent controller per display so the popup +
        // magnifier render against the correct display context.
        val popup = WordLookupPopup(displayCtx, wm, displayId)
        val magnifier = MagnifierLens(displayCtx, wm, displayId)
        val controller = DragLookupController(
            displayId = displayId,
            popup = popup,
            magnifier = magnifier
        )
        // Track whether live mode / region overlay were active when drag started
        var liveWasPausedForPopup = false
        var overlayHiddenForDrag = false
        // Wire the service-level cancel hook to this closure's flag.
        // openSentenceInApp calls cancelLivePauseObligation() to make the
        // chained resumeLiveMode in onSettled a no-op when the user is
        // launching a covering detail view (single-screen). Stored as a
        // local for now; bundled into the FloatingIconHandle on success.
        val clearLivePauseFlag: () -> Unit = { liveWasPausedForPopup = false }

        fun restoreRegionOverlay() {
            if (overlayHiddenForDrag) {
                overlayHiddenForDrag = false
                regionIndicatorView?.visibility = View.VISIBLE
            }
        }

        fun resumeLiveMode() {
            if (liveWasPausedForPopup) {
                liveWasPausedForPopup = false
                val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
                if (effectivelySingleScreen) {
                    toggleLiveDirect(true)
                } else {
                    sendMainActivityIntent(MainActivity.ACTION_START_LIVE)
                }
            }
        }

        // The controller fires onSettled from every "drag flow done, no popup
        // pending" path: drag end with no OCR / no hit / async lookup miss,
        // popup dismissed post-drag, and gesture cancel. The restore lambdas
        // are idempotent (gated on overlayHiddenForDrag / liveWasPausedForPopup).
        controller.onSettled = {
            restoreRegionOverlay()
            resumeLiveMode()
        }
        icon.onDragStart = {
            // Hide region preview so the user can see game text while dragging
            if (regionIndicatorView?.visibility == View.VISIBLE) {
                overlayHiddenForDrag = true
                regionIndicatorView?.visibility = View.INVISIBLE
            }
            // Pause live mode while dragging for definitions
            if (CaptureService.instance?.isLive == true) {
                liveWasPausedForPopup = true
                val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
                if (effectivelySingleScreen) {
                    toggleLiveDirect(false)
                } else {
                    sendMainActivityIntent(MainActivity.ACTION_STOP_LIVE)
                }
            }
            // Always take a fresh screenshot — ScreenshotManager handles
            // rate limiting, and the cached file could be stale.
            controller.onDragStart()
        }
        icon.onDragMove = { rawX, rawY -> controller.onDragMove(rawX, rawY) }
        icon.onDragEnd = { controller.onDragEnd() }
        icon.onDragCancel = { controller.cancelDrag() }
        icon.onHoldCancel = { CaptureService.instance?.holdCancel() }
        // Pass the displayId through so P5 can route the one-shot to the
        // tapped icon's display. P2's holdStart still treats this as global
        // pause; the parameter just gets recorded.
        icon.onHoldStart  = { CaptureService.instance?.holdStart(displayId) }
        icon.onHoldEnd    = { CaptureService.instance?.holdEnd() }
        icon.onAnyTouch   = {
            // Track which display the user is interacting with so hotkey
            // one-shots route to the right place when more than one display
            // is selected (P5 wires this further into OneShotManager).
            CaptureService.instance?.lastInteractedDisplayId = displayId
            DimController.notifyInteraction()
        }
        if (addOverlayWindow(icon, wm, params, displayId)) {
            // Set position after addView from this display's saved slot.
            val pos = prefs.iconPositionForDisplay(displayId)
            icon.setPosition(pos.edge, pos.fraction)
            try { wm.updateViewLayout(icon, params) } catch (_: Exception) {}
            iconHandles[displayId] = FloatingIconHandle(
                icon = icon,
                wm = wm,
                dragController = controller,
                clearLivePauseFlag = clearLivePauseFlag,
            )
        } else {
            // Window install failed. Nothing to roll back from any map —
            // we never inserted a handle. Just destroy the controller we
            // built locally.
            controller.destroy()
        }

        // The old floatingIcon setter used to fire these on every install/
        // teardown; we keep that contract by triggering them explicitly.
        CaptureService.instance?.updateForegroundState()
        CaptureService.instance?.syncIconState()
    }

    /**
     * Remove and re-add floating icons so they draw above newly added
     * overlays. Pass [displayId] = null (default) to bring every icon
     * forward; pass an id to bring just one. Icons in drag mode are skipped
     * — re-adding mid-drag breaks the touch event sequence.
     */
    fun bringFloatingIconsToFront(displayId: Int? = null) {
        // The remove + re-add pair re-stacks the icon above newly-added overlays.
        // The handle in [iconHandles] is intentionally NOT mutated across this
        // call — view, wm, controller, and closure all stay the same instances.
        val targets: List<Map.Entry<Int, FloatingIconHandle>> = if (displayId != null) {
            listOfNotNull(iconHandles.entries.firstOrNull { it.key == displayId })
        } else {
            iconHandles.entries.toList()
        }
        for ((id, handle) in targets) {
            if (handle.icon.inDragMode) continue
            val params = handle.icon.params ?: continue
            removeOverlayWindow(handle.icon)
            addOverlayWindow(handle.icon, handle.wm, params, id)
        }
    }

    /** Tear down a single display's floating icon and its drag-lookup
     *  controller. Idempotent — no-op when no icon is registered for
     *  [displayId]. */
    private fun hideFloatingIconForDisplay(displayId: Int, reason: String) {
        val handle = iconHandles.remove(displayId) ?: return
        Log.i(TAG, "hideFloatingIcon[$displayId]: $reason")
        handle.dragController.destroy()
        handle.icon.destroy()
        removeOverlayWindow(handle.icon)

        CaptureService.instance?.updateForegroundState()
        CaptureService.instance?.syncIconState()
    }

    /** Tear down every floating icon. Used by callers that want to remove
     *  the icons entirely (task removed, user disabled the icon pref). */
    fun hideFloatingIcon(reason: String = "unspecified") {
        if (iconHandles.isEmpty()) return
        Log.i(TAG, "hideFloatingIcon (all): $reason")
        // Snapshot to a list since hideFloatingIconForDisplay mutates the map.
        val ids = iconHandles.keys.toList()
        for (id in ids) hideFloatingIconForDisplay(id, reason)
    }

    /** Called by [com.playtranslate.ui.DragLookupController.openSentenceInApp]
     *  before dismissing the magnifier so the dismiss-chain's resumeLiveMode
     *  is a no-op when the detail view will cover the live-mode surface.
     *  The "covering" predicate matches the service's own
     *  [effectivelySingleScreen]-style routing used elsewhere — single-screen
     *  OR dual-screen with MainActivity backgrounded both result in TRA
     *  taking over the user's view. Dual-screen with the in-app panel
     *  visible leaves auto-resume in place since TRA lands on the panel
     *  side and live captures continue on the game side. The user re-enables
     *  live mode manually via the floating-icon menu after closing the
     *  detail view.
     *
     *  Iterates all per-display flags — only one is realistically active at
     *  any time (one pointer means one drag), but invoking all is harmless
     *  and avoids a stale-id race. */
    fun cancelLivePauseObligation() {
        val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
        if (effectivelySingleScreen) {
            iconHandles.values.forEach { it.clearLivePauseFlag.invoke() }
        }
    }

    // ── Floating icon menu ────────────────────────────────────────────────

    private fun showFloatingMenu(display: Display, icon: FloatingOverlayIcon) {
        dismissFloatingMenu()
        val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return
        val screenSize = getDisplaySize(display)
        val themeRes = baseActivityTheme(this)
        val themedCtx = android.view.ContextThemeWrapper(displayCtx, themeRes)
        applyAccentOverlay(themedCtx.theme, this)
        val menu = FloatingIconMenu(themedCtx)
        menu.isSingleScreen = Prefs.isSingleScreen(this)

        // Suppress live captures while menu is open — the menu darkens
        // the screen and we don't want overlays appearing behind it.
        CaptureService.instance?.holdActive = true
        hideTranslationOverlay()

        val prefs = Prefs(this)
        val hintKind = SourceLanguageProfiles[prefs.sourceLangId].hintTextKind
        menu.hintModeLabel = if (prefs.overlayMode == OverlayMode.FURIGANA && hintKind != HintTextKind.NONE) {
            when (hintKind) { HintTextKind.PINYIN -> "Pinyin"; else -> "Furigana" }
        } else null
        menu.isLiveMode = CaptureService.instance?.isLive == true
        menu.degradedWarningKind =
            CaptureService.instance?.degradationState?.value
                ?: com.playtranslate.ui.DegradedWarningKind.None
        menu.onHideIcon = {
            dismissFloatingMenu()
            disable(this, "menu_turn_off")
        }
        menu.onHideTemporary = {
            dismissFloatingMenu()
            hideFloatingIcon("menu_hide_temporary")
        }
        menu.onCloseRequested = {
            dismissFloatingMenu()
            showHideConfirmAlert(display)
        }
        menu.onDismiss = {
            // Only refresh if the menu is still showing — other handlers
            // (onRegionSelected, onToggleLive, etc.) call dismissFloatingMenu
            // first, so floatingMenu would already be null.
            val needsRefresh = floatingMenu != null && CaptureService.instance?.isLive == true
            dismissFloatingMenu()
            if (needsRefresh) {
                CaptureService.instance?.refreshLiveOverlay()
            }
        }
        menu.onToggleLive = {
            dismissFloatingMenu()
            if (CaptureService.instance?.isLive == true) {
                // Stopping: same logic regardless of mode
                val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
                if (effectivelySingleScreen) {
                    toggleLiveDirect(false)
                } else {
                    sendMainActivityIntent(MainActivity.ACTION_STOP_LIVE)
                }
            } else {
                // Starting
                if (Prefs.shouldUseInAppOnlyMode(this)) {
                    // Dual screen + hide overlays + single display selected:
                    // bring app to foreground for In-App Only.
                    sendMainActivityIntent(MainActivity.ACTION_START_LIVE)
                } else {
                    val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
                    if (effectivelySingleScreen) {
                        toggleLiveDirect(true)
                    } else {
                        sendMainActivityIntent(MainActivity.ACTION_START_LIVE)
                    }
                }
            }
        }
        // The floating menu is anchored to a specific display; show that
        // display's region in the picker and route override writes to it.
        menu.activeRegion = CaptureService.instance?.activeRegionForDisplay(display.displayId)
        menu.onRegionSelected = { region ->
            dismissFloatingMenu()
            CaptureService.instance?.configureOverride(display.displayId, region)
            if (CaptureService.instance?.isLive == true) {
                hideTranslationOverlay()
                CaptureService.instance?.refreshLiveOverlay()
            } else {
                val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
                if (effectivelySingleScreen) {
                    handleRegionSelection(display.displayId, region)
                } else {
                    sendMainActivityIntent(MainActivity.ACTION_REGION_CAPTURE, display.displayId)
                }
            }
        }
        menu.onClearRegion = {
            // Reset this display's selected region to full screen.
            val prefs = Prefs(this)
            prefs.setSelectedRegionIdForDisplay(display.displayId, Prefs.DEFAULT_REGION_LIST[0].id)
            val svc = CaptureService.instance
            if (svc != null && svc.isConfigured) {
                // Drop any runtime override too — clearOverride re-resolves
                // the region from Prefs (now full screen) and refreshes
                // live mode for this display.
                svc.clearOverride(display.displayId)
            }
            if (MainActivity.isInForeground) {
                sendMainActivityIntent(MainActivity.ACTION_REFRESH_REGION_LABEL)
            }
        }
        menu.onToggleInspectMode = {
            val p = Prefs(this)
            p.inspectModeEnabled = !p.inspectModeEnabled
            dismissFloatingMenu()
            hideTranslationOverlay()
            CaptureService.instance?.refreshLiveOverlay()
        }
        menu.onSetTtsZone = { dismissFloatingMenu(); showTtsZoneEditor(display) }
        menu.onOpenTtsSettings = {
            dismissFloatingMenu()
            val intent = Intent(this@PlayTranslateAccessibilityService, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                action = "com.playtranslate.ACTION_OPEN_TTS_SETTINGS"
            }
            startActivity(intent)
        }
        menu.onCaptureRegion = {
            dismissFloatingMenu()
            val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
            if (effectivelySingleScreen) {
                showRegionEditor(display)
            } else {
                sendMainActivityIntent(MainActivity.ACTION_ADD_CUSTOM_REGION, display.displayId)
            }
        }
        menu.onSettings = {
            dismissFloatingMenu()
            sendMainActivityIntent(MainActivity.ACTION_OPEN_SETTINGS)
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )

        addOverlayWindow(menu, wm, params, display.displayId)
        floatingMenuWm = wm
        floatingMenu = menu

        // Compute icon center in screen coords
        val p = icon.params
        val iconCx = (p?.x ?: 0) + icon.viewSizePx / 2
        val iconCy = (p?.y ?: 0) + icon.viewSizePx / 2
        menu.positionNearIcon(iconCx, iconCy, icon.currentEdge, screenSize.x, screenSize.y)
    }

    private fun dismissFloatingMenu() {
        val wasShowing = floatingMenu != null
        floatingMenu?.let { removeOverlayWindow(it) }
        floatingMenu = null
        floatingMenuWm = null
        if (wasShowing) {
            CaptureService.instance?.holdActive = false
        }
    }

    private fun showHideConfirmAlert(display: android.view.Display) {
        val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val overlayWm = displayCtx.getSystemService(WindowManager::class.java) ?: return
        val appName = getString(R.string.app_name)
        val prefs = Prefs(this)
        val alreadyCompact = prefs.compactOverlayIcon

        val builder = OverlayAlert.Builder(displayCtx, overlayWm, display.displayId)

        if (!Prefs.hasMultipleDisplays(this)) {
            builder.setTitle("Disable $appName?")
                .setMessage("Re-enable in $appName app")
            if (!alreadyCompact) {
                builder.addButton("Minimize Icon", OverlayColors.accent(this)) {
                    prefs.compactOverlayIcon = true
                    hideFloatingIcon("confirm_minimize_single")
                    reconcileFloatingIcons()
                }
            }
            builder.addButton("Turn Off", OverlayColors.divider(this), OverlayColors.danger(this)) {
                    disable(this, "confirm_turn_off_single")
                }
                .addCancelButton()
        } else {
            builder.setTitle("Hide $appName game screen controls?")
            if (!alreadyCompact) {
                builder.setMessage("\u201CMinimize Icon\u201D shrinks the floating icon. \u201CTurn Off\u201D disables it until re-enabled in settings.")
                    .addButton("Minimize Icon", OverlayColors.accent(this)) {
                        prefs.compactOverlayIcon = true
                        hideFloatingIcon("confirm_minimize_multi")
                        reconcileFloatingIcons()
                    }
            } else {
                builder.setMessage("\u201CHide for Now\u201D brings it back next time you open $appName. \u201CTurn Off\u201D disables it until re-enabled in settings.")
                    .addButton("Hide for Now", OverlayColors.accent(this)) {
                        hideFloatingIcon("confirm_hide_for_now")
                    }
            }
            builder.addButton("Turn Off", OverlayColors.divider(this), OverlayColors.danger(this)) {
                    disable(this, "confirm_turn_off_multi")
                }
                .addCancelButton()
        }

        builder.show()
    }

    // ── Single-screen region editor ─────────────────────────────────────

    /**
     * Shows the RegionDragView pre-populated with the current capture region
     * plus a small floating bar with Use/Cancel buttons. Used on single-screen
     * devices (or when the app is backgrounded) where we can't show
     * AddCustomRegionSheet on a separate screen.
     */
    private fun showRegionEditor(display: Display) {
        hideRegionEditor()
        // Suppress live captures while editing
        CaptureService.instance?.holdActive = true
        hideTranslationOverlay()
        hideRegionOverlay()

        // Pre-populate with this display's current active region (or
        // default if full-screen). The region editor is anchored to the
        // display [showRegionEditor] was opened on.
        val currentRegion = CaptureService.instance?.activeRegionForDisplay(display.displayId)
        val initRegion = if (currentRegion == null || currentRegion.isFullScreen)
            RegionEntry("", 0.25f, 0.75f, 0.25f, 0.75f) else currentRegion

        showRegionDragOverlay(display, initRegion) { _ -> }
        dragView?.onDragStart = {
            regionEditorBar?.visibility = View.INVISIBLE
            regionEditorLabel?.visibility = View.INVISIBLE
        }
        dragView?.onDragEnd = {
            regionEditorBar?.visibility = View.VISIBLE
            regionEditorLabel?.visibility = View.VISIBLE
        }

        // Build floating Use / Cancel button bar
        val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return
        val dp = ctx.resources.displayMetrics.density
        val btnSize = (48 * dp).toInt()
        val barPad = (12 * dp).toInt()
        val gap = (16 * dp).toInt()

        val surfaceColor = OverlayColors.surface(this)
        val cardColor = OverlayColors.card(this)
        val dividerColor = OverlayColors.divider(this)
        val accentColorBtn = OverlayColors.accent(this)
        val accentOnColor = OverlayColors.accentOn(this)
        val textColor = OverlayColors.text(this)
        val surfaceAlpha = android.graphics.Color.argb(230,
            android.graphics.Color.red(surfaceColor),
            android.graphics.Color.green(surfaceColor),
            android.graphics.Color.blue(surfaceColor))
        val btnRadius = 16 * dp

        val bar = android.widget.LinearLayout(ctx).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(barPad * 2 - (9 * dp).toInt(), barPad, barPad * 2 - (9 * dp).toInt(), barPad)
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(surfaceAlpha)
                setStroke((1 * dp).toInt(), dividerColor)
                cornerRadius = 22 * dp
            }
        }

        // Cancel button (X)
        val cancelBtn = android.widget.TextView(ctx).apply {
            text = "\u2715"
            setTextColor(textColor)
            textSize = 22f
            gravity = Gravity.CENTER
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(cardColor)
                cornerRadius = btnRadius
            }
            layoutParams = android.widget.LinearLayout.LayoutParams(btnSize, btnSize).apply {
                marginEnd = gap
            }
            setOnClickListener {
                hideRegionEditor()
                if (CaptureService.instance?.isLive == true) {
                    CaptureService.instance?.refreshLiveOverlay()
                }
            }
        }

        // Use button (checkmark)
        val useBtn = android.widget.TextView(ctx).apply {
            text = "\u2713"
            setTextColor(accentOnColor)
            textSize = 22f
            gravity = Gravity.CENTER
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(accentColorBtn)
                cornerRadius = btnRadius
            }
            layoutParams = android.widget.LinearLayout.LayoutParams(btnSize, btnSize)
            setOnClickListener {
                val dv = dragView ?: return@setOnClickListener
                val drawnRegion = RegionEntry("Drawn Region", dv.topFraction, dv.bottomFraction, dv.leftFraction, dv.rightFraction)
                hideRegionEditor()
                CaptureService.instance?.configureOverride(display.displayId, drawnRegion)
                if (CaptureService.instance?.isLive == true) {
                    CaptureService.instance?.refreshLiveOverlay()
                } else {
                    handleRegionSelection(display.displayId, drawnRegion)
                }
            }
        }

        bar.addView(cancelBtn)
        bar.addView(useBtn)

        val barParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            y = (32 * dp).toInt()
        }

        addOverlayWindow(bar, wm, barParams, display.displayId)
        regionEditorBarWm = wm
        regionEditorBar = bar

        // Instruction label at top center
        val label = android.widget.TextView(ctx).apply {
            text = "Drag edges to restrict screen captures to this region"
            setTextColor(textColor)
            textSize = 14f
            gravity = Gravity.CENTER
            setPadding((16 * dp).toInt(), (12 * dp).toInt(), (16 * dp).toInt(), (12 * dp).toInt())
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(surfaceAlpha)
                setStroke((1 * dp).toInt(), dividerColor)
                cornerRadius = 100 * dp
            }
        }
        val screenW = getDisplaySize(display).x
        val maxLabelW = screenW - (32 * dp).toInt()
        label.setSingleLine(true)
        label.measure(
            View.MeasureSpec.makeMeasureSpec(maxLabelW, View.MeasureSpec.AT_MOST),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
        )
        val labelParams = WindowManager.LayoutParams(
            label.measuredWidth,
            label.measuredHeight,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = (16 * dp).toInt()
        }
        addOverlayWindow(label, wm, labelParams, display.displayId)
        regionEditorLabelWm = wm
        regionEditorLabel = label
    }

    private fun hideRegionEditor() {
        hideRegionDragOverlay()
        regionEditorBar?.let { removeOverlayWindow(it) }
        regionEditorBar = null
        regionEditorBarWm = null
        regionEditorLabel?.let { removeOverlayWindow(it) }
        regionEditorLabel = null
        regionEditorLabelWm = null
        CaptureService.instance?.holdActive = false
    }

    /**
     * Returns the floating icon's bounding rect in screen coordinates for
     * [displayId], or null if no icon is showing on that display. Used by
     * CaptureService to black out the icon area before OCR so it doesn't
     * interfere with text recognition.
     */
    fun getFloatingIconRect(displayId: Int): android.graphics.Rect? {
        val icon = iconHandles[displayId]?.icon ?: return null
        val p = icon.params ?: return null
        return android.graphics.Rect(p.x, p.y, p.x + icon.viewSizePx, p.y + icon.viewSizePx)
    }

    /**
     * Start/stop live mode directly without bringing MainActivity to the
     * foreground. Used on single-screen devices where showing the Activity
     * would cover the game.
     */
    private fun toggleLiveDirect(start: Boolean) {
        val svc = CaptureService.instance ?: return
        if (start) {
            // Live state is set by CaptureService.startLive() via LiveData
            // Dismiss any definition popup when entering live mode.
            val hadPopup = isAnyDragLookupPopupShowing
            dismissAllDragLookupPopups()
            if (!svc.isConfigured) {
                val prefs = Prefs(this)
                svc.configureSaved(displayIds = prefs.captureDisplayIds)
            }
            // Delay start if a popup was just dismissed so the compositor
            // has time to remove it before the first screenshot.
            if (hadPopup) {
                debugHandler.postDelayed({ svc.startLive() }, 100)
            } else {
                svc.startLive()
            }
        } else {
            svc.stopLive()
        }
    }

    private fun sendMainActivityIntent(action: String, targetDisplayId: Int? = null) {
        val intent = Intent(this, MainActivity::class.java).apply {
            this.action = action
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            if (targetDisplayId != null) {
                putExtra(MainActivity.EXTRA_TARGET_DISPLAY_ID, targetDisplayId)
            }
        }
        startActivity(intent)
    }

    /**
     * Routes a drag-selected region to the appropriate activity:
     * - If effectively single screen (or app not in foreground), captures the
     *   screenshot NOW (while the game is still visible) and passes the path
     *   to TranslationResultActivity so it can OCR the saved image.
     * - Otherwise, sends ACTION_REGION_CAPTURE to MainActivity (which is on a
     *   different display and doesn't cover the game).
     */
    private fun handleRegionSelection(displayId: Int, region: RegionEntry) {
        val effectivelySingleScreen = Prefs.isSingleScreen(this) || !MainActivity.isInForeground
        if (effectivelySingleScreen) {
            serviceScope.launch {
                val bitmap = screenshotManager?.requestClean(displayId)
                val intent = Intent(this@PlayTranslateAccessibilityService, com.playtranslate.ui.TranslationResultActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    putExtra(com.playtranslate.ui.TranslationResultActivity.EXTRA_TOP_FRAC, region.top)
                    putExtra(com.playtranslate.ui.TranslationResultActivity.EXTRA_BOTTOM_FRAC, region.bottom)
                    putExtra(com.playtranslate.ui.TranslationResultActivity.EXTRA_LEFT_FRAC, region.left)
                    putExtra(com.playtranslate.ui.TranslationResultActivity.EXTRA_RIGHT_FRAC, region.right)
                    putExtra(com.playtranslate.ui.TranslationResultActivity.EXTRA_TARGET_DISPLAY_ID, displayId)
                }
                if (bitmap != null) {
                    val path = savePreCapturedScreenshot(bitmap)
                    bitmap.recycle()
                    intent.putExtra(com.playtranslate.ui.TranslationResultActivity.EXTRA_SCREENSHOT_PATH, path)
                }
                // Pin the activity to the display the user just dragged on.
                // Without this, a backgrounded-app launch falls back to the
                // service's default-display routing and the result lands on
                // the wrong screen on dual-display setups.
                val opts = android.app.ActivityOptions.makeBasic()
                    .setLaunchDisplayId(displayId)
                    .toBundle()
                startActivity(intent, opts)
            }
        } else {
            val intent = Intent(this, MainActivity::class.java).apply {
                action = MainActivity.ACTION_REGION_CAPTURE
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(MainActivity.EXTRA_TOP_FRAC, region.top)
                putExtra(MainActivity.EXTRA_BOTTOM_FRAC, region.bottom)
                putExtra(MainActivity.EXTRA_LEFT_FRAC, region.left)
                putExtra(MainActivity.EXTRA_RIGHT_FRAC, region.right)
                putExtra(MainActivity.EXTRA_TARGET_DISPLAY_ID, displayId)
            }
            startActivity(intent)
        }
    }

    /**
     * Saves a pre-captured screenshot to the app's cache directory so it can
     * be loaded by TranslationResultActivity on single-screen devices.
     */
    private fun savePreCapturedScreenshot(bitmap: Bitmap): String? {
        return try {
            val dir = java.io.File(cacheDir, "screenshots").apply { mkdirs() }
            val file = java.io.File(dir, "precapture.jpg")
            file.outputStream().use { bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 90, it) }
            file.absolutePath
        } catch (e: Exception) {
            Log.e(TAG, "savePreCapturedScreenshot failed: ${e.message}")
            null
        }
    }

    /** Returns the capture display (game screen), or the only display on single-screen.
     *  Used by [reconcileFloatingIcons] as a fallback when [Prefs.captureDisplayIds]
     *  is unexpectedly empty. */
    private fun findIconDisplay(prefs: Prefs): Display? {
        val dm = getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
        val displays = dm.displays
        if (displays.size <= 1) return displays.firstOrNull()
        val primaryId = prefs.captureDisplayIds.firstOrNull()
            ?: Display.DEFAULT_DISPLAY
        return dm.getDisplay(primaryId) ?: displays.firstOrNull()
    }

    @Suppress("DEPRECATION")
    private fun getDisplaySize(display: Display): Point {
        val size = Point()
        display.getRealSize(size)
        return size
    }

    // ── Screenshot (legacy, kept for callers not yet migrated) ──────────
    // All new code should use screenshotManager.requestClean/requestRaw.


     else {
            displayCtx
        }
    }

    
    // KIẾN TRÚC MỚI: Dùng trực tiếp Context của Service để giữ nguyên Accessibility Token
     else {
            this.createDisplayContext(display) // Kế thừa token cho màn hình phụ
        }
    }
    
    companion object {
        private const val TAG = "PlayTranslateA11y"

        /** Non-null while the service is connected (i.e. user has it enabled).
         *  `
        // Hàm lấy WindowManager an toàn tuyệt đối chống Crash BadTokenException trong Game
         else {
                val dm = context.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
                val display = dm.getDisplay(displayId) ?: return context.getSystemService(WindowManager::class.java)
                context.createDisplayContext(display).getSystemService(WindowManager::class.java)
            }
        }

        @Volatile` because the field is written from the main thread
         *  (`onServiceConnected` / `onUnbind`) and read from many others —
         *  drag controllers, hotkey callbacks, ML Kit worker threads. Without
         *  the visibility barrier a stale non-null read could survive a
         *  service teardown. Mirrors [CaptureService.instance]'s annotation. */
        @Volatile
        var instance: PlayTranslateAccessibilityService? = null

        /** True only when the service has bound to this process — i.e. methods
         *  on [instance] will actually do something. Distinct from [isEnabled]:
         *  the user can have the service enabled in system Settings while
         *  Android has not yet bound it to our process (cold start, post-unbind
         *  rebinding). Action gates that need a working service (capture,
         *  drag mode, region edits) must use this; display-state gates
         *  ("does the user have permission") should use [isEnabled]. */
        val isConnected: Boolean get() = instance != null

        /** Whether the user has enabled this app's accessibility service in
         *  system Settings. Fast-paths to `instance != null` once the service
         *  has bound to our process; falls back to the authoritative system
         *  setting otherwise, so a cold-started activity (or the QS tile in a
         *  fresh process) doesn't see a stale "disabled" state during the
         *  window before `onServiceConnected` fires. */
        fun isEnabled(ctx: Context): Boolean {
            if (instance != null) return true
            val enabled = Settings.Secure.getString(
                ctx.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: return false
            val component = ComponentName(ctx, PlayTranslateAccessibilityService::class.java)
            val full = component.flattenToString()
            val short = component.flattenToShortString()
            return enabled.split(':').any { it.equals(full, ignoreCase = true) || it.equals(short, ignoreCase = true) }
        }

        /** Single source of truth for "PlayTranslate is going inactive". Writes
         *  the pref, stops live mode if running, hides the floating icon, and
         *  refreshes the QS tile. Safe to call when the service isn't bound —
         *  the icon-hide is a no-op (no icon to hide). */
        fun disable(ctx: Context, reason: String) {
            Prefs(ctx).showOverlayIcon = false
            CaptureService.instance?.let { if (it.isLive) it.stopLive() }
            instance?.hideFloatingIcon(reason)
            PlayTranslateTileService.TileSync.refresh(ctx)
        }

        /**
         * Static convenience for overlay owners that don't have a service
         * reference handy (MagnifierLens, WordLookupPopup, etc.). When the
         * service isn't connected the window is added without registration —
         * it just won't participate in clean-capture blanking.
         *
         * [displayId] must be the display the window will appear on so
         * [prepareForCleanCapture] can scope its blanking. There is no
         * default — silently falling back to [Display.DEFAULT_DISPLAY] for
         * a window actually shown on a secondary display would leak the
         * window into clean screenshots of that display.
         */
        fun addOverlay(
            view: View,
            wm: WindowManager,
            params: WindowManager.LayoutParams,
            displayId: Int,
        ): Boolean {
            instance?.let { return it.addOverlayWindow(view, wm, params, displayId) }
            applyFullScreenOverlayDefaults(params)
            return try { wm.addView(view, params); true } catch (_: Exception) { false }
        }

        /**
         * Defensive defaults for accessibility overlays that request the full
         * display via MATCH_PARENT × MATCH_PARENT. Sets [FLAG_LAYOUT_NO_LIMITS]
         * so the window isn't inset by system bars, and
         * [LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS] so it isn't inset by display
         * cutouts in portrait. Without these, a notch device reports a smaller
         * view than the display, which silently miscalibrates OCR-box overlay
         * coordinates (boxes drawn lower/right than the underlying text).
         *
         * Idempotent. Honors callers that explicitly set a non-DEFAULT
         * cutout mode — only the DEFAULT case is upgraded.
         */
        private fun applyFullScreenOverlayDefaults(params: WindowManager.LayoutParams) {
            val fullScreen =
                params.width == WindowManager.LayoutParams.MATCH_PARENT &&
                    params.height == WindowManager.LayoutParams.MATCH_PARENT
            if (!fullScreen) return
            params.flags = params.flags or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
            if (params.layoutInDisplayCutoutMode ==
                WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_DEFAULT
            ) {
                params.layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
            }
        }

        fun removeOverlay(view: View, wm: WindowManager) {
            // If the service is connected and the view is in the registry,
            // removeOverlayWindow handles both unregister + removeView. If
            // the view was added via the no-service fallback path of
            // [addOverlay] (service connected later), it's not in the
            // registry — fall through to a direct removeView so the window
            // doesn't leak.
            if (instance?.removeOverlayWindow(view) == true) return
            try { wm.removeView(view) } catch (_: Exception) {}
        }
    }
}


