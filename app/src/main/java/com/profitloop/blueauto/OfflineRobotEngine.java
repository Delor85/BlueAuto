package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.UUID;

final class OfflineRobotEngine {
    private OfflineRobotEngine(){}
    static boolean supports(String requestType,String role){
        String t=norm(requestType),r=norm(role);
        if("REQUEST_SUPPLY".equals(t))return false;
        if("SUPPLY_CHILD".equals(t)||"CHILD_BALANCE".equals(t)||"INIT_CHILD_PIN_RESET".equals(t)||"SUSPEND_CHILD".equals(t)||"REACTIVATE_CHILD".equals(t)||"FREEZE_CHILD".equals(t)||"REACTIVATE_FROZEN_CHILD".equals(t))return "DAE".equals(r)||"DSM".equals(r);
        if("RETAIL_SALE".equals(t))return "POS".equals(r);
        return "TEST_NUMBER".equals(t)||"CHECK_BALANCE".equals(t)||"LAST_TRANSACTIONS".equals(t)||"TRANSACTION_DETAIL".equals(t)||"RESET_PIN_SELF".equals(t)||"MODIFY_PIN_LOCAL".equals(t)||"FREEZE_SELF".equals(t);
    }
    static boolean canRunHere(Context c,String requestType){String p=AppConfig.profileId(c);return AppConfig.isRobotMode(c,p)&&AppConfig.robotEnabled(c,p)&&supports(requestType,AppConfig.role(c,p));}

    static JSONObject preview(Context c,String requestType,String targetNode,String targetPhone,String amount,String argument,int rateBps) throws Exception {
        String profile=AppConfig.profileId(c), type=norm(requestType), role=AppConfig.role(c,profile), node=up(targetNode), phone=digits(targetPhone), amt=digits(amount);
        if(!canRunHere(c,type))throw new IllegalStateException("Cette commande nécessite un Robot local actif ou une connexion Remote.");
        if(needsChild(type)){
            JSONObject cached=OfflineDirectoryStore.find(c,profile,node);
            if(cached==null)throw new IllegalStateException("Annuaire enfant absent hors connexion. Synchronisez ce réseau une fois en ligne puis réessayez.");
            phone=digits(cached.optString("phone_number"));
        }
        if("FREEZE_SELF".equals(type)){node=AppConfig.nodeCode(c,profile);phone=digits(AppConfig.phoneNumber(c,profile));}
        String op=operation(type); validate(role,type,node,phone,amt,argument);
        int base=amt.isEmpty()?0:Integer.parseInt(amt),bps=Math.max(0,Math.min(5000,rateBps));
        int commission="SUPPLY_CHILD".equals(type)?(int)Math.floor(base*bps/10000.0):0,total=base+commission;
        JSONObject p=new JSONObject(); p.put("request_type",type);p.put("operation",op);p.put("target_node_code",node);p.put("target_phone",phone);p.put("amount",("SUPPLY_CHILD".equals(type)||"RETAIL_SALE".equals(type))?String.valueOf(total):"");p.put("requested_base_amount",base);p.put("base_amount",base);p.put("commission_rate_bps",bps);p.put("commission_amount",commission);p.put("total_amount",total);p.put("executor_node_code",AppConfig.nodeCode(c,profile));p.put("executor_phone",AppConfig.phoneNumber(c,profile));p.put("execution_path","LOCAL_ROBOT");p.put("offline_capable",true);p.put("command_argument",argument==null?"":argument.trim());
        String fingerprint=sha256(type+"|"+node+"|"+phone+"|"+base+"|"+bps+"|"+total+"|"+AppConfig.nodeCode(c,profile));p.put("confirmation_fingerprint",fingerprint);
        JSONObject result=new JSONObject();result.put("preview",p);return result;
    }

