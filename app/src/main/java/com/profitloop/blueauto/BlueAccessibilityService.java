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

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class BlueAccessibilityService extends AccessibilityService {
    private static final Pattern TX_ID = Pattern.compile("(?i)(?:transaction\\s*id|transactionid)(?:\\s+is)?\\s*[:#-]?\\s*(\\d{6,})");
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long lastActionAt = 0L;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        JSONObject command = PendingCommandStore.get(this);
        if (command == null || System.currentTimeMillis() - lastActionAt < 300L) return;

        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;
        String visible = collectText(root);
        String lower = visible.toLowerCase(Locale.ROOT);

        if (containsAny(lower, "wrong pin code", "pin incorrect", "code pin incorrect", "code erroné")) {
            AppConfig.setPinBlocked(this, true);
            lastActionAt = System.currentTimeMillis();
            RobotService.operatorResult(this, false, "WRONG_PIN", safeScreenText(visible), transactionId(visible));
            clickFirst(root, "ok", "fermer", "close");
            return;
        }

        if (containsAny(lower, "processed successfully", "request is processed successfully",
                "successfully transferred", "transfer successfully", "you transfer")) {
            lastActionAt = System.currentTimeMillis();
            RobotService.operatorResult(this, true, "", safeScreenText(visible), transactionId(visible));
            clickFirst(root, "ok", "fermer", "close");
            return;
        }

        if (containsAny(lower, "insufficient", "not enough", "transaction failed", "request failed",
                "operator is frozen", "operator is suspended", "invalid amount", "échec")) {
            lastActionAt = System.currentTimeMillis();
            RobotService.operatorResult(this, false, "OPERATOR_REJECTED", safeScreenText(visible), transactionId(visible));
            clickFirst(root, "ok", "fermer", "close");
            return;
        }

        String state = command.optString("local_state", PendingCommandStore.LEASED);
        if ("TEST_NUMBER".equals(command.optString("operation"))
                && PendingCommandStore.AWAITING_RESULT.equals(state)
                && !lower.contains("pin")
                && lower.matches("(?s).*\\d{9}.*")) {
            lastActionAt = System.currentTimeMillis();
            RobotService.operatorResult(this, true, "", safeScreenText(visible), transactionId(visible));
            clickFirst(root, "ok", "fermer", "close");
            return;
        }
        if (!UssdCommandFactory.requiresPin(command)
                || !(PendingCommandStore.DIALING.equals(state) || PendingCommandStore.AWAITING_PIN.equals(state))) {
            return;
        }

        if (!isPinPrompt(lower)) return;

        String expectedPhone = command.optString("target_phone", "").replaceAll("\\D", "");
        String expectedAmount = command.optString("amount", "").replaceFirst("\\.0+$", "").replaceAll("\\D", "");
        if (!confirmationMatches(lower, expectedPhone, expectedAmount)) {
            lastActionAt = System.currentTimeMillis();
            clickFirst(root, "annuler", "cancel");
            RobotService.operatorResult(this, false, "CONFIRMATION_MISMATCH",
                    "Le numéro ou le montant affiché par Camtel ne correspond pas à l’ordre attendu.", "");
            return;
        }

        try {
            String pin = SecurePinStore.read(this);
            AccessibilityNodeInfo field = findEditable(root);
            if (field == null) {
                lastActionAt = System.currentTimeMillis();
                RobotService.operatorResult(this, false, "PIN_FIELD_NOT_FOUND",
                        "Le champ PIN de la fenêtre USSD n’est pas accessible sur ce téléphone.", "");
                return;
            }

            Bundle args = new Bundle();
            args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, pin);
            boolean inserted = field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
            if (!inserted) {
                lastActionAt = System.currentTimeMillis();
                RobotService.operatorResult(this, false, "PIN_AUTOFILL_FAILED",
                        "Android a refusé l’injection sécurisée du PIN.", "");
                return;
            }

            lastActionAt = System.currentTimeMillis();
            PendingCommandStore.updateState(this, PendingCommandStore.PIN_SUBMITTED);
            handler.postDelayed(() -> {
                AccessibilityNodeInfo current = getRootInActiveWindow();
                if (current == null || !clickFirst(current, "envoyer", "send", "confirmer", "confirm", "valider", "ok")) {
                    RobotService.operatorResult(this, false, "CONFIRM_BUTTON_NOT_FOUND",
                            "Le bouton de validation USSD n’est pas accessible sur ce téléphone.", "");
                    return;
                }
                RobotService.pinSubmitted(this);
            }, 350L);
        } catch (Exception error) {
            lastActionAt = System.currentTimeMillis();
            RobotService.operatorResult(this, false, "PIN_DECRYPTION_FAILED",
                    "Impossible de lire le PIN chiffré local.", "");
        }
    }

    private boolean confirmationMatches(String text, String phone, String amount) {
        String compact = text.replaceAll("[\\s,._-]", "");
        boolean phoneMatches = phone.length() == 9 && compact.contains(phone);
        String normalizedMoney = text.replace(",", "");
        boolean amountMatches = !amount.isEmpty() && Pattern.compile(
                "(?i)(?<!\\d)" + Pattern.quote(amount) + "(?:\\.00)?\\s*FCFA(?!\\w)")
                .matcher(normalizedMoney).find();
        return phoneMatches && amountMatches;
    }

    private static boolean isPinPrompt(String lower) {
        return lower.contains("pin")
                && containsAny(lower, "confirm", "confirmer", "enter", "saisir", "transfer balance");
    }

    private static AccessibilityNodeInfo findEditable(AccessibilityNodeInfo node) {
        if (node == null) return null;
        CharSequence className = node.getClassName();
        if (node.isEditable() || (className != null && className.toString().contains("EditText"))) return node;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo result = findEditable(node.getChild(i));
            if (result != null) return result;
        }
        return null;
    }

    private static boolean clickFirst(AccessibilityNodeInfo root, String... labels) {
        List<AccessibilityNodeInfo> nodes = new ArrayList<>();
        flatten(root, nodes);
        for (String label : labels) {
            for (AccessibilityNodeInfo node : nodes) {
                String text = node.getText() == null ? "" : node.getText().toString().trim().toLowerCase(Locale.ROOT);
                if (text.equals(label) || text.contains(label)) {
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

    private static String collectText(AccessibilityNodeInfo root) {
        List<AccessibilityNodeInfo> nodes = new ArrayList<>();
        flatten(root, nodes);
        StringBuilder result = new StringBuilder();
        for (AccessibilityNodeInfo node : nodes) {
            CharSequence text = node.getText();
            if (!TextUtils.isEmpty(text)) result.append(text).append(' ');
            CharSequence description = node.getContentDescription();
            if (!TextUtils.isEmpty(description)) result.append(description).append(' ');
        }
        return result.toString().trim();
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
    }
}
