package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

final class OfflineDirectoryStore {
    private static final String PREFIX="offline_directory_v290_";
    private OfflineDirectoryStore(){}
    private static String key(String profileId){return PREFIX+(profileId==null?"":profileId);}
    static synchronized JSONObject all(Context c,String profileId){try{return new JSONObject(AppConfig.prefs(c).getString(key(profileId),"{}"));}catch(Exception e){return new JSONObject();}}
    static synchronized void put(Context c,String profileId,String node,String phone,String role,String parent){
        node=node==null?"":node.trim().toUpperCase(); phone=phone==null?"":phone.replaceAll("\\D","");
        if(node.isEmpty()||!phone.matches("\\d{9}"))return;
        try{JSONObject root=all(c,profileId),v=new JSONObject();v.put("node_code",node);v.put("phone_number",phone);v.put("role",role==null?"":role);v.put("parent_node_code",parent==null?"":parent);v.put("cached_at",System.currentTimeMillis());root.put(node,v);AppConfig.prefs(c).edit().putString(key(profileId),root.toString()).apply();}catch(Exception ignored){}
    }
    static JSONObject find(Context c,String profileId,String node){return all(c,profileId).optJSONObject(node==null?"":node.trim().toUpperCase());}
    static void ingestDashboard(Context c,String profileId,JSONObject dashboard){
        JSONArray nodes=dashboard==null?null:dashboard.optJSONArray("nodes"); if(nodes==null)return;
        for(int i=0;i<nodes.length();i++){JSONObject n=nodes.optJSONObject(i);if(n==null)continue;put(c,profileId,n.optString("node_code"),n.optString("phone_number"),n.optString("role"),n.optString("parent_node_code"));}
    }
    static void ingestPreview(Context c,String profileId,JSONObject response){
        JSONObject p=response==null?null:response.optJSONObject("preview"); if(p==null)return;
        put(c,profileId,p.optString("target_node_code"),p.optString("target_phone"),p.optString("target_role"),p.optString("target_parent_node_code"));
    }
}
