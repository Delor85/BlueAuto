package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

final class OfflineSyncManager {
    private OfflineSyncManager(){}

    static void syncSome(Context c,int limit){
        for(String profile:AppConfig.profileIds(c)) syncProfile(c,profile,limit);
        syncRelayed(c,limit);
    }

    static void syncProfile(Context c,String profile,int limit){
        JSONArray items=LocalEventStore.pending(c,profile,Math.max(1,limit));
        if(items.length()==0)return;
        try{
            JSONObject response=ApiClient.forProfile(c,profile).syncLocalEvents(items);
            JSONArray accepted=response.optJSONArray("accepted_event_ids");
            if(accepted!=null){for(int i=0;i<accepted.length();i++) LocalEventStore.markSynced(c,accepted.optString(i)); return;}
        }catch(Exception ignored){}
        // Compatibility with the live 2.8 Worker: preserve events locally and only send operator
        // evidence through the historical passive endpoint. Never replay a financial command.
        for(int i=0;i<items.length();i++){
            JSONObject e=items.optJSONObject(i); if(e==null)continue;
            JSONObject p=e.optJSONObject("payload"); String raw=p==null?"":p.optString("result_message","");
            if(raw.length()<4)continue;
            try{ApiClient.forProfile(c,profile).recordOperatorMessage(raw);}catch(Exception ignored){break;}
            LocalEventStore.retryLater(c,e.optString("event_id"),60_000L);
        }
    }

    static JSONArray relayBundle(Context c,int limit){
        JSONArray src=LocalEventStore.pending(c,"",limit),out=new JSONArray();
        for(int i=0;i<src.length();i++){
            JSONObject e=src.optJSONObject(i); if(e==null)continue;
            String profile=e.optString("profile_id",""); if(!AppConfig.isPaired(c,profile))continue;
            try{
                JSONObject x=new JSONObject(e.toString());
                x.put("protocol","BIR_RELAY_EVENT_V1");
                x.put("source_device_id",AppConfig.serverDeviceId(c,profile));
                x.put("source_node_code",AppConfig.nodeCode(c,profile));
                x.put("relay_public_key",RelayIdentityStore.publicKeyBase64());
                x.put("relay_fingerprint",RelayIdentityStore.fingerprint());
                x.put("relay_hops",Math.max(0,x.optInt("relay_hops",0)));
                x.put("relay_signature",RelayIdentityStore.sign(canonical(x)));
                out.put(x);
            }catch(Exception ignored){}
        }
        return out;
    }

    static void acceptRelayBundle(Context c,JSONArray bundle){
        if(bundle==null)return;
        for(int i=0;i<bundle.length();i++){
            JSONObject e=bundle.optJSONObject(i); if(!validRelayEnvelope(e))continue;
            if(e.optInt("relay_hops",0)>=3)continue;
            try{JSONObject copy=new JSONObject(e.toString());copy.put("relay_hops",e.optInt("relay_hops",0)+1);LocalEventStore.importRelayEnvelope(c,copy);}catch(Exception ignored){}
        }
    }

    static void syncRelayed(Context c,int limit){
        JSONArray in=LocalEventStore.relayInbox(c,limit); if(in.length()==0||!AppConfig.isPaired(c))return;
        ApiClient courier=new ApiClient(c);
        for(int i=0;i<in.length();i++){
            JSONObject e=in.optJSONObject(i); if(e==null||!validRelayEnvelope(e))continue;
            String id=e.optString("event_id","");
            try{courier.relaySync(e);LocalEventStore.markRelaySynced(c,id);}catch(Exception error){LocalEventStore.retryRelayLater(c,id,60_000L);break;}
        }
    }

    static boolean validRelayEnvelope(JSONObject e){
        if(e==null||!"BIR_RELAY_EVENT_V1".equals(e.optString("protocol","")))return false;
        String id=e.optString("event_id",""),pub=e.optString("relay_public_key",""),fp=e.optString("relay_fingerprint",""),sig=e.optString("relay_signature","");
        if(!id.matches("evt_[A-Za-z0-9]{16,80}")||pub.length()<100||sig.length()<100||!fp.matches("[a-f0-9]{64}"))return false;
        if(!fp.equals(RelayIdentityStore.sha256(pub)))return false;
        return RelayIdentityStore.verify(pub,canonical(e),sig);
    }

    private static String canonical(JSONObject e){
        JSONObject p=e.optJSONObject("payload");
        return e.optString("event_id","")+"|"+e.optString("source_device_id","")+"|"+e.optString("source_node_code","")+"|"+e.optLong("created_at",0L)+"|"+e.optString("kind","")+"|"+(p==null?"{}":p.toString());
    }
}
