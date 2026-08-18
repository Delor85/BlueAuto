package com.profitloop.blueauto;

import android.content.Context;

import org.json.JSONObject;

import java.util.Locale;
import java.util.UUID;

/**
 * Builds commands that can be completed entirely by the physical Robot + Blue SIM.
 * Remote/cross-device requests are deliberately excluded. Server-originated orders are still
 * leased/idempotent; after lease the Robot uses the same local execution pipeline.
 */
final class OfflineRobotEngine {
    private OfflineRobotEngine() {}

    static boolean canRunLocally(Context context, String requestType) {
        if (!AppConfig.isRobotMode(context) || !AppConfig.isPaired(context)) return false;
        String type = normalize(requestType);
        return !"REQUEST_SUPPLY".equals(type) && ("TEST_NUMBER".equals(type)
                || "CHECK_BALANCE".equals(type) || "LAST_TRANSACTIONS".equals(type)
                || "TRANSACTION_DETAILS".equals(type) || "CHILD_BALANCE".equals(type)
                || "SUPPLY_CHILD".equals(type) || "RETAIL_SALE".equals(type)
                || "RESET_PIN_SELF".equals(type) || "MODIFY_PIN_LOCAL".equals(type)
                || "FREEZE_SELF".equals(type) || "INIT_CHILD_PIN_RESET".equals(type)
                || "SUSPEND_CHILD".equals(type) || "REACTIVATE_CHILD".equals(type)
                || "FREEZE_CHILD".equals(type) || "REACTIVATE_FROZEN_CHILD".equals(type));
    }

    static JSONObject preview(Context context, String requestType, String targetNode,
                              String targetPhone, String amount, String requestId,
                              String argument, Integer commissionRateBps) throws Exception {
        if (!canRunLocally(context, requestType)) {
            throw new IllegalStateException("Cette commande nécessite le serveur ou un autre appareil.");
        }
        JSONObject command = build(context, requestType, targetNode, targetPhone, amount,
                requestId, argument, commissionRateBps, false);
        String fingerprint = fingerprint(command);
        JSONObject preview = new JSONObject();
        preview.put("confirmation_fingerprint", fingerprint);
        preview.put("operation", command.optString("operation", ""));
        preview.put("operation_label", label(command.optString("operation", "")));
        preview.put("executor_node_code", command.optString("executor_node_code", ""));
        preview.put("executor_phone", command.optString("executor_phone", ""));
        preview.put("target_node_code", command.optString("target_node_code", ""));
        preview.put("target_phone", command.optString("target_phone", ""));
        preview.put("requested_base_amount", command.optLong("requested_base_amount", command.optLong("amount", 0L)));
        preview.put("commission_rate_bps", command.optInt("commission_rate_bps", 0));
        preview.put("commission_amount", command.optLong("commission_amount", 0L));
        preview.put("amount", command.optLong("amount", 0L));
        preview.put("robot_ready", AppConfig.robotEnabled(context));
        preview.put("robot_status", AppConfig.robotEnabled(context) ? "ROBOT_LOCAL_READY" : "ROBOT_LOCAL_STOPPED");
        preview.put("robot_message", "Exécution locale sur la SIM : Internet non requis après confirmation.");
        preview.put("offline_capable", true);
        preview.put("local_execution", true);
        preview.put("dangerous", isDangerous(command.optString("operation", "")));
        JSONObject out = new JSONObject();
        out.put("preview", preview);
        out.put("offline", true);
        return out;
    }

