from pathlib import Path

main = Path('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
s = main.read_text()
old = '''                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "
Actions regroupées pour rester lisibles même sur les petits téléphones.");'''
new = '''                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "\\nActions regroupées pour rester lisibles même sur les petits téléphones.");'''
if old not in s:
    raise SystemExit('MainActivity responsive intro compile anchor missing')
main.write_text(s.replace(old, new, 1))

obsolete = Path('app/src/main/java/com/profitloop/blueauto/InsecureKeyguardDismissActivity.java')
if obsolete.exists():
    obsolete.unlink()

test = Path('app/src/test/java/com/profitloop/blueauto/CommandExecutionPolicyTest.java')
t = test.read_text()
old_test = '''    public void directBalanceRequiresLocalPinAndAccessibility() {
        CommandExecutionPolicy.Capability noPin = CommandExecutionPolicy.capability(
                "BALANCE_OWN", false, true, false);
        assertFalse(noPin.ready);
        assertEquals("PIN_NOT_CONFIGURED", noPin.code);
        CommandExecutionPolicy.Capability noAccessibility = CommandExecutionPolicy.capability(
                "BALANCE_OWN", true, false, false);
        assertFalse(noAccessibility.ready);
        assertEquals("ACCESSIBILITY_DISABLED", noAccessibility.code);
        assertTrue(CommandExecutionPolicy.capability(
                "BALANCE_OWN", true, true, false).ready);
    }
'''
new_test = '''    public void directBalanceRequiresLocalPinButNotAccessibility() {
        CommandExecutionPolicy.Capability noPin = CommandExecutionPolicy.capability(
                "BALANCE_OWN", false, true, false);
        assertFalse(noPin.ready);
        assertEquals("PIN_NOT_CONFIGURED", noPin.code);
        assertTrue(CommandExecutionPolicy.capability(
                "BALANCE_OWN", true, false, false).ready);
        assertTrue(CommandExecutionPolicy.capability(
                "BALANCE_OWN", true, true, false).ready);
    }
'''
if old_test not in t:
    raise SystemExit('legacy balance accessibility unit test anchor missing')
test.write_text(t.replace(old_test, new_test, 1))
