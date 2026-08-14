package com.profitloop.blueauto;

import android.content.Context;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

final class UssdCommandFactory {
    private UssdCommandFactory() {}

    static String buildAndValidate(Context context, String profileId, JSONObject command) throws Exception {
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
        int integrityVersion = command.optInt("integrity_version", 1);
        String executorPhone = digits(string(command, "executor_phone"));
        String configuredPhone = digits(AppConfig.phoneNumber(context, profileId));
        if (configuredPhone.length() > 9) {
            configuredPhone = configuredPhone.substring(configuredPhone.length() - 9);
        }
        if (integrityVersion >= 2 && !executorPhone.matches("\\d{9}")) {
            throw new SecurityException("Le numéro officiel de la SIM exécutrice est absent.");
        }
        if (!executorPhone.isEmpty() && !executorPhone.equals(configuredPhone)) {
            throw new SecurityException("La commande vise une autre SIM fournisseur.");
        }

        String baseOperation = string(command, "operation");
        String operation = operation(command);
        String phone = digits(string(command, "target_phone"));
        String amount = digits(string(command, "amount"));
        String argument = string(command, "command_argument").trim();
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
            case "BALANCE_OWN": {
                if (!phone.isEmpty() || !amount.isEmpty() || !targetNode.isEmpty()) {
                    throw new SecurityException("La consultation du solde contient des paramètres inattendus.");
                }
                String localPin = SecurePinStore.read(context, profileId);
                if (!localPin.matches("\\d{4}")) {
                    throw new SecurityException("PIN local absent pour consulter le solde.");
                }
                built = "*550*3*1*" + localPin + "#";
                break;
            }
            case "HISTORY_LAST5":
                requireNoTransferParameters(phone, amount, targetNode);
                built = "*550*3*3*" + localPin(context, profileId) + "#";
                break;
            case "TRANSACTION_DETAIL":
                requireNoTransferParameters(phone, amount, targetNode);
                if (!argument.matches("[A-Za-z0-9_-]{6,64}")) {
                    throw new SecurityException("Identifiant de transaction invalide.");
                }
                built = "*550*3*2*" + argument + "*" + localPin(context, profileId) + "#";
                break;
            case "BALANCE_CHILD":
                if (!"DAE".equals(role) && !"DSM".equals(role)) {
                    throw new SecurityException("Ce rôle ne peut pas consulter un solde enfant.");
                }
                requirePhone(phone);
                if (!amount.isEmpty() || targetNode.isEmpty()) {
                    throw new SecurityException("Paramètres du solde enfant incohérents.");
                }
                built = "*550*5*2*" + phone + "*" + localPin(context, profileId) + "#";
                break;
            case "FREEZE_SELF":
                if (!expectedExecutor.equals(targetNode) || !phone.equals(configuredPhone)
                        || !amount.isEmpty()) {
                    throw new SecurityException("La commande de gel propre ne correspond pas à cette SIM.");
                }
                built = "*550*3*4*" + configuredPhone + "*" + localPin(context, profileId) + "#";
                break;
            case "INIT_CHILD_PIN_RESET":
                requireManagedChild(role, targetNode, phone, amount);
                built = "*550*4*1*" + phone + "*" + localPin(context, profileId) + "#";
                break;
            case "SUSPEND_CHILD":
                requireManagedChild(role, targetNode, phone, amount);
                built = "*550*4*2*" + phone + "*" + localPin(context, profileId) + "#";
                break;
            case "REACTIVATE_CHILD":
                requireManagedChild(role, targetNode, phone, amount);
                built = "*550*4*3*" + phone + "*" + localPin(context, profileId) + "#";
                break;
            case "FREEZE_CHILD":
                requireManagedChild(role, targetNode, phone, amount);
                built = "*550*5*3*" + phone + "*" + localPin(context, profileId) + "#";
                break;
            case "REACTIVATE_FROZEN_CHILD":
                requireManagedChild(role, targetNode, phone, amount);
                built = "*550*5*4*" + phone + "*" + localPin(context, profileId) + "#";
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
            String digestUssd = integrityVersion >= 3 ? serverValue : built;
            String digestInput = commandId + "|"
                    + string(command, "requester_node_code").trim().toUpperCase() + "|"
                    + suppliedExecutor + "|"
                    + (integrityVersion >= 2 ? executorPhone + "|" : "")
                    + targetNode + "|" + baseOperation + "|"
                    + (integrityVersion >= 3 ? string(command, "command_kind") + "|" : "")
                    + (integrityVersion >= 3 ? argument + "|" : "")
                    + phone + "|" + amount + "|" + digestUssd + "|"
                    + (requiresPin(command) ? "1" : "0");
            if (!suppliedDigest.equals(sha256(digestInput))) {
                throw new SecurityException("L’empreinte d’intégrité de la commande est invalide.");
            }
        }
        return built;
    }

    static boolean requiresPin(JSONObject command) {
        String operation = operation(command);
        return "DISTRIBUTION_TRANSFER".equals(operation) || "RETAIL_TRANSFER".equals(operation);
    }

    static String operation(JSONObject command) {
        String kind = command == null ? "" : command.optString("command_kind", "");
        return kind.isEmpty() ? (command == null ? "" : command.optString("operation", "")) : kind;
    }

    private static String localPin(Context context, String profileId) throws Exception {
        String pin = SecurePinStore.read(context, profileId);
        if (!pin.matches("\\d{4}")) throw new SecurityException("PIN local absent ou invalide.");
        return pin;
    }

    private static void requireNoTransferParameters(String phone, String amount, String targetNode) {
        if (!phone.isEmpty() || !amount.isEmpty() || !targetNode.isEmpty()) {
            throw new SecurityException("La consultation contient des paramètres financiers inattendus.");
        }
    }

    private static void requireManagedChild(String role, String targetNode,
                                            String phone, String amount) {
        if (!"DAE".equals(role) && !"DSM".equals(role)) {
            throw new SecurityException("Ce rôle ne peut pas administrer un enfant.");
        }
        requirePhone(phone);
        if (targetNode.isEmpty() || !amount.isEmpty()) {
            throw new SecurityException("Paramètres de l’enfant incohérents.");
        }
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
