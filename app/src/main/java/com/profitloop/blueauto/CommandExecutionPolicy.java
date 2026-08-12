package com.profitloop.blueauto;

/**
 * Keeps routing safety separate from financial confirmation requirements.
 *
 * A TEST_NUMBER command must be allowed as soon as the selected physical SIM and its exact call
 * route are ready. A financial command additionally requires the encrypted PIN, accessibility and
 * an unblocked PIN state. Mixing those two levels was the v2.5 regression that disabled every
 * command when only a financial prerequisite was missing.
 */
final class CommandExecutionPolicy {
    private CommandExecutionPolicy() {}

    static boolean isFinancial(String operation) {
        return "DISTRIBUTION_TRANSFER".equals(operation)
                || "RETAIL_TRANSFER".equals(operation);
    }

    static Capability capability(String operation, boolean hasEncryptedPin,
                                 boolean accessibilityEnabled, boolean pinBlocked) {
        if (!isFinancial(operation)) return Capability.ready();
        if (pinBlocked) {
            return Capability.failure("PIN_BLOCKED",
                    "Le PIN est bloqué après un refus opérateur. Corrigez-le avant une opération financière.");
        }
        if (!hasEncryptedPin) {
            return Capability.failure("PIN_NOT_CONFIGURED",
                    "Aucun PIN Camtel chiffré n’est enregistré pour ce Robot.");
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
