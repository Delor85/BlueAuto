from pathlib import Path

root = Path('.')
index = root/'app/src/main/assets/index.html'
text = index.read_text(encoding='utf-8')
needle = '<script src="pilotage-v292.js"></script>'
insert = needle + '\n<script src="war-room-v294.js"></script>'
if 'war-room-v294.js' not in text:
    if needle not in text:
        raise SystemExit('pilotage anchor not found')
    text = text.replace(needle, insert, 1)
index.write_text(text, encoding='utf-8')

# Commission strategy is owned by each DAE/DSM. Keep computation/audit, simplify only the wording.
ct = root/'app/src/main/assets/control-tower-v2611.js'
s = ct.read_text(encoding='utf-8')
repls = {
    "Taux par défaut, personnalisés et envoi ponctuel.": "Vos règles, taux par enfant et envoi ponctuel.",
    "Le taux par défaut s\\'applique automatiquement. Une exception enfant remplace seulement ce taux.": "Votre taux habituel s\\'applique automatiquement. Un taux enfant remplace seulement votre taux habituel pour cet enfant.",
    "<label>Taux par défaut (%)</label>": "<label>Mon taux habituel (%)</label>",
    "REVENIR AU DÉFAUT": "REVENIR À MON TAUX HABITUEL",
    "à remettre au taux par défaut.": "à remettre à votre taux habituel.",
}
for old,new in repls.items():
    if old in s:
        s=s.replace(old,new)
s=s.replace("placeholder=\"Ex. '+(r==='DAE'?'10':'8')+'\"", "placeholder=\"Ex. 9,5\"")
ct.write_text(s, encoding='utf-8')

# Neutral wording in the detailed network cards too: no operator-prescribed commercial rule.
appjs = root/'app/src/main/assets/app.js'
a = appjs.read_text(encoding='utf-8')
a = a.replace('Stock hors commission : ', 'Solde réel hors commission : ')
a = a.replace(' • part taux par défaut : ', ' • part commission : ')
a = a.replace(' • taux '+"'+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace(\'.\',\',\'))+'"+' %', ' • taux appliqué '+"'+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace(\'.\',\',\'))+'"+' %') if 'part taux par défaut' in a else a
appjs.write_text(a, encoding='utf-8')

# Telemetry must identify the installed APK, while the server can remain 2.9.3-cloudflare.
api = root/'app/src/main/java/com/profitloop/blueauto/ApiClient.java'
ap = api.read_text(encoding='utf-8')
ap = ap.replace('payload.put("app_version", "2.9.3");','payload.put("app_version", "2.9.4");')
api.write_text(ap, encoding='utf-8')

