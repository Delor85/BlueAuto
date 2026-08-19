from pathlib import Path

p=Path('app/src/main/assets/pilotage-v292.js')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    c=s.count(old)
    if c!=1: raise SystemExit(f'{label}: expected 1 anchor, got {c}')
    s=s.replace(old,new,1)

once("var c=cfg(),role=upper(c.role),last=null,selectedTool='health';","var c=cfg(),role=upper(c.role),last=null,commandCenter=null,selectedTool='command-center';",'pilot state')
once("<div class=\"v292-tools\"><button class=\"v292-tool\" data-v292-tool=\"continuity\">","<div class=\"v292-tools\"><button class=\"v292-tool\" data-v292-tool=\"command-center\"><i>∞</i><b>Command Center</b><small>Rupture, anomalies, qualité de service.</small></button><button class=\"v292-tool\" data-v292-tool=\"continuity\">",'command center tool')
once("function load(){if(c.owner_admin_workspace)req('owner_ops_cockpit',{});else req('ops_cockpit',{});}","function load(){if(c.owner_admin_workspace){req('owner_ops_cockpit',{});window.setTimeout(function(){req('owner_distribution_command_center',{});},80);}else{req('ops_cockpit',{});window.setTimeout(function(){req('distribution_command_center',{});},80);}}",'command center load')
old="function detail(){var out=id('v292Detail');if(!out||!last)return;var s=last.summary||{},a=last.audit||{},f=last.forecast||{},co=last.commission||{},r=last.rescue||{},list=nodes(),h=[],i,x,filtered=[];if(selectedTool==='continuity'){"
new="function detail(){var out=id('v292Detail');if(!out||!last)return;var s=last.summary||{},a=last.audit||{},f=last.forecast||{},co=last.commission||{},r=last.rescue||{},list=nodes(),h=[],i,x,filtered=[];if(selectedTool==='command-center'){var cc=commandCenter||{},cs=cc.summary||{},sig=cc.service_signal||{},an=cc.anomalies||[],cn=cc.nodes||[];h.push('<h3>∞ Blue Distribution Command Center</h3><p><b>'+esc(cs.nodes||0)+'</b> compte(s) suivis · <b>'+esc(cs.stockout_critical||0)+'</b> rupture(s) critique(s) · <b>'+esc(cs.stockout_watch||0)+'</b> à surveiller.</p><p><b>'+esc(sig.code||'SERVICE_STABLE')+'</b> — '+esc(sig.message||'Aucun signal transversal significatif.')+'</p>');for(i=0;i<Math.min(12,an.length);i++){x=an[i];h.push('<div class=\"v292-simple-row\"><span class=\"v292-dot '+esc(String(x.severity||'INFO').toLowerCase())+'\"></span><div><b>'+esc(x.node_code||'Réseau')+' · '+esc(x.code||'ANOMALIE')+'</b><small>'+esc(x.message||'Signal à vérifier.')+'</small></div></div>');}if(!an.length)h.push('<p>Aucune anomalie prioritaire détectée.</p>');if(cn.length){h.push('<small>Prévisions fondées sur les soldes et débits réellement connus par B.I.R. Elles assistent la décision et ne déclenchent jamais seules un transfert.</small>');}}else if(selectedTool==='continuity'){"
once(old,new,'command center detail')
old="if(a==='ops_cockpit'){render(d);return;}"
new="if(a==='ops_cockpit'||a==='owner_ops_cockpit'){render(d);return;}if(a==='distribution_command_center'||a==='owner_distribution_command_center'){commandCenter=d;detail();return;}"
once(old,new,'command center callback')

p.write_text(s,encoding='utf-8')
print('B.I.R. v2.9.3 command-center UI patch applied')
