package com.profitloop.blueauto;

/**
 * Référentiel unique des commandes USSD Blue/Camtel exécutées par l'APK.
 * Si Camtel change un code, modifier ce fichier et son miroir public
 * cloudflare/src/camtel-catalog.mjs dans le même lot de version.
 * Aucun PIN réel n'est stocké ici.
 */
final class CamtelUssdCatalog {
    private CamtelUssdCatalog() {}

    static String testNumber() { return "*825*3*3#"; }
    static String distributionTransfer(String phone, String amount) { return "*550*2*" + phone + "*" + amount + "#"; }
    static String retailTransfer(String phone, String amount) { return "*550*1*" + phone + "*" + amount + "#"; }
    static String balanceOwn(String pin) { return "*550*3*1*" + pin + "#"; }
    static String historyLast5(String pin) { return "*550*3*3*" + pin + "#"; }
    static String transactionDetail(String id, String pin) { return "*550*3*2*" + id + "*" + pin + "#"; }
    static String resetPinSelf() { return "*550*5*1#"; }
    static String modifyPin(String newPin, String oldPin) { return "*550*3*5*" + newPin + "*" + newPin + "*" + oldPin + "#"; }
    static String balanceChild(String phone, String pin) { return "*550*5*2*" + phone + "*" + pin + "#"; }
    static String freezeSelf(String phone, String pin) { return "*550*3*4*" + phone + "*" + pin + "#"; }
    static String initChildPinReset(String phone, String pin) { return "*550*4*1*" + phone + "*" + pin + "#"; }
    static String suspendChild(String phone, String pin) { return "*550*4*2*" + phone + "*" + pin + "#"; }
    static String reactivateChild(String phone, String pin) { return "*550*4*3*" + phone + "*" + pin + "#"; }
    static String freezeChild(String phone, String pin) { return "*550*5*3*" + phone + "*" + pin + "#"; }
    static String reactivateFrozenChild(String phone, String pin) { return "*550*5*4*" + phone + "*" + pin + "#"; }
}
