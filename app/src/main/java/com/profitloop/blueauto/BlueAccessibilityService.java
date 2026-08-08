package com.profitloop.blueauto;

import android.accessibilityservice.AccessibilityService;
import android.content.ComponentName;
import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
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
    private static final int MAX_PROMPT_RETRIES = 85;
    private static final int MAX_BUTTON_RETRIES = 20;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable inspectAgain = () -> inspect(null);
    private long lastResultAt = 0L;
    private String retryCommandId = "";
    private int promptRetries = 0;
    private boolean insertingPin = false;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        inspect(event);
    }

    private void inspect(AccessibilityEvent event) {
        JSONObject command = PendingCommandStore.get(this);
        if (command == null) {
            resetRetries();
            return;
        }

        List<AccessibilityNodeInfo> roots = externalRoots();
        String visible = collectExternalText(roots, event);
        String normalized = normalize(visible);

        if (System.currentTimeMillis() - lastResultAt >= 800L) {
            if (containsAny(normalized, "wrong pin code", "pin incorrect", "code pin incorrect", "code errone")) {
                lastResultAt = System.currentTimeMillis();
                AppConfig.setPinBlocked(this, true);
                RobotService.operatorResult(this, false, "WRONG_PIN", safeScreenText(visible), transactionId(visible));
                clickFirst(roots, "ok", "fermer", "close");
                resetRetries();
                return;
            }

            if (containsAny(normalized, "processed successfully", "request is processed successfully",
                    "successfully transferred", "transfer successfully", "you transfer")) {
                lastResultAt = System.currentTimeMillis();
                RobotService.operatorResult(this, true, "", safeScreenText(visible), transactionId(visible));
                clickFirst(roots, "ok", "fermer", "close");
                resetRetries();
                return;
            }

            if (containsAny(normalized, "insufficient", "not enough", "transaction failed", "request failed",
                    "operator is frozen", "operator is suspended", "invalid amount", "echec")) {
                lastResultAt = System.currentTimeMillis();
                RobotService.operatorResult(this, false, "OPERATOR_REJECTED",
                        safeScreenText(visible), transactionId(visible));
                clickFirst(roots, "ok", "fermer", "close");
                resetRetries();
                return;
            }
        }

        String state = command.optString("local_state", PendingCommandStore.LEASED);
        if ("TEST_NUMBER".equals(command.optString("operation"))
                && PendingCommandStore.AWAITING_RESULT.equals(state)
                && !normalized.contains("pin")
                && normalized.matches("(?s).*\\d{9}.*")) {
            lastResultAt = System.currentTimeMillis();
            RobotService.operatorResult(this, true, "", safeScreenText(visible), transactionId(visible));
            clickFirst(roots, "ok", "fermer", "close");
            resetRetries();
            return;
        }

        if (!UssdCommandFactory.requiresPin(command)) return;
        if (PendingCommandStore.PIN_SUBMITTED.equals(state)) {
            scheduleSubmit(command.optString("public_id", ""), 0);
            return;
        }
        if (!(PendingCommandStore.DIALING.equals(state) || PendingCommandStore.AWAITING_PIN.equals(state))) return;

        String commandId = command.optString("public_id", "");
        if (!commandId.equals(retryCommandId)) {
            retryCommandId = commandId;
            promptRetries = 0;
        }

        boolean promptVisible = isPinPrompt(normalized);
        AccessibilityNodeInfo field = findEditable(roots);
        if (!promptVisible || field == null) {
            scheduleInspection(commandId);
            return;
        }

        String expectedPhone = digits(command.optString("target_phone", ""));
        String expectedAmount = digits(command.optString("amount", "").replaceFirst("\\.0+$", ""));
        if (!confirmationMatches(normalized, expectedPhone, expectedAmount)) {
            if (confirmationHasDefiniteMismatch(normalized, expectedPhone, expectedAmount)) {
                clickFirst(roots, "annuler", "cancel");
                RobotService.operatorResult(this, false, "CONFIRMATION_MISMATCH",
                        "Le numéro ou le montant affiché par Camtel ne correspond pas à l’ordre attendu.", "");
                resetRetries();
                return;
            }
            scheduleInspection(commandId);
            return;
        }

        if (insertingPin) return;
        insertingPin = true;
        handler.removeCallbacks(inspectAgain);
        try {
            String pin = SecurePinStore.read(this);
            field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
            Bundle args = new Bundle();
            args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, pin);
            if (!field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) {
                insertingPin = false;
                scheduleInspection(commandId);
                return;
            }

            PendingCommandStore.updateState(this, PendingCommandStore.PIN_SUBMITTED);
            handler.postDelayed(() -> scheduleSubmit(commandId, 0), 450L);
        } catch (Exception error) {
            insertingPin = false;
            RobotService.operatorResult(this, false, "PIN_DECRYPTION_FAILED",
                    "Impossible de lire le PIN chiffré local.", "");
            resetRetries();
        }
    }

    private void scheduleInspection(String commandId) {
        JSONObject current = PendingCommandStore.get(this);
        if (current == null || !commandId.equals(current.optString("public_id", ""))) return;
        if (++promptRetries > MAX_PROMPT_RETRIES) {
            List<AccessibilityNodeInfo> roots = externalRoots();
            clickFirst(roots, "annuler", "cancel");
            RobotService.operatorResult(this, false, "PIN_PROMPT_NOT_ACCESSIBLE",
                    "Blue Magic n’a pas pu accéder au champ PIN Camtel dans les 30 secondes.", "");
            resetRetries();
            return;
        }
        handler.removeCallbacks(inspectAgain);
        handler.postDelayed(inspectAgain, 350L);
    }

    private void scheduleSubmit(String commandId, int attempt) {
        JSONObject current = PendingCommandStore.get(this);
        if (current == null || !commandId.equals(current.optString("public_id", ""))
                || !PendingCommandStore.PIN_SUBMITTED.equals(current.optString("local_state", ""))) {
            insertingPin = false;
            return;
        }
        List<AccessibilityNodeInfo> roots = externalRoots();
        if (clickFirst(roots, "envoyer", "send", "confirmer", "confirm", "valider", "submit", "ok")) {
            PendingCommandStore.updateState(this, PendingCommandStore.AWAITING_RESULT);
            insertingPin = false;
            resetRetries();
            RobotService.pinSubmitted(this);
            return;
        }
        if (attempt >= MAX_BUTTON_RETRIES) {
            insertingPin = false;
            RobotService.operatorResult(this, false, "CONFIRM_BUTTON_NOT_FOUND",
                    "Le PIN a été inséré, mais le bouton de validation Camtel n’est pas accessible.", "");
            resetRetries();
            return;
        }
        handler.postDelayed(() -> scheduleSubmit(commandId, attempt + 1), 300L);
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
        Matcher phoneMatcher = Pattern.compile("(?<!\\d)(6\\d{8})(?!\\d)").matcher(text.replaceAll("[ ._-]", ""));
        boolean anotherPhone = phoneMatcher.find() && !phone.equals(phoneMatcher.group(1));
        Matcher amountMatcher = Pattern.compile("(?i)(?<!\\d)(\\d{1,9})(?:[.,]00)?\\s*(?:f\\s*cfa|fcfa|xaf)")
                .matcher(text);
        boolean anotherAmount = amountMatcher.find() && !amount.equals(amountMatcher.group(1));
        return anotherPhone || anotherAmount;
    }

    private static boolean isPinPrompt(String text) {
        return text.contains("pin") && containsAny(text,
                "confirm", "confirmer", "enter", "saisir", "transfer balance", "code pin");
    }

    private static AccessibilityNodeInfo findEditable(List<AccessibilityNodeInfo> roots) {
        for (AccessibilityNodeInfo root : roots) {
            AccessibilityNodeInfo result = findEditable(root);
            if (result != null) return result;
        }
        return null;
    }

    private static AccessibilityNodeInfo findEditable(AccessibilityNodeInfo node) {
        if (node == null) return null;
        CharSequence className = node.getClassName();
        boolean supportsSetText = false;
        for (AccessibilityNodeInfo.AccessibilityAction action : node.getActionList()) {
            if (action.getId() == AccessibilityNodeInfo.ACTION_SET_TEXT) {
                supportsSetText = true;
                break;
            }
        }
        if (node.isEditable() || supportsSetText
                || (className != null && className.toString().contains("EditText"))) return node;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo result = findEditable(node.getChild(i));
            if (result != null) return result;
        }
        return null;
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

    private void resetRetries() {
        handler.removeCallbacks(inspectAgain);
        retryCommandId = "";
        promptRetries = 0;
        insertingPin = false;
    }

    private String safeScreenText(String value) {
        try {
            String pin = SecurePinStore.read(this);
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

    @Override
    public void onInterrupt() {
        resetRetries();
    }

    @Override
    public void onDestroy() {
        resetRetries();
        super.onDestroy();
    }
}
