package com.profitloop.blueauto;

import org.json.JSONObject;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Parser for real Blue/Camtel SMS and USSD popups documented in the July 2026
 * functional specification. It deliberately treats the first "Request is processed
 * successfully" popup as an acknowledgement, not as the final financial result.
 */
final class BlueMessageParser {
    private static final Pattern TRANSACTION_ID = Pattern.compile(
            "(?i)(?:TransactionID|Transaction\\s*ID|Trans\\s*ID|Ref(?:erence)?)[\\s:#=-]*([A-Za-z0-9_-]{5,64})");
    private static final Pattern RECEIPT = Pattern.compile(
            "(?i)ReceiptNumber[\\s:#=-]*([A-Za-z0-9_-]{4,64})");
    private static final Pattern PHONE = Pattern.compile("(?<!\\d)(6\\d{8})(?!\\d)");
    private static final Pattern DATE_TIME = Pattern.compile(
            "(?i)(\\d{2}[-/]\\d{2}[-/]\\d{2,4})[^\\d]{0,16}(\\d{1,2}:\\d{2}(?::\\d{2})?)");
    private static final Pattern AMOUNT = Pattern.compile(
            "(?i)(?:Amount(?:\\s+is)?|Amount:|Dr:|Cr:|Transfer\\s+Balance\\s+of|Topup\\s+Amount)\\s*([0-9][0-9 .,'’]*?(?:[.,]\\d{1,2})?)\\s*(?:F\\s*CFA|FCFA|XAF)");
    private static final Pattern BALANCE = Pattern.compile(
            "(?i)(?:Current\\s*Balance|Now\\s+your\\s+balance\\s+is|Available\\s+Balance|Your\\s+available\\s+voucher\\s+stock\\s+is|Your\\s+Balance|Solde(?:\\s+(?:actuel|disponible|restant))?)\\s*(?:(?:est)(?:\\s+de)?|[:=])?\\s*([0-9][0-9 .,'’]*?(?:[.,]\\d{1,2})?)\\s*(?:F\\s*CFA|FCFA|XAF)");
    private static final Pattern ACCOUNT = Pattern.compile("(?i)AccountNo[\\s:#=-]*([A-Za-z0-9_-]{2,64})");
    private static final Pattern PROVISIONAL_PIN = Pattern.compile(
            "(?i)(?:password\\s+is|temporary\\s+PIN(?:\\s+is)?|PIN(?:\\s+code)?\\s+is)\\s*([0-9]{4})");

    private BlueMessageParser() {}

    static Result parse(String raw) {
        String text = normalize(raw);
        String lower = text.toLowerCase(Locale.ROOT);
        Result r = new Result();
        r.raw = text;
        r.transactionId = group(TRANSACTION_ID, text, 1);
        r.receiptNumber = group(RECEIPT, text, 1);
        r.accountNo = group(ACCOUNT, text, 1);
        r.amountFcfa = firstMoney(AMOUNT, text);
        r.currentBalanceFcfa = firstMoney(BALANCE, text);
        Matcher dt = DATE_TIME.matcher(text);
        if (dt.find()) {
            r.date = dt.group(1);
            r.time = dt.group(2);
        }
        Matcher phone = PHONE.matcher(text);
        if (phone.find()) r.primaryPhone = phone.group(1);
        Matcher pp = PROVISIONAL_PIN.matcher(text);
        if (pp.find()) r.provisionalPin = pp.group(1);

        r.wrongPin = containsAny(lower, "incorrect pin", "pin incorrect", "wrong pin", "invalid pin");
        r.processing = containsAny(lower, "request is processed successfully", "request is being processed",
                "requête est en cours", "requete est en cours", "processing request");
        r.failure = !r.processing && containsAny(lower, "failed", "failure", "not successful", "declined",
                "insufficient", "unable to", "cannot", "error", "erreur", "frozen", "suspended");
        r.success = !r.processing && !r.wrongPin && containsAny(lower,
                "successfully processed", "has been successful", "completed", "you received airtime",
                "your transfer airtime", "top up of", "topup of", "successfully modified pin",
                "successfully suspended", "successfully reactivated", "successfully frozen");

        if (r.wrongPin) {
            r.kind = "WRONG_PIN";
            r.status = "BLOCKED";
        } else if (r.processing) {
            r.kind = "REQUEST_ACK";
            r.status = "PROCESSING";
        } else if (containsAny(lower, "you received airtime", "has received airtime")) {
            r.kind = "TRANSFER_RECEIVED";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
        } else if (containsAny(lower, "your transfer airtime to", "transfer airtime to")) {
            r.kind = "TRANSFER_SENT";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
        } else if (containsAny(lower, "top up of", "topup of", "top-up")) {
            r.kind = lower.contains("received") ? "RETAIL_TOPUP_RECEIVED" : "RETAIL_TOPUP_SENT";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
        } else if (lower.contains("receiptnumber") && lower.contains("currentbalance")) {
            r.kind = "MINI_STATEMENT";
            r.status = "SUCCEEDED";
            r.success = true;
        } else if (containsAny(lower, "available voucher stock", "current balance", "your balance", "solde")) {
            r.kind = "BALANCE";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
            if (!r.failure && r.currentBalanceFcfa != null) r.success = true;
        } else if (lower.contains("transaction") && containsAny(lower, "details", "accountno", "dr:", "cr:")) {
            r.kind = "TRANSACTION_DETAIL";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
            if (!r.failure) r.success = true;
        } else if (lower.contains("reset") && lower.contains("pin")) {
            r.kind = "PIN_RESET";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
        } else if (lower.contains("modified pin") || lower.contains("pin changed")) {
            r.kind = "PIN_CHANGED";
            r.status = r.failure ? "FAILED" : "SUCCEEDED";
            if (!r.failure) r.success = true;
        } else if (containsAny(lower, "suspend", "reactivat", "frozen", "freeze")) {
            r.kind = "ORGANIZATION_STATUS";
            r.status = r.failure ? "FAILED" : (r.success ? "SUCCEEDED" : "INFO");
        } else {
            r.kind = "UNKNOWN";
            r.status = r.failure ? "FAILED" : (r.success ? "SUCCEEDED" : "INFO");
        }
        return r;
    }