    static JSONObject enqueue(Context context, String requestType, String targetNode,
                              String targetPhone, String amount, String requestId,
                              String confirmationFingerprint, String argument,
                              Integer commissionRateBps) throws Exception {
        if (!canRunLocally(context, requestType)) {
            throw new IllegalStateException("Cette commande nécessite une liaison serveur.");
        }
        String profileId = AppConfig.profileId(context);
        if (PendingCommandStore.get(context, profileId) != null) {
            throw new IllegalStateException("Cette SIM a déjà une commande locale ou un résultat à synchroniser.");
        }
        JSONObject command = build(context, requestType, targetNode, targetPhone, amount,
                requestId, argument, commissionRateBps, true);
        if (confirmationFingerprint != null && !confirmationFingerprint.trim().isEmpty()
                && !confirmationFingerprint.trim().equalsIgnoreCase(fingerprint(command))) {
            throw new SecurityException("La confirmation ne correspond plus aux paramètres de la commande locale.");
        }
        // Validate the exact USSD now; the service validates it again immediately before dialing.
        UssdCommandFactory.buildAndValidate(context, profileId, command);
        PendingCommandStore.save(context, profileId, command);
        OfflineLedgerDb.get(context).record(context, profileId, command, "QUEUED_LOCAL",
                "Commande conservée localement avant exécution.", "", true);
        AppConfig.setRobotEnabled(context, profileId, true);
        RobotService.startEnabled(context);
        JSONObject publicCommand = new JSONObject(command.toString());
        publicCommand.remove("lease_token");
        publicCommand.put("state", "PENDING");
        publicCommand.put("robot_ready", true);
        publicCommand.put("offline_capable", true);
        publicCommand.put("local_execution", true);
        JSONObject out = new JSONObject();
        out.put("command", publicCommand);
        out.put("offline", true);
        out.put("duplicate", false);
        return out;
    }

    static JSONObject enqueueInternal(Context context, String profileId, String requestType,
                                      String targetNode, String targetPhone, String argument) throws Exception {
        String previous = AppConfig.profileId(context);
        if (!profileId.equals(previous)) AppConfig.activateProfile(context, profileId);
        try {
            return enqueue(context, requestType, targetNode, targetPhone, "",
                    "local_" + UUID.randomUUID().toString().replace("-", ""), "", argument, null);
        } finally {
            if (!previous.isEmpty() && !previous.equals(profileId)) AppConfig.activateProfile(context, previous);
        }
    }

    private static JSONObject build(Context context, String requestType, String targetNode,
                                    String targetPhone, String amountText, String requestId,
                                    String argument, Integer commissionRateBps, boolean terminalId) throws Exception {
        String profileId = AppConfig.profileId(context);
        String role = AppConfig.role(context, profileId).toUpperCase(Locale.ROOT);
        String type = normalize(requestType);
        String operation = operation(type);
        String node = targetNode == null ? "" : targetNode.trim().toUpperCase(Locale.ROOT);
        String phone = digits(targetPhone);
        long base = longAmount(amountText);
        int rate = commissionRateBps == null ? 0 : Math.max(0, Math.min(5000, commissionRateBps));
        JSONObject child = null;
        if (requiresDirectChild(type)) {
            child = OfflineDirectoryStore.directChild(context, profileId, node);
            if (child == null) {
                throw new IllegalStateException("Enfant non disponible dans le répertoire local. Synchronisez le réseau une fois en ligne avant cette opération hors connexion.");
            }
            phone = digits(child.optString("phone_number", ""));
        }
        if ("SUPPLY_CHILD".equals(type) && !("DAE".equals(role) || "DSM".equals(role))) {
            throw new SecurityException("Seul un DAE/DSM peut approvisionner un enfant.");
        }
        if ("RETAIL_SALE".equals(type) && !"POS".equals(role)) {
            throw new SecurityException("Seul un PoS peut vendre au client final.");
        }
        if ("RETAIL_SALE".equals(type) && !phone.matches("\\d{9}")) {
            throw new IllegalArgumentException("Numéro client invalide.");
        }
        if (("SUPPLY_CHILD".equals(type) || "RETAIL_SALE".equals(type)) && base <= 0L) {
            throw new IllegalArgumentException("Montant invalide.");
        }
        long commission = "SUPPLY_CHILD".equals(type) ? (base * rate) / 10000L : 0L;
        long total = "SUPPLY_CHILD".equals(type) ? base + commission : base;
        JSONObject command = new JSONObject();
        command.put("public_id", terminalId ? "loc_" + UUID.randomUUID().toString().replace("-", "")
                : "loc_preview_" + UUID.randomUUID().toString().replace("-", ""));
        command.put("event_id", "evt_" + UUID.randomUUID().toString().replace("-", ""));
        command.put("local_only", true);
        command.put("origin", "LOCAL_ROBOT");
        command.put("local_profile_id", profileId);
        command.put("operation", operation);
        command.put("command_kind", operation);
        command.put("request_type", type);
        command.put("requester_node_code", AppConfig.nodeCode(context, profileId));
        command.put("executor_node_code", AppConfig.nodeCode(context, profileId));
        command.put("executor_phone", AppConfig.phoneNumber(context, profileId));
        command.put("target_node_code", node);
        command.put("target_phone", phone);
        command.put("requested_base_amount", base);
        command.put("commission_rate_bps", rate);
        command.put("commission_amount", commission);
        command.put("amount", total);
        command.put("command_argument", argument == null ? "" : argument.trim());
        command.put("client_request_id", requestId == null ? "" : requestId.trim());
        command.put("local_state", PendingCommandStore.LEASED);
        command.put("state_changed_at", System.currentTimeMillis());
        command.put("leased_at", System.currentTimeMillis());
        command.put("created_at", OfflineLedgerDb.isoNow());
        if ("FREEZE_SELF".equals(type)) {
            command.put("target_node_code", AppConfig.nodeCode(context, profileId));
            command.put("target_phone", AppConfig.phoneNumber(context, profileId));
        }
        return command;
    }

