package com.profitloop.blueauto;

import android.accessibilityservice.AccessibilityService;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.telecom.TelecomManager;
import android.text.TextUtils;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

import org.json.JSONObject;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class BlueAccessibilityService extends AccessibilityService {
    private static final Pattern TX_ID = Pattern.compile(
            "(?i)(?:transaction\\s*id|transactionid)(?:\\s+is)?\\s*[:#-]?\\s*(\\d{6,})");
    private static final int MAX_PROMPT_RETRIES = 100;
    private static final int MAX_PIN_WRITE_ATTEMPTS = 3;
    private static final int MAX_BUTTON_RETRIES = 24;

    private static volatile BlueAccessibilityService liveInstance;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable inspectAgain = () -> inspect(null);
    private long lastResultAt = 0L;
    private String retryCommandId = "";
    private String retryProfileId = "";
    private int promptRetries = 0;
    private boolean pinWorkScheduled = false;
    private boolean submitScheduled = false;

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        liveInstance = this;
        handler.postDelayed(inspectAgain, 250L);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        inspect(event);
    }

    private void inspect(AccessibilityEvent event) {
        JSONObject command = PendingCommandStore.getActiveUssd(this);
        if (command == null) {
            resetAutomation();
            return;
        }

        String commandId = command.optString("public_id", "");
        String profileId = command.optString("local_profile_id", "");
        prepareCommand(commandId, profileId);

        // Never target or submit a Phone field behind any Android keyguard. The Robot normally
        // removes a swipe-only lock before dialing; this also covers a screen re-locked mid-flow.
        if (DeviceLockState.isKeyguardLocked(this)) {
            scheduleInspection(commandId, profileId);
            return;
        }

        List<AccessibilityNodeInfo> roots = externalRoots();
        String visible = collectExternalText(roots, event);
        String normalized = normalize(visible);
        String state = command.optString("local_state", PendingCommandStore.LEASED);
        String operation = UssdCommandFactory.operation(command);
        String trustedResult = PendingCommandStore.AWAITING_RESULT.equals(state)
                ? trustedUssdResult(roots, operation) : "";
        String resultVisible = trustedResult;
        String resultNormalized = normalize(trustedResult);
        BlueMessageParser.Result parsedBlue = BlueMessageParser.parse(trustedResult);

        if (System.currentTimeMillis() - lastResultAt >= 800L) {
            if (parsedBlue.wrongPin || containsAny(resultNormalized,
                    "wrong pin code", "pin incorrect", "code pin incorrect", "code errone")) {
                lastResultAt = System.currentTimeMillis();
                AppConfig.setPinBlocked(this, profileId, true);
                RobotService.operatorResult(this, profileId, false, "WRONG_PIN",
                        safeScreenText(resultVisible, profileId), transactionId(resultVisible));
                clickTrustedTelephonyFirst(roots, "ok", "fermer", "close");
                resetAutomation();
                return;
            }

            if ((parsedBlue.terminalSuccess() || (!parsedBlue.processing && containsAny(resultNormalized, "processed successfully",
                    "successfully transferred", "transfer successfully", "you transfer")))
                    && resultBelongsToVerifiedSession(command)) {
                lastResultAt = System.currentTimeMillis();
                RobotService.operatorResult(this, profileId, true, "",
                        safeScreenText(resultVisible, profileId), transactionId(resultVisible));
                clickTrustedTelephonyFirst(roots, "ok", "fermer", "close");
                resetAutomation();
                return;
            }

            if ((parsedBlue.terminalFailure() || containsAny(resultNormalized, "insufficient", "not enough", "transaction failed", "request failed",
                    "operator is frozen", "operator is suspended", "invalid amount", "echec"))
                    && resultBelongsToVerifiedSession(command)) {
                lastResultAt = System.currentTimeMillis();
                RobotService.operatorResult(this, profileId, false, "OPERATOR_REJECTED",
                        safeScreenText(resultVisible, profileId), transactionId(resultVisible));
                clickTrustedTelephonyFirst(roots, "ok", "fermer", "close");
                resetAutomation();
                return;
            }
        }

        if (("BALANCE_OWN".equals(operation) || "BALANCE_CHILD".equals(operation))
                && !trustedResult.isEmpty()) {
            lastResultAt = System.currentTimeMillis();
            RobotService.operatorResult(this, profileId, true, "",
                    safeScreenText(trustedResult, profileId), transactionId(trustedResult));
            clickTrustedTelephonyFirst(roots, "ok", "fermer", "close");
            resetAutomation();
            return;
        }
        if ((isRecognizedInformationResult(operation, normalize(trustedResult))
                || isRecognizedAdministrationResult(operation, normalize(trustedResult)))
                && !trustedResult.isEmpty()) {
            lastResultAt = System.currentTimeMillis();
            RobotService.operatorResult(this, profileId, true, "",
                    safeScreenText(trustedResult, profileId), transactionId(trustedResult));
            clickTrustedTelephonyFirst(roots, "ok", "fermer", "close");
            resetAutomation();
            return;
        }
        if ("TEST_NUMBER".equals(operation)
                && PendingCommandStore.AWAITING_RESULT.equals(state)
                && !trustedResult.isEmpty()
                && !normalize(trustedResult).contains("pin")
                && normalize(trustedResult).matches("(?s).*\\d{9}.*")) {
            lastResultAt = System.currentTimeMillis();
            RobotService.operatorResult(this, profileId, true, "",
                    safeScreenText(trustedResult, profileId), transactionId(trustedResult));
            clickTrustedTelephonyFirst(roots, "ok", "fermer", "close");
            resetAutomation();
            return;
        }

        if (!UssdCommandFactory.requiresPin(command)) return;
        if (PendingCommandStore.PIN_SUBMITTED.equals(state)) {
            scheduleSubmit(commandId, profileId, 0, 0L);
            return;
        }
        if (!(PendingCommandStore.DIALING.equals(state) || PendingCommandStore.AWAITING_PIN.equals(state))) return;

        PromptTarget target = findVerifiedPrompt(command, roots);
        if (target == null) {
            if (hasDefiniteMismatch(command, roots)) {
                clickFirst(roots, "annuler", "cancel");
                RobotService.operatorResult(this, profileId, false, "CONFIRMATION_MISMATCH",
                        mismatchEvidence(command, visible, profileId), "");
                resetAutomation();
                return;
            }
            scheduleInspection(commandId, profileId);
            return;
        }

        if (!pinWorkScheduled) {
            pinWorkScheduled = true;
            handler.removeCallbacks(inspectAgain);
            handler.post(() -> attemptPinWrite(commandId, profileId, 0));
        }
    }

    private void attemptPinWrite(String commandId, String profileId, int attempt) {
        JSONObject command = PendingCommandStore.get(this, profileId);
        if (!isSamePending(command, commandId, PendingCommandStore.DIALING, PendingCommandStore.AWAITING_PIN)) {
            pinWorkScheduled = false;
            return;
        }

        PromptTarget target = findVerifiedPrompt(command, externalRoots());
        if (target == null) {
            pinWorkScheduled = false;
            scheduleInspection(commandId, profileId);
            return;
        }

        try {
            String pin = SecurePinStore.read(this, profileId);
            if (!pin.matches("\\d{4}")) throw new IllegalStateException("PIN local invalide.");
            if (fieldContainsPin(target.field, pin)) {
                markPinReady(commandId, profileId);
                return;
            }

            target.field.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            target.field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
            final int currentAttempt = attempt;
            handler.postDelayed(() -> {
                JSONObject current = PendingCommandStore.get(this, profileId);
                if (!isSamePending(current, commandId,
                        PendingCommandStore.DIALING, PendingCommandStore.AWAITING_PIN)) {
                    pinWorkScheduled = false;
                    return;
                }
                PromptTarget refreshed = findVerifiedPrompt(current, externalRoots());
                if (refreshed == null) {
                    retryPinWrite(commandId, profileId, currentAttempt);
                    return;
                }
                boolean accepted;
                if (currentAttempt == 0) {
                    accepted = pastePin(refreshed.field, pin);
                } else {
                    accepted = setText(refreshed.field, pin);
                }
                final boolean actionAccepted = accepted;
                handler.postDelayed(() -> verifyPinWrite(commandId, profileId,
                        currentAttempt, pin, actionAccepted), 260L);
            }, attempt == 0 ? 180L : 100L);
        } catch (Exception error) {
            pinWorkScheduled = false;
            RobotService.operatorResult(this, profileId, false, "PIN_DECRYPTION_FAILED",
                    "Impossible de lire le PIN chiffré local.", "");
            resetAutomation();
        }
    }

    private void verifyPinWrite(String commandId, String profileId, int attempt,
                                String pin, boolean actionAccepted) {
        JSONObject command = PendingCommandStore.get(this, profileId);
        if (!isSamePending(command, commandId, PendingCommandStore.DIALING, PendingCommandStore.AWAITING_PIN)) {
            pinWorkScheduled = false;
            return;
        }
        PromptTarget target = findVerifiedPrompt(command, externalRoots());
        boolean finalFallback = attempt + 1 >= MAX_PIN_WRITE_ATTEMPTS
                && actionAccepted && target != null && target.field.isVisibleToUser()
                && target.field.isFocused() && !DeviceLockState.isKeyguardLocked(this);
        // A first ACTION_SET_TEXT "true" is not proof of mutation on Android 11/OEM dialers. Try
        // the independent clipboard path before accepting the last focused and visible fallback.
        if (target != null && (fieldContainsPin(target.field, pin) || finalFallback)) {
            markPinReady(commandId, profileId);
            return;
        }
        retryPinWrite(commandId, profileId, attempt);
    }

    private void retryPinWrite(String commandId, String profileId, int attempt) {
        if (attempt + 1 >= MAX_PIN_WRITE_ATTEMPTS) {
            pinWorkScheduled = false;
            RobotService.operatorResult(this, profileId, false, "PIN_FIELD_REJECTED",
                    "Le champ Camtel est visible mais a refusé la saisie automatique après plusieurs méthodes.", "");
            resetAutomation();
            return;
        }
        handler.postDelayed(() -> attemptPinWrite(commandId, profileId, attempt + 1), 220L);
    }

    private void markPinReady(String commandId, String profileId) {
        PendingCommandStore.putBoolean(this, profileId, "confirmation_verified", true);
        PendingCommandStore.updateState(this, profileId, PendingCommandStore.PIN_SUBMITTED);
        pinWorkScheduled = false;
        scheduleSubmit(commandId, profileId, 0, 350L);
    }

    private void scheduleInspection(String commandId, String profileId) {
        JSONObject current = PendingCommandStore.get(this, profileId);
        if (!isSamePending(current, commandId,
                PendingCommandStore.DIALING, PendingCommandStore.AWAITING_PIN)) return;
        if (++promptRetries > MAX_PROMPT_RETRIES) {
            List<AccessibilityNodeInfo> roots = externalRoots();
            clickFirst(roots, "annuler", "cancel");
            RobotService.operatorResult(this, profileId, false, "PIN_PROMPT_NOT_ACCESSIBLE",
                    "Blue Magic n’a pas pu accéder au champ PIN Camtel dans le délai prévu.", "");
            resetAutomation();
            return;
        }
        handler.removeCallbacks(inspectAgain);
        handler.postDelayed(inspectAgain, 300L);
    }

    private void scheduleSubmit(String commandId, String profileId, int attempt, long delayMs) {
        if (submitScheduled && attempt == 0) return;
        submitScheduled = true;
        handler.postDelayed(() -> submitPin(commandId, profileId, attempt), delayMs);
    }

    private void submitPin(String commandId, String profileId, int attempt) {
        JSONObject current = PendingCommandStore.get(this, profileId);
        if (!isSamePending(current, commandId, PendingCommandStore.PIN_SUBMITTED)) {
            submitScheduled = false;
            return;
        }
        PromptTarget target = findVerifiedPrompt(current, externalRoots());
        boolean clicked = target != null && clickFirst(target.root,
                "envoyer", "send", "confirmer", "confirm", "valider", "submit", "ok");
        if (clicked) {
            PendingCommandStore.updateState(this, profileId, PendingCommandStore.AWAITING_RESULT);
            submitScheduled = false;
            resetCountersOnly();
            RobotService.pinSubmitted(this, profileId);
            return;
        }
        if (attempt >= MAX_BUTTON_RETRIES) {
            submitScheduled = false;
            RobotService.operatorResult(this, profileId, false, "CONFIRM_BUTTON_NOT_FOUND",
                    "Le PIN a été inséré, mais le bouton de validation Camtel n’est pas accessible.", "");
            resetAutomation();
            return;
        }
        handler.postDelayed(() -> submitPin(commandId, profileId, attempt + 1), 250L);
    }

    private PromptTarget findVerifiedPrompt(JSONObject command, List<AccessibilityNodeInfo> roots) {
        String expectedPhone = digits(command.optString("target_phone", ""));
        String expectedAmount = digits(command.optString("amount", "").replaceFirst("\\.0+$", ""));
        for (AccessibilityNodeInfo root : roots) {
            String text = collectText(root);
            String normalized = normalize(text);
            if (!isPinPrompt(normalized)
                    || !confirmationMatches(normalized, expectedPhone, expectedAmount)) continue;
            AccessibilityNodeInfo field = findBestEditable(root);
            if (field != null) return new PromptTarget(root, field);
        }
        return null;
    }

    private boolean hasDefiniteMismatch(JSONObject command, List<AccessibilityNodeInfo> roots) {
        String expectedPhone = digits(command.optString("target_phone", ""));
        String expectedAmount = digits(command.optString("amount", "").replaceFirst("\\.0+$", ""));
        for (AccessibilityNodeInfo root : roots) {
            String text = normalize(collectText(root));
            if (isPinPrompt(text) && confirmationHasDefiniteMismatch(text, expectedPhone, expectedAmount)) return true;
        }
        return false;
    }

    private List<AccessibilityNodeInfo> externalRoots() {
        List<AccessibilityNodeInfo> roots = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        try {
            List<AccessibilityWindowInfo> windows = getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) addExternalRoot(roots, seen, window.getRoot());
            }
        } catch (Exception ignored) {
        }
        addExternalRoot(roots, seen, getRootInActiveWindow());
        return roots;
    }

    private void addExternalRoot(List<AccessibilityNodeInfo> roots, Set<String> seen,
                                 AccessibilityNodeInfo root) {
        if (root == null) return;
        CharSequence packageName = root.getPackageName();
        String owner = packageName == null ? "" : packageName.toString();
        if (getPackageName().equals(owner)) return;
        String identity = owner + ":" + root.getWindowId();
        if (seen.add(identity)) roots.add(root);
    }

    private String collectExternalText(List<AccessibilityNodeInfo> roots, AccessibilityEvent event) {
        StringBuilder result = new StringBuilder();
        for (AccessibilityNodeInfo root : roots) appendText(root, result);
        if (event != null && event.getPackageName() != null
                && !getPackageName().contentEquals(event.getPackageName())) {
            for (CharSequence text : event.getText()) {
                if (!TextUtils.isEmpty(text)) result.append(text).append(' ');
            }
            if (!TextUtils.isEmpty(event.getContentDescription())) {
                result.append(event.getContentDescription()).append(' ');
            }
        }
        return result.toString().trim();
    }

    private static String collectText(AccessibilityNodeInfo root) {
        StringBuilder result = new StringBuilder();
        appendText(root, result);
        return result.toString().trim();
    }

    private static void appendText(AccessibilityNodeInfo node, StringBuilder output) {
        if (node == null) return;
        CharSequence text = node.getText();
        if (!TextUtils.isEmpty(text)) output.append(text).append(' ');
        CharSequence description = node.getContentDescription();
        if (!TextUtils.isEmpty(description)) output.append(description).append(' ');
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            CharSequence hint = node.getHintText();
            if (!TextUtils.isEmpty(hint)) output.append(hint).append(' ');
        }
        for (int i = 0; i < node.getChildCount(); i++) appendText(node.getChild(i), output);
    }

    private AccessibilityNodeInfo findBestEditable(AccessibilityNodeInfo root) {
        List<AccessibilityNodeInfo> nodes = new ArrayList<>();
        flatten(root, nodes);
        AccessibilityNodeInfo best = null;
        int bestScore = -1;
        for (AccessibilityNodeInfo node : nodes) {
            CharSequence className = node.getClassName();
            boolean supportsSetText = supportsAction(node, AccessibilityNodeInfo.ACTION_SET_TEXT);
            boolean editText = className != null && className.toString().contains("EditText");
            if (!(node.isEditable() || supportsSetText || editText)
                    || !node.isVisibleToUser()) continue;
            int score = 0;
            if (node.isFocused()) score += 8;
            if (node.isEditable()) score += 4;
            if (supportsSetText) score += 3;
            if (editText) score += 2;
            if (score > bestScore) {
                best = node;
                bestScore = score;
            }
        }
        return best;
    }

    private static boolean supportsAction(AccessibilityNodeInfo node, int actionId) {
        for (AccessibilityNodeInfo.AccessibilityAction action : node.getActionList()) {
            if (action.getId() == actionId) return true;
        }
        return false;
    }

    private static boolean setText(AccessibilityNodeInfo field, String pin) {
        Bundle args = new Bundle();
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, pin);
        return field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
    }

    private boolean pastePin(AccessibilityNodeInfo field, String pin) {
        ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        if (clipboard == null) return false;
        ClipData previous = null;
        try {
            if (clipboard.hasPrimaryClip()) previous = clipboard.getPrimaryClip();
        } catch (Exception ignored) {
        }
        try {
            clipboard.setPrimaryClip(ClipData.newPlainText("Blue Magic", pin));
            field.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
            boolean pasted = field.performAction(AccessibilityNodeInfo.ACTION_PASTE);
            clipboard.setPrimaryClip(previous == null
                    ? ClipData.newPlainText("", "") : previous);
            return pasted;
        } catch (Exception ignored) {
            try {
                clipboard.setPrimaryClip(previous == null
                        ? ClipData.newPlainText("", "") : previous);
            } catch (Exception ignoredAgain) {
            }
            return false;
        }
    }

    private static boolean fieldContainsPin(AccessibilityNodeInfo field, String pin) {
        CharSequence value = field == null ? null : field.getText();
        if (TextUtils.isEmpty(value)) return false;
        String text = value.toString();
        String numeric = digits(text);
        if (pin.equals(numeric)) return true;
        String compact = text.replaceAll("\\s+", "");
        return compact.matches("[•●∙*×]{4}");
    }

    private static boolean confirmationMatches(String text, String phone, String amount) {
        String compactDigits = digits(text);
        boolean phoneMatches = phone.length() == 9 && compactDigits.contains(phone);
        boolean amountMatches = !amount.isEmpty() && Pattern.compile(
                "(?i)(?<!\\d)" + Pattern.quote(amount)
                        + "(?:[.,]00)?\\s*(?:f\\s*cfa|fcfa|xaf)(?!\\w)")
                .matcher(text).find();
        return phoneMatches && amountMatches;
    }

    private static boolean confirmationHasDefiniteMismatch(String text, String phone, String amount) {
        Matcher phoneMatcher = Pattern.compile("(?<!\\d)(6\\d{8})(?!\\d)")
                .matcher(text.replaceAll("[ ._-]", ""));
        boolean sawPhone = false;
        boolean expectedPhoneSeen = false;
        while (phoneMatcher.find()) {
            sawPhone = true;
            if (phone.equals(phoneMatcher.group(1))) expectedPhoneSeen = true;
        }
        Matcher amountMatcher = Pattern.compile(
                "(?i)(?<!\\d)(\\d{1,9})(?:[.,]00)?\\s*(?:f\\s*cfa|fcfa|xaf)").matcher(text);
        boolean sawAmount = false;
        boolean expectedAmountSeen = false;
        while (amountMatcher.find()) {
            sawAmount = true;
            if (amount.equals(amountMatcher.group(1))) expectedAmountSeen = true;
        }
        return (sawPhone && !expectedPhoneSeen) || (sawAmount && !expectedAmountSeen);
    }

    private String mismatchEvidence(JSONObject command, String visible, String profileId) {
        String expectedPhone = digits(command.optString("target_phone", ""));
        String expectedAmount = digits(command.optString("amount", "").replaceFirst("\\.0+$", ""));
        String observed = safeScreenText(visible == null ? "" : visible, profileId)
                .replaceAll("\\s+", " ").trim();
        if (observed.length() > 700) observed = observed.substring(0, 700);
        return "Transaction annulée avant PIN. Attendu : destinataire " + expectedPhone
                + ", montant " + expectedAmount + " FCFA. Capture textuelle Camtel : "
                + (observed.isEmpty() ? "contenu inaccessible" : observed);
    }

    private static boolean resultBelongsToVerifiedSession(JSONObject command) {
        return !UssdCommandFactory.requiresPin(command)
                || command.optBoolean("confirmation_verified", false);
    }

    private static boolean isRecognizedInformationResult(String operation, String text) {
        if ("HISTORY_LAST5".equals(operation)) {
            return containsAny(text, "transaction", "historique", "last transaction")
                    && text.matches("(?s).*\\d{4,}.*");
        }
        if ("TRANSACTION_DETAIL".equals(operation)) {
            return containsAny(text, "transaction", "detail")
                    && containsAny(text, "montant", "amount", "fcfa", "xaf", "id");
        }
        return false;
    }

    private static boolean isRecognizedAdministrationResult(String operation, String text) {
        if ("INIT_CHILD_PIN_RESET".equals(operation)) {
            return text.contains("pin") && containsAny(text, "reset", "reinitial")
                    && containsAny(text, "init", "demarr", "started", "code");
        }
        if ("SUSPEND_CHILD".equals(operation)) {
            return containsAny(text, "suspendu avec succes", "successfully suspended");
        }
        if ("REACTIVATE_CHILD".equals(operation)
                || "REACTIVATE_FROZEN_CHILD".equals(operation)) {
            return containsAny(text, "reactive avec succes", "successfully reactivated");
        }
        if ("FREEZE_SELF".equals(operation) || "FREEZE_CHILD".equals(operation)) {
            return containsAny(text, "gele avec succes", "successfully frozen");
        }
        return false;
    }

    /** Returns one matching Phone/Telecom window, never concatenated text from other apps. */
    private String trustedUssdResult(List<AccessibilityNodeInfo> roots, String operation) {
        for (AccessibilityNodeInfo root : roots) {
            if (!isTrustedTelephonyRoot(root)) continue;
            String text = collectText(root);
            String normalized = normalize(text);
            if (normalized.isEmpty() || normalized.contains("ussd code running")) continue;
            if (containsAny(normalized, "processed successfully", "request is processed successfully",
                    "successfully transferred", "transfer successfully", "you transfer",
                    "insufficient", "not enough", "transaction failed", "request failed",
                    "operator is frozen", "operator is suspended", "invalid amount", "echec")) {
                return text;
            }
            if (containsAny(normalized,
                    "wrong pin code", "pin incorrect", "code pin incorrect", "code errone")) return text;
            if (("BALANCE_OWN".equals(operation) || "BALANCE_CHILD".equals(operation))
                    && containsAny(normalized, "solde", "balance")
                    && containsAny(normalized, "fcfa", "f cfa", "xaf")) return text;
            if (isRecognizedInformationResult(operation, normalized)
                    || isRecognizedAdministrationResult(operation, normalized)) return text;
            if ("TEST_NUMBER".equals(operation) && !normalized.contains("pin")
                    && normalized.matches("(?s).*\\d{9}.*")) return text;
        }
        return "";
    }

    private boolean isTrustedTelephonyRoot(AccessibilityNodeInfo root) {
        String packageName = root == null || root.getPackageName() == null
                ? "" : root.getPackageName().toString();
        if (packageName.isEmpty() || getPackageName().equals(packageName)) return false;
        try {
            TelecomManager telecom = (TelecomManager) getSystemService(TELECOM_SERVICE);
            if (telecom != null && packageName.equals(telecom.getDefaultDialerPackage())) return true;
        } catch (Exception ignored) {
        }
        if ("com.android.phone".equals(packageName)
                || "com.android.dialer".equals(packageName)
                || "com.google.android.dialer".equals(packageName)
                || "com.samsung.android.dialer".equals(packageName)
                || "com.samsung.android.incallui".equals(packageName)
                || "com.android.incallui".equals(packageName)
                || "com.mediatek.ussd".equals(packageName)
                || "com.mediatek.phone".equals(packageName)) return true;
        try {
            ApplicationInfo info = getPackageManager().getApplicationInfo(packageName, 0);
            boolean system = (info.flags & (ApplicationInfo.FLAG_SYSTEM
                    | ApplicationInfo.FLAG_UPDATED_SYSTEM_APP)) != 0;
            String lower = packageName.toLowerCase(Locale.ROOT);
            return system && (lower.contains("phone") || lower.contains("dialer")
                    || lower.contains("telecom") || lower.contains("ussd")
                    || lower.contains("incall"));
        } catch (PackageManager.NameNotFoundException ignored) {
            return false;
        }
    }

    private boolean clickTrustedTelephonyFirst(List<AccessibilityNodeInfo> roots, String... labels) {
        for (AccessibilityNodeInfo root : roots) {
            if (isTrustedTelephonyRoot(root) && clickFirst(root, labels)) return true;
        }
        return false;
    }

    private static boolean isPinPrompt(String text) {
        return text.contains("pin") && containsAny(text,
                "confirm", "confirmer", "enter", "saisir", "transfer balance", "code pin");
    }

    private static boolean clickFirst(List<AccessibilityNodeInfo> roots, String... labels) {
        for (AccessibilityNodeInfo root : roots) if (clickFirst(root, labels)) return true;
        return false;
    }

    private static boolean clickFirst(AccessibilityNodeInfo root, String... labels) {
        List<AccessibilityNodeInfo> nodes = new ArrayList<>();
        flatten(root, nodes);
        for (String label : labels) {
            for (AccessibilityNodeInfo node : nodes) {
                String text = normalize(node.getText() == null ? "" : node.getText().toString().trim());
                String description = normalize(node.getContentDescription() == null
                        ? "" : node.getContentDescription().toString().trim());
                if (text.equals(label) || text.contains(label)
                        || description.equals(label) || description.contains(label)) {
                    AccessibilityNodeInfo clickable = node;
                    while (clickable != null && !clickable.isClickable()) clickable = clickable.getParent();
                    if (clickable != null && clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true;
                }
            }
        }
        return false;
    }

    private static void flatten(AccessibilityNodeInfo node, List<AccessibilityNodeInfo> output) {
        if (node == null) return;
        output.add(node);
        for (int i = 0; i < node.getChildCount(); i++) flatten(node.getChild(i), output);
    }

    private void prepareCommand(String commandId, String profileId) {
        if (commandId.equals(retryCommandId) && profileId.equals(retryProfileId)) return;
        resetAutomation();
        retryCommandId = commandId;
        retryProfileId = profileId;
    }

    private static boolean isSamePending(JSONObject command, String commandId, String... states) {
        if (command == null || !commandId.equals(command.optString("public_id", ""))) return false;
        String current = command.optString("local_state", "");
        for (String state : states) if (state.equals(current)) return true;
        return false;
    }

    private void resetCountersOnly() {
        handler.removeCallbacks(inspectAgain);
        promptRetries = 0;
        pinWorkScheduled = false;
    }

    private void resetAutomation() {
        handler.removeCallbacksAndMessages(null);
        retryCommandId = "";
        retryProfileId = "";
        promptRetries = 0;
        pinWorkScheduled = false;
        submitScheduled = false;
    }

    private String safeScreenText(String value, String profileId) {
        try {
            String pin = SecurePinStore.read(this, profileId);
            if (!pin.isEmpty()) value = value.replace(pin, "****");
        } catch (Exception ignored) {
        }
        return value.length() <= 1800 ? value : value.substring(0, 1800);
    }

    private static String transactionId(String text) {
        Matcher matcher = TX_ID.matcher(text);
        return matcher.find() ? matcher.group(1) : "";
    }

    private static String normalize(String value) {
        String plain = Normalizer.normalize(value == null ? "" : value, Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "");
        return plain.toLowerCase(Locale.ROOT).replace('\u00a0', ' ').trim();
    }

    private static String digits(String value) {
        return value == null ? "" : value.replaceAll("\\D", "");
    }

    private static boolean containsAny(String value, String... needles) {
        for (String needle : needles) if (value.contains(needle)) return true;
        return false;
    }

    static boolean isEnabled(Context context) {
        String enabled = Settings.Secure.getString(
                context.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (enabled == null) return false;
        String expected = new ComponentName(context, BlueAccessibilityService.class).flattenToString();
        TextUtils.SimpleStringSplitter splitter = new TextUtils.SimpleStringSplitter(':');
        splitter.setString(enabled);
        while (splitter.hasNext()) {
            if (expected.equalsIgnoreCase(splitter.next())) return true;
        }
        return false;
    }

    static void kick(Context context) {
        BlueAccessibilityService service = liveInstance;
        if (service == null) return;
        service.handler.removeCallbacks(service.inspectAgain);
        service.handler.postDelayed(service.inspectAgain, 350L);
    }

    static void cancelVisiblePrompt(Context context, String profileId) {
        BlueAccessibilityService service = liveInstance;
        if (service == null) return;
        service.handler.post(() -> {
            JSONObject current = PendingCommandStore.get(service, profileId);
            if (current == null) return;
            List<AccessibilityNodeInfo> roots = service.externalRoots();
            if (!clickFirst(roots, "annuler", "cancel", "fermer", "close")) {
                service.performGlobalAction(GLOBAL_ACTION_BACK);
            }
            service.resetAutomation();
        });
    }

    @Override
    public void onInterrupt() {
        resetAutomation();
    }

    @Override
    public void onDestroy() {
        if (liveInstance == this) liveInstance = null;
        resetAutomation();
        super.onDestroy();
    }

    private static final class PromptTarget {
        final AccessibilityNodeInfo root;
        final AccessibilityNodeInfo field;

        PromptTarget(AccessibilityNodeInfo root, AccessibilityNodeInfo field) {
            this.root = root;
            this.field = field;
        }
    }
}
