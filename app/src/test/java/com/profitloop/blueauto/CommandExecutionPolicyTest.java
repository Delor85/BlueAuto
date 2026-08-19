package com.profitloop.blueauto;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class CommandExecutionPolicyTest {
    @Test
    public void testNumberNeverRequiresPinOrAccessibility() {
        CommandExecutionPolicy.Capability result = CommandExecutionPolicy.capability(
                "TEST_NUMBER", false, false, true);
        assertTrue(result.ready);
        assertEquals("READY", result.code);
    }

    @Test
    public void distributionRequiresEncryptedPin() {
        CommandExecutionPolicy.Capability result = CommandExecutionPolicy.capability(
                "DISTRIBUTION_TRANSFER", false, true, false);
        assertFalse(result.ready);
        assertEquals("PIN_NOT_CONFIGURED", result.code);
    }

    @Test
    public void retailRequiresAccessibility() {
        CommandExecutionPolicy.Capability result = CommandExecutionPolicy.capability(
                "RETAIL_TRANSFER", true, false, false);
        assertFalse(result.ready);
        assertEquals("ACCESSIBILITY_DISABLED", result.code);
    }

    @Test
    public void blockedPinDoesNotAffectTestButBlocksFinance() {
        assertTrue(CommandExecutionPolicy.capability("TEST_NUMBER", true, true, true).ready);
        CommandExecutionPolicy.Capability financial = CommandExecutionPolicy.capability(
                "RETAIL_TRANSFER", true, true, true);
        assertFalse(financial.ready);
        assertEquals("PIN_BLOCKED", financial.code);
    }

    @Test
    public void completeFinancialCapabilitiesAreAccepted() {
        assertTrue(CommandExecutionPolicy.capability(
                "DISTRIBUTION_TRANSFER", true, true, false).ready);
        assertTrue(CommandExecutionPolicy.capability(
                "RETAIL_TRANSFER", true, true, false).ready);
    }

    @Test
    public void directBalanceRequiresLocalPinButNotAccessibility() {
        CommandExecutionPolicy.Capability noPin = CommandExecutionPolicy.capability(
                "BALANCE_OWN", false, true, false);
        assertFalse(noPin.ready);
        assertEquals("PIN_NOT_CONFIGURED", noPin.code);
        assertTrue(CommandExecutionPolicy.capability(
                "BALANCE_OWN", true, false, false).ready);
        assertTrue(CommandExecutionPolicy.capability(
                "BALANCE_OWN", true, true, false).ready);
    }
}