# Make the War Room consume the exact v2.9.3 Command Center schema.
war = root/'app/src/main/assets/war-room-v294.js'
w = war.read_text(encoding='utf-8')
old_children = "function childrenRows(){var rs=rows(),me=String(state.config.node_code||''),role=String(state.config.role||'').toUpperCase(),out=[],i,r,parent;if(role==='POS')return out;for(i=0;i<rs.length;i++){r=rs[i]||{};parent=String(r.parent_node_code||r.parent||'');if(parent===me){out.push(r);continue;}if(role==='DAE'&&String(r.ancestor_dae||'')===me){out.push(r);}}return out;}"
new_children = "function childrenRows(){var rs=rows(),me=String(state.config.node_code||''),role=String(state.config.role||'').toUpperCase(),out=[],included={},changed=true,i,r,parent;if(role==='POS')return out;included[me]=true;while(changed){changed=false;for(i=0;i<rs.length;i++){r=rs[i]||{};parent=String(r.parent_node_code||r.parent||'');if(String(r.node_code||'')!==me&&included[parent]&&!included[String(r.node_code||'')]){if(role==='DSM'&&parent!==me)continue;included[String(r.node_code||'')]=true;out.push(r);changed=true;}}}return out;}"
if old_children not in w: raise SystemExit('war-room children anchor missing')
w=w.replace(old_children,new_children,1)
w=w.replace("var candidates=[row.stockout_days,row.coverage_days,row.days_of_stock,row.estimated_days_to_stockout,row.days_to_stockout]", "var candidates=[row.days_cover,row.stockout_days,row.coverage_days,row.days_of_stock,row.estimated_days_to_stockout,row.days_to_stockout]")
w=w.replace("Number(row.daily_outflow||row.daily_sales_velocity||row.avg_daily_sales)", "Number(row.daily_outflow_estimate||row.daily_outflow||row.daily_sales_velocity||row.avg_daily_sales)")
old_week="function weekSales(){var cc=state.commandCenter||{},vals=[cc.week_sales,cc.sales_7d,cc.weekly_sales,cc.summary&&cc.summary.sales_7d],i,n;for(i=0;i<vals.length;i++){n=Number(vals[i]);if(isFinite(n))return n;}return null;}"
new_week="function weekSales(){var cc=state.commandCenter||{},flows=cc.flows_7d||[],sum=0,seen=false,i,n;for(i=0;i<flows.length;i++){n=Number(flows[i]&&flows[i].amount);if(isFinite(n)){sum+=n;seen=true;}}if(seen)return sum;var self=selfRow(),fallback=Number(self.outflow_7d);return isFinite(fallback)?fallback:null;}"
if old_week not in w: raise SystemExit('war-room weekly sales anchor missing')
w=w.replace(old_week,new_week,1)
old_render_start="var own=ownNode()||{},self=selfRow(),kids=childrenRows(),rupture=0,near=0,sick=0,i,d,actions=urgencyList(),sales=weekSales(),ownDays=inferDays(self),bal=num(own.balance),available=own.available_balance==null?bal:num(own.available_balance),commission=num(own.commission_component_balance),html='';"
new_render_start="var own=ownNode()||{},self=selfRow(),kids=childrenRows(),rupture=0,near=0,sick=0,i,d,actions=urgencyList(),sales=weekSales(),ownDays=inferDays(self),bal=num(own.balance),commission=num(own.commission_component_balance),real=own.commission_base_balance==null?Math.max(0,bal-commission):num(own.commission_base_balance),available=own.available_balance==null?bal:num(own.available_balance),role=String(state.config.role||'').toUpperCase(),html='';"
if old_render_start not in w: raise SystemExit('war-room render anchor missing')
w=w.replace(old_render_start,new_render_start,1)
old_bal="html+='<div class=\"bir-war-kpis\"><div class=\"bir-war-kpi bir-war-balance\"><span>Mes 3 soldes</span><div class=\"bir-war-balances\"><div><span>Réel / disponible</span><b>'+esc(money(available))+'</b></div><div><span>Commission</span><b>'+esc(money(commission))+'</b></div><div><span>Total Blue</span><b>'+esc(money(bal))+'</b></div></div></div>"
new_bal="html+='<div class=\"bir-war-kpis\"><div class=\"bir-war-kpi bir-war-balance\">'+(role==='POS'?'<span>Mon solde Blue</span><div class=\"bir-war-balances\"><div><span>Disponible</span><b>'+esc(money(available))+'</b></div></div>':'<span>Mes 3 soldes</span><div class=\"bir-war-balances\"><div><span>Solde réel</span><b>'+esc(money(real))+'</b></div><div><span>Commission</span><b>'+esc(money(commission))+'</b></div><div><span>Total global</span><b>'+esc(money(bal))+'</b></div></div><small>Disponible après réservations : '+esc(money(available))+'</small>')+'"
if old_bal not in w: raise SystemExit('war-room balance anchor missing')
w=w.replace(old_bal,new_bal,1)
war.write_text(w, encoding='utf-8')

# Bump only after additive UX patch is applied.
gradle = root/'app/build.gradle'
g = gradle.read_text(encoding='utf-8')
g = g.replace('versionCode 58','versionCode 59',1).replace('versionName "2.9.3"','versionName "2.9.4"',1)
gradle.write_text(g, encoding='utf-8')

print('BIR v2.9.4 War Room patch applied')
