package com.profitloop.blueauto;

/**
 * Separates three independent requirements:
 *  - TEST_NUMBER needs only a verified SIM route;
 *  - Camtel consultations/maintenance whose full dial string already embeds the locally encrypted
 *    PIN need that PIN, but do not need Accessibility merely to compose the call;
 *  - financial transfers keep the stricter Accessibility requirement because their PIN is injected
 *    only after the Camtel confirmation dialog has been verified.
 */
final class CommandExecutionPolicy {
    private CommandExecutionPolicy() {}

    static boolean isFinancial(String operation) {
        return "DISTRIBUTION_TRANSFER".equals(operation)
                || "RETAIL_TRANSFER".equals(operation);
    }

    static boolean needsStoredPin(String operation) {
        return isFinancial(operation)
                || "BALANCE_OWN".equals(operation)
                || "HISTORY_LAST5".equals(operation)
                || "TRANSACTION_DETAIL".equals(operation)
                || "BALANCE_CHILD".equals(operation)
                || "FREEZE_SELF".equals(operation)
                || "INIT_CHILD_PIN_RESET".equals(operation)
                || "SUSPEND_CHILD".equals(operation)
                || "REACTIVATE_CHILD".equals(operation)
                || "FREEZE_CHILD".equals(operation)
                || "REACTIVATE_FROZEN_CHILD".equals(operation)
                || "MODIFY_PIN_LOCAL".equals(operation);
    }

    static boolean needsAccessibility(String operation) {
        return isFinancial(operation);
    }

    static boolean needsProtectedRobot(String operation) {
        return needsStoredPin(operation);
    }

    static Capability capability(String operation, boolean hasEncryptedPin,
                                 boolean accessibilityEnabled, boolean pinBlocked) {
        if (!needsStoredPin(operation)) return Capability.ready();
        if (pinBlocked) {
            return Capability.failure("PIN_BLOCKED",
                    "Le PIN Camtel est bloqué. Corrigez-le avant cette commande protégée.");
        }
        if (!hasEncryptedPin) {
            return Capability.failure("PIN_NOT_CONFIGURED",
                    "Aucun PIN Camtel chiffré n’est enregistré pour cette commande.");
        }
        if (needsAccessibility(operation) && !accessibilityEnabled) {
            return Capability.failure("ACCESSIBILITY_DISABLED",
                    "Activez l’Accessibilité Blue Magic avant un achat ou une vente.");
        }
        return Capability.ready();
    }

    static final class Capability {
        final boolean ready;
        final String code;
        final String message;

        private Capability(boolean ready, String code, String message) {
            this.ready = ready;
            this.code = code;
            this.message = message;
        }

        static Capability ready() {
            return new Capability(true, "READY", "Prérequis de la commande disponibles.");
        }

        static Capability failure(String code, String message) {
            return new Capability(false, code, message);
        }
    }
}
