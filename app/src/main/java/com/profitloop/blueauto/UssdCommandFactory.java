package com.profitloop.blueauto;

import org.json.JSONObject;

final class UssdCommandFactory {
    private UssdCommandFactory() {}

    static String buildAndValidate(JSONObject command) {
        String operation = command.optString("operation", "");
        String phone = digits(command.optString("target_phone", ""));
        String amount = digits(command.optString("amount", ""));
        String built;

        switch (operation) {
            case "DISTRIBUTION_TRANSFER":
                requirePhone(phone);
                requireAmount(amount);
                built = "*550*2*" + phone + "*" + amount + "#";
                break;
            case "RETAIL_TRANSFER":
                requirePhone(phone);
                requireAmount(amount);
                built = "*550*1*" + phone + "*" + amount + "#";
                break;
            case "TEST_NUMBER":
                built = "*825*3*3#";
                break;
            default:
                throw new IllegalArgumentException("Opération USSD inconnue: " + operation);
        }

        String serverValue = command.optString("ussd_code", "");
        if (!serverValue.isEmpty() && !built.equals(serverValue)) {
            throw new SecurityException("La commande serveur ne correspond pas aux paramètres signés.");
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

    private static void requirePhone(String phone) {
        if (!phone.matches("\\d{9}")) throw new IllegalArgumentException("Numéro cible invalide.");
    }

    private static void requireAmount(String amount) {
        if (!amount.matches("[1-9]\\d{0,8}")) throw new IllegalArgumentException("Montant invalide.");
    }
}