    static JSONObject queue(Context c,String requestType,String targetNode,String targetPhone,String amount,String argument,int rateBps,String fingerprint) throws Exception {
        JSONObject result=preview(c,requestType,targetNode,targetPhone,amount,argument,rateBps),p=result.getJSONObject("preview");
        if(fingerprint==null||!fingerprint.equalsIgnoreCase(p.optString("confirmation_fingerprint")))throw new SecurityException("La confirmation locale ne correspond plus aux données affichées.");
        String profile=AppConfig.profileId(c); if(PendingCommandStore.get(c,profile)!=null)throw new IllegalStateException("Une commande est déjà en cours sur cette SIM.");
        String id="local_"+UUID.randomUUID().toString().replace("-","");
        JSONObject cmd=new JSONObject();cmd.put("public_id",id);cmd.put("lease_token",randomHex());cmd.put("local_origin",true);cmd.put("request_type",p.optString("request_type"));cmd.put("operation",p.optString("operation"));cmd.put("command_kind",p.optString("operation"));cmd.put("command_argument",p.optString("command_argument"));cmd.put("requester_node_code",AppConfig.nodeCode(c,profile));cmd.put("executor_node_code",AppConfig.nodeCode(c,profile));cmd.put("executor_phone",AppConfig.phoneNumber(c,profile));cmd.put("target_node_code",p.optString("target_node_code"));cmd.put("target_phone",p.optString("target_phone"));cmd.put("amount",p.optString("amount",""));cmd.put("requested_base_amount",p.optInt("base_amount",0));cmd.put("commission_rate_bps",p.optInt("commission_rate_bps",0));cmd.put("commission_amount",p.optInt("commission_amount",0));cmd.put("total_amount",p.optInt("total_amount",0));cmd.put("requires_pin",requiresPin(p.optString("operation")));cmd.put("local_profile_id",profile);cmd.put("local_state",PendingCommandStore.LEASED);cmd.put("state","PENDING");cmd.put("created_at",isoNow());cmd.put("state_changed_at",System.currentTimeMillis());
        PendingCommandStore.save(c,profile,cmd);
        JSONObject event=new JSONObject(cmd.toString());event.remove("lease_token");LocalEventStore.append(c,profile,id,"LOCAL_COMMAND_QUEUED",event);
        RobotService.startEnabled(c);
        JSONObject out=new JSONObject();JSONObject ui=new JSONObject(cmd.toString());ui.put("robot_ready",true);ui.put("robot_status","LOCAL_ROBOT");ui.put("robot_message","Commande prise en charge directement par ce Robot, sans dépendre du serveur pour l’exécution.");out.put("command",ui);out.put("local",true);return out;
    }

    static JSONObject queueMaintenance(Context c,String requestType)throws Exception{return queue(c,requestType,"","","0","",0,preview(c,requestType,"","","0","",0).getJSONObject("preview").getString("confirmation_fingerprint"));}
    private static boolean needsChild(String t){return "SUPPLY_CHILD".equals(t)||"CHILD_BALANCE".equals(t)||"INIT_CHILD_PIN_RESET".equals(t)||"SUSPEND_CHILD".equals(t)||"REACTIVATE_CHILD".equals(t)||"FREEZE_CHILD".equals(t)||"REACTIVATE_FROZEN_CHILD".equals(t);}
    private static String operation(String t){if("CHECK_BALANCE".equals(t))return "BALANCE_OWN";if("LAST_TRANSACTIONS".equals(t))return "HISTORY_LAST5";if("TRANSACTION_DETAIL".equals(t))return "TRANSACTION_DETAIL";if("SUPPLY_CHILD".equals(t))return "DISTRIBUTION_TRANSFER";if("RETAIL_SALE".equals(t))return "RETAIL_TRANSFER";if("CHILD_BALANCE".equals(t))return "BALANCE_CHILD";return t;}
    private static boolean requiresPin(String op){return "DISTRIBUTION_TRANSFER".equals(op)||"RETAIL_TRANSFER".equals(op);}
    private static void validate(String role,String type,String node,String phone,String amount,String argument){if(("SUPPLY_CHILD".equals(type)||"RETAIL_SALE".equals(type))&&!amount.matches("[1-9]\\d{0,8}"))throw new IllegalArgumentException("Montant invalide.");if((needsChild(type)||"RETAIL_SALE".equals(type))&&!phone.matches("\\d{9}"))throw new IllegalArgumentException("Numéro cible hors-ligne indisponible ou invalide.");if(needsChild(type)&&node.isEmpty())throw new IllegalArgumentException("Nœud enfant requis.");if("TRANSACTION_DETAIL".equals(type)&&(argument==null||!argument.matches("[A-Za-z0-9_-]{6,64}")))throw new IllegalArgumentException("Identifiant transaction invalide.");}
    private static String norm(String v){return v==null?"":v.trim().toUpperCase(Locale.ROOT);}private static String up(String v){return norm(v);}private static String digits(String v){if(v==null)return"";int dot=v.indexOf('.');if(dot>=0)v=v.substring(0,dot);return v.replaceAll("[^0-9]","");}
    private static String randomHex(){return UUID.randomUUID().toString().replace("-","")+UUID.randomUUID().toString().replace("-","");}
    private static String isoNow(){return new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX",Locale.ROOT).format(new java.util.Date());}
    private static String sha256(String v)throws Exception{byte[] d=MessageDigest.getInstance("SHA-256").digest(v.getBytes(StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();for(byte x:d)b.append(String.format(Locale.ROOT,"%02x",x&255));return b.toString();}
}
