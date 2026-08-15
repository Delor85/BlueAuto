package com.profitloop.blueauto;

/**
 * Keeps routing safety separate from financial confirmation requirements.
 *
 * A TEST_NUMBER command must be allowed as soon as the selected physical SIM and its exact call
 * route are ready. A financial command or a Camtel consultation that embeds the local PIN also
 * requires the encrypted PIN, accessibility and an unblocked state. Mixing those levels was the
 * v2.5 regression that disabled every command when only a protected prerequisite was missing.
 */
final class CommandExecutionPolicy {
    private CommandExecutionPolicy() {}

    static boolean isFinancial(String operation) {
        return "DISTRIBUTION_TRANSFER".equals(operation)
                || "RETAIL_TRANSFER".equals(operation);
    }

    static boolean needsProtectedRobot(String operation) {
        return isFinancial(operation) || "BALANCE_OWN".equals(operation)
                || "HISTORY_LAST5".equals(operation)
                || "TRANSACTION_DETAIL".equals(operation)
                || "BALANCE_CHILD".equals(operation)
                || "FREEZE_SELF".equals(operation)
                || "INIT_CHILD_PIN_RESET".equals(operation)
                || "SUSPEND_CHILD".equals(operation)
                || "REACTIVATE_CHILD".equals(operation)
                || "FREEZE_CHILD".equals(operation)
                || "REACTIVATE_FROZEN_CHILD".equals(operation)
                || "RESET_PIN_SELF".equals(operation)
                || "MODIFY_PIN_LOCAL".equals(operation);
    }

    static Capability capability(String operation, boolean hasEncryptedPin,
                                 boolean accessibilityEnabled, boolean pinBlocked) {
        if (!needsProtectedRobot(operation)) return Capability.ready();
        if (pinBlocked) {
            return Capability.failure("PIN_BLOCKED",
                    "Le PIN est bloqué après un refus opérateur. Corrigez-le avant une opération protégée.");
        }
        if (!hasEncryptedPin) {
            return Capability.failure("PIN_NOT_CONFIGURED",
                    "Aucun PIN Camtel chiffré n’est enregistré pour cette commande protégée.");
        }
        if (!accessibilityEnabled) {
            return Capability.failure("ACCESSIBILITY_DISABLED",
                    "Activez l’Accessibilité Blue Magic avant une opération financière.");
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
