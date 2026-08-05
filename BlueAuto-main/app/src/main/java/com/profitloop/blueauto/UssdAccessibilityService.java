package com.profitloop.blueauto;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.os.Bundle;
import java.util.List;

public class UssdAccessibilityService extends AccessibilityService {

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event.getEventType() == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            
            AccessibilityNodeInfo nodeInfo = event.getSource();
            // On vérifie que la fenêtre est là et qu'on a bien reçu un PIN du site web
            if (nodeInfo != null && MainActivity.currentPin != null && !MainActivity.currentPin.isEmpty()) {
                
                AccessibilityNodeInfo inputField = findEditText(nodeInfo);
                if (inputField != null) {
                    // On écrit le PIN
                    Bundle arguments = new Bundle();
                    arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, MainActivity.currentPin);
                    inputField.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments);
                    
                    // On clique sur Envoyer
                    clickButton(nodeInfo, "Envoyer", "OK", "Send", "SEND");
                    
                    // On efface le PIN de la mémoire
                    MainActivity.currentPin = "";
                }
            }
        }
    }

    private AccessibilityNodeInfo findEditText(AccessibilityNodeInfo root) {
        if (root == null) return null;
        if ("android.widget.EditText".equals(root.getClassName())) return root;
        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo child = root.getChild(i);
            AccessibilityNodeInfo result = findEditText(child);
            if (result != null) return result;
        }
        return null;
    }

    private void clickButton(AccessibilityNodeInfo root, String... buttonTexts) {
        if (root == null) return;
        for (String text : buttonTexts) {
            List<AccessibilityNodeInfo> buttons = root.findAccessibilityNodeInfosByText(text);
            for (AccessibilityNodeInfo button : buttons) {
                if (button.isClickable()) {
                    button.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                    return;
                }
            }
        }
    }

    @Override
    public void onInterrupt() {}
}
