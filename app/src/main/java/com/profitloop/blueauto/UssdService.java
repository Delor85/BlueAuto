package com.profitloop.blueauto;

import android.accessibilityservice.AccessibilityService;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import java.util.List;

public class UssdService extends AccessibilityService {
    // Cette variable stockera le PIN temporairement
    public static String pinEnAttente = null; 

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        String className = String.valueOf(event.getClassName());
        
        // On vérifie si une boîte de dialogue s'ouvre à l'écran
        if (className.contains("AlertDialog") || className.contains("Dialog")) {
            AccessibilityNodeInfo rootNode = getRootInActiveWindow();
            if (rootNode != null && pinEnAttente != null) {
                injecterPinEtValider(rootNode);
            }
        }
    }

    private void injecterPinEtValider(AccessibilityNodeInfo node) {
        // 1. Chercher le champ de texte où taper le code (EditText)
        AccessibilityNodeInfo champTexte = trouverNoeudParClasse(node, "android.widget.EditText");
        
        // 2. Chercher le bouton pour valider (Souvent "Envoyer", "OK", "Send")
        AccessibilityNodeInfo boutonValider = trouverBouton(node);

        if (champTexte != null && boutonValider != null) {
            // On injecte le PIN
            Bundle arguments = new Bundle();
            arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, pinEnAttente);
            champTexte.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);

            // On clique sur le bouton pour valider
            boutonValider.performAction(AccessibilityNodeInfo.ACTION_CLICK);

            // On vide le PIN pour sécuriser et éviter de le retaper en boucle
            pinEnAttente = null; 
        }
    }

    private AccessibilityNodeInfo trouverNoeudParClasse(AccessibilityNodeInfo racine, String classeCherchee) {
        if (racine == null) return null;
        if (racine.getClassName() != null && racine.getClassName().toString().equals(classeCherchee)) {
            return racine;
        }
        for (int i = 0; i < racine.getChildCount(); i++) {
            AccessibilityNodeInfo resultat = trouverNoeudParClasse(racine.getChild(i), classeCherchee);
            if (resultat != null) return resultat;
        }
        return null;
    }

    private AccessibilityNodeInfo trouverBouton(AccessibilityNodeInfo racine) {
        String[] textesBoutons = {"Envoyer", "Send", "OK", "Valider", "Yes", "Oui"};
        for (String texte : textesBoutons) {
            List<AccessibilityNodeInfo> noeuds = racine.findAccessibilityNodeInfosByText(texte);
            for (AccessibilityNodeInfo noeud : noeuds) {
                if (noeud.isClickable()) {
                    return noeud;
                }
            }
        }
        return null;
    }

    @Override
    public void onInterrupt() {}
}