    static String redactSensitive(String raw, String knownPin) {
        String text = normalize(raw);
        Result parsed = parse(text);
        if (knownPin != null && knownPin.matches("\\d{4}")) text = text.replace(knownPin, "****");
        if (parsed.provisionalPin.matches("\\d{4}")) text = text.replace(parsed.provisionalPin, "****");
        return text.replaceAll("(?i)((?:password|temporary\\s+PIN|PIN(?:\\s+code)?)\\s+(?:is\\s+)?)\\d{4}", "$1****");
    }

    private static Long firstMoney(Pattern pattern, String text) {
        Matcher m = pattern.matcher(text);
        return m.find() ? money(m.group(1)) : null;
    }

    static Long money(String raw) {
        if (raw == null) return null;
        String value = raw.trim().replace("’", "'").replace(" ", "");
        if (value.isEmpty()) return null;
        int lastDot = value.lastIndexOf('.');
        int lastComma = value.lastIndexOf(',');
        int decimal = Math.max(lastDot, lastComma);
        String normalized;
        if (decimal >= 0 && value.length() - decimal - 1 <= 2) {
            String whole = value.substring(0, decimal).replaceAll("[^0-9]", "");
            String fraction = value.substring(decimal + 1).replaceAll("[^0-9]", "");
            normalized = (whole.isEmpty() ? "0" : whole) + "." + (fraction.isEmpty() ? "0" : fraction);
        } else {
            normalized = value.replaceAll("[^0-9]", "");
        }
        if (normalized.isEmpty()) return null;
        try {
            BigDecimal amount = new BigDecimal(normalized).setScale(0, RoundingMode.DOWN);
            long result = amount.longValueExact();
            return result >= 0L && result <= 9_999_999_999L ? result : null;
        } catch (Exception ignored) {
            return null;
        }
    }

    private static String group(Pattern p, String text, int group) {
        Matcher m = p.matcher(text);
        return m.find() ? safe(m.group(group)) : "";
    }

    private static boolean containsAny(String value, String... needles) {
        for (String needle : needles) if (value.contains(needle)) return true;
        return false;
    }

    private static String normalize(String value) {
        return value == null ? "" : value.replace('\u00a0', ' ').replace('\u202f', ' ')
                .replaceAll("[\\r\\n]+", " ").replaceAll("\\s+", " ").trim();
    }

    private static String safe(String value) { return value == null ? "" : value.trim(); }

    static final class Result {
        String kind = "UNKNOWN";
        String status = "INFO";
        String raw = "";
        String transactionId = "";
        String receiptNumber = "";
        String accountNo = "";
        String primaryPhone = "";
        String date = "";
        String time = "";
        String provisionalPin = "";
        Long amountFcfa;
        Long currentBalanceFcfa;
        boolean success;
        boolean failure;
        boolean processing;
        boolean wrongPin;

        boolean terminalSuccess() { return success && !processing && !wrongPin; }
        boolean terminalFailure() { return failure || wrongPin; }

        JSONObject toJson() {
            JSONObject value = new JSONObject();
            try {
                value.put("kind", kind);
                value.put("status", status);
                value.put("transaction_id", transactionId);
                value.put("receipt_number", receiptNumber);
                value.put("account_no", accountNo);
                value.put("phone", primaryPhone);
                value.put("date", date);
                value.put("time", time);
                if (amountFcfa != null) value.put("amount_fcfa", amountFcfa);
                if (currentBalanceFcfa != null) value.put("current_balance_fcfa", currentBalanceFcfa);
            } catch (Exception ignored) {}
            return value;
        }
    }
}
