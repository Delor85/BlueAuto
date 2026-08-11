package com.profitloop.blueauto;

import android.content.Context;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

final class UssdCommandFactory {
    private UssdCommandFactory() {}

    static String buildAndValidate(Context context, String profileId, JSONObject command) {
        String commandId = string(command, "public_id");
        String leaseToken = string(command, "lease_token");
        if (!commandId.matches("[A-Za-z0-9_-]{16,80}")) {
            throw new SecurityException("Identifiant de commande serveur invalide.");
        }
        if (!leaseToken.matches("[a-fA-F0-9]{32,128}")) {
            throw new SecurityException("Jeton de réservation serveur invalide.");
        }

        String expectedExecutor = AppConfig.nodeCode(context, profileId);
        String suppliedExecutor = string(command, "executor_node_code").trim().toUpperCase();
        if (!suppliedExecutor.isEmpty() && !expectedExecutor.equals(suppliedExecutor)) {
            throw new SecurityException("La commande appartient à un autre nœud Robot.");
        }

        String operation = string(command, "operation");
        String phone = digits(string(command, "target_phone"));
        String amount = digits(string(command, "amount"));
        String role = AppConfig.role(context, profileId);
        String targetNode = string(command, "target_node_code").trim().toUpperCase();
        String built;

        switch (operation) {
            case "DISTRIBUTION_TRANSFER":
                if (!"DAE".equals(role) && !"DSM".equals(role)) {
                    throw new SecurityException("Ce rôle ne peut pas exécuter un transfert de distribution.");
                }
                requirePhone(phone);
                requireAmount(amount);
                if (!targetNode.isEmpty() && targetNode.equals(expectedExecutor)) {
                    throw new SecurityException("Un approvisionnement ne peut pas cibler le Robot lui-même.");
                }
                built = "*550*2*" + phone + "*" + amount + "#";
                break;
            case "RETAIL_TRANSFER":
                if (!"POS".equals(role)) {
                    throw new SecurityException("Seul un PoS peut exécuter une vente client.");
                }
                requirePhone(phone);
                requireAmount(amount);
                if (!targetNode.isEmpty()) {
                    throw new SecurityException("Une vente client ne doit pas viser un nœud interne.");
                }
                built = "*550*1*" + phone + "*" + amount + "#";
                break;
            case "TEST_NUMBER":
                if (!phone.isEmpty() || !amount.isEmpty() || !targetNode.isEmpty()) {
                    throw new SecurityException("Le diagnostic contient des paramètres financiers inattendus.");
                }
                built = "*825*3*3#";
                break;
            default:
                throw new IllegalArgumentException("Opération USSD inconnue: " + operation);
        }

        String serverValue = string(command, "ussd_code");
        if (!serverValue.isEmpty() && !built.equals(serverValue)) {
            throw new SecurityException("La commande serveur ne correspond pas aux paramètres signés.");
        }
        if (command.has("requires_pin")
                && command.optBoolean("requires_pin", false) != requiresPin(command)) {
            throw new SecurityException("Le niveau de confirmation PIN de la commande est incohérent.");
        }
        String suppliedDigest = string(command, "integrity_digest");
        if (!suppliedDigest.isEmpty()) {
            String digestInput = commandId + "|"
                    + string(command, "requester_node_code").trim().toUpperCase() + "|"
                    + suppliedExecutor + "|" + targetNode + "|" + operation + "|"
                    + phone + "|" + amount + "|" + built + "|"
                    + (requiresPin(command) ? "1" : "0");
            if (!suppliedDigest.equals(sha256(digestInput))) {
                throw new SecurityException("L’empreinte d’intégrité de la commande est invalide.");
            }
        }
        return built;
    }

    static boolean requiresPin(JSONObject command) {
        String operation = command.optString("operation", "");
        return "DISTRIBUTION_TRANSFER".equals(operation) || "RETAIL_TRANSFER".equals(operation);
    }

    private static String digits(String value) {
        if (value == null) return "";
        int decimal = value.indexOf('.');
        if (decimal >= 0) value = value.substring(0, decimal);
        return value.replaceAll("[^0-9]", "");
    }

    private static String string(JSONObject value, String key) {
        return value == null || value.isNull(key) ? "" : value.optString(key, "");
    }

    private static void requirePhone(String phone) {
        if (!phone.matches("\\d{9}")) throw new IllegalArgumentException("Numéro cible invalide.");
    }

    private static void requireAmount(String amount) {
        if (!amount.matches("[1-9]\\d{0,8}")) throw new IllegalArgumentException("Montant invalide.");
    }

    private static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder();
            for (byte item : digest) result.append(String.format(Locale.ROOT, "%02x", item & 0xff));
            return result.toString();
        } catch (Exception error) {
            throw new SecurityException("Contrôle d’intégrité indisponible.");
        }
    }
}