    private static boolean requiresDirectChild(String type) {
        return "SUPPLY_CHILD".equals(type) || "CHILD_BALANCE".equals(type)
                || "INIT_CHILD_PIN_RESET".equals(type) || "SUSPEND_CHILD".equals(type)
                || "REACTIVATE_CHILD".equals(type) || "FREEZE_CHILD".equals(type)
                || "REACTIVATE_FROZEN_CHILD".equals(type);
    }

    private static String operation(String type) {
        switch (type) {
            case "SUPPLY_CHILD": return "DISTRIBUTION_TRANSFER";
            case "RETAIL_SALE": return "RETAIL_TRANSFER";
            case "CHECK_BALANCE": return "BALANCE_OWN";
            case "LAST_TRANSACTIONS": return "HISTORY_LAST5";
            case "TRANSACTION_DETAILS": return "TRANSACTION_DETAIL";
            case "CHILD_BALANCE": return "BALANCE_CHILD";
            default: return type;
        }
    }

    private static String label(String operation) {
        if ("DISTRIBUTION_TRANSFER".equals(operation)) return "Approvisionnement Blue local";
        if ("RETAIL_TRANSFER".equals(operation)) return "Vente Blue locale";
        if ("BALANCE_OWN".equals(operation)) return "Solde Blue local";
        if ("HISTORY_LAST5".equals(operation)) return "Historique Blue local";
        return operation.replace('_', ' ');
    }

    private static boolean isDangerous(String operation) {
        return "FREEZE_SELF".equals(operation) || "INIT_CHILD_PIN_RESET".equals(operation)
                || "SUSPEND_CHILD".equals(operation) || "REACTIVATE_CHILD".equals(operation)
                || "FREEZE_CHILD".equals(operation) || "REACTIVATE_FROZEN_CHILD".equals(operation);
    }

    private static String fingerprint(JSONObject command) {
        String material = command.optString("executor_node_code", "") + "|"
                + command.optString("target_node_code", "") + "|"
                + command.optString("target_phone", "") + "|"
                + command.optString("operation", "") + "|"
                + command.optLong("amount", 0L) + "|"
                + command.optInt("commission_rate_bps", 0) + "|"
                + command.optString("command_argument", "");
        return OfflineLedgerDb.sha256(material);
    }

    private static long longAmount(String value) {
        if (value == null || value.trim().isEmpty()) return 0L;
        String digits = value.replaceAll("[^0-9]", "");
        if (digits.isEmpty()) return 0L;
        long amount = Long.parseLong(digits);
        if (amount > 999_999_999L) throw new IllegalArgumentException("Montant trop élevé.");
        return amount;
    }

    private static String digits(String value) {
        if (value == null) return "";
        String digits = value.replaceAll("[^0-9]", "");
        return digits.length() > 9 ? digits.substring(digits.length() - 9) : digits;
    }

    private static String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
    }
}
