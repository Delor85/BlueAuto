from pathlib import Path

ROOT = Path('.')
OWNER_HASH = '207e4a9bca5e4073fa98e767a85bd937a63d9e2f62d2fe5e693360ab2ee3e3cd'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, content):
    (ROOT / path).write_text(content, encoding='utf-8')


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 occurrence, found {count}')
    return text.replace(old, new, 1)

# --- Native owner entitlement and national MOCK orchestration ---
main_path = 'app/src/main/java/com/profitloop/blueauto/MainActivity.java'
main = read(main_path)
main = replace_once(main, 'import org.json.JSONObject;\n', 'import org.json.JSONArray;\nimport org.json.JSONObject;\n', 'JSONArray import')
main = replace_once(main, 'import java.net.UnknownHostException;\n', 'import java.net.UnknownHostException;\nimport java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\n', 'crypto imports')
main = replace_once(
    main,
    '    private static final String MOCK_WORKSPACE_KEY = "bir_mock_workspace_v270";\n'
    '    private static final String MOCK_OWNER_NODE_CODE = "SU1";\n'
    '    private static final String MOCK_PROFILE_ID = "__BIR_MOCK_OWNER__";\n',
    '    private static final String MOCK_WORKSPACE_KEY = "bir_mock_workspace_v270";\n'
    '    private static final String MOCK_OWNER_ENABLED_KEY = "bir_mock_owner_enabled_v270";\n'
    '    private static final String MOCK_ROUTE_PROFILE_KEY = "bir_mock_route_profile_v270";\n'
    f'    private static final String MOCK_OWNER_CODE_SHA256 = "{OWNER_HASH}";\n'
    '    private static final String MOCK_PROFILE_ID = "__BIR_MOCK_OWNER__";\n'
    '    private static final String[] MOCK_REGION_CODES = {"AD", "CE", "ES", "EN", "LT", "NO", "NW", "OU", "SU", "SW"};\n'
    '    private static final String[] MOCK_REGION_NAMES = {"Adamaoua", "Centre", "Est", "Extrême-Nord", "Littoral", "Nord", "Nord-Ouest", "Ouest", "Sud", "Sud-Ouest"};\n',
    'replace SU1 mock constants'
)
old_block = '''    private boolean mockOwnerEligible() {
        return "DAE".equalsIgnoreCase(AppConfig.role(this))
                && MOCK_OWNER_NODE_CODE.equalsIgnoreCase(AppConfig.nodeCode(this));
    }

    private boolean isMockWorkspaceActive() {
        return mockOwnerEligible() && AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false);
    }

    private void setMockWorkspaceActive(boolean active) {
        AppConfig.prefs(this).edit().putBoolean(MOCK_WORKSPACE_KEY, active && mockOwnerEligible()).commit();
    }

'''
new_block = '''    private boolean mockOwnerEnrolled() {
        return AppConfig.prefs(this).getBoolean(MOCK_OWNER_ENABLED_KEY, false);
    }

    private boolean mockOwnerEligible() {
        // MOCK is deliberately independent from every real Camtel identity. It becomes available
        // only after the high-entropy owner code has been enrolled on this physical installation.
        return mockOwnerEnrolled() && AppConfig.hasProfiles(this);
    }

    private boolean isMockWorkspaceActive() {
        return mockOwnerEligible() && AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false);
    }

    private void setMockWorkspaceActive(boolean active) {
        AppConfig.prefs(this).edit().putBoolean(MOCK_WORKSPACE_KEY, active && mockOwnerEligible()).commit();
    }

    private boolean isDaeProfile(String profileId) {
        return profileId != null && !profileId.isEmpty()
                && AppConfig.isPaired(this, profileId)
                && "DAE".equalsIgnoreCase(AppConfig.role(this, profileId));
    }

    private String mockRouteProfile() {
        String saved = AppConfig.prefs(this).getString(MOCK_ROUTE_PROFILE_KEY, "");
        if (isDaeProfile(saved)) return saved;
        String[] ids = AppConfig.profileIds(this);
        for (String id : ids) {
            if (isDaeProfile(id)) {
                AppConfig.prefs(this).edit().putString(MOCK_ROUTE_PROFILE_KEY, id).commit();
                return id;
            }
        }
        return "";
    }

    private void showMockActivationDialog() {
        LinearLayout content = verticalContainer();
        content.setPadding(dp(16), dp(8), dp(16), dp(8));
        TextView explanation = help("MOCK est le compte propriétaire national, au-dessus des 10 régions. "
                + "Il n'est ni DAE, ni DSM, ni PoS et ne possède aucune SIM. Son code propriétaire reste local : "
                + "il n'est jamais envoyé à Cloudflare.");
        EditText code = field("Code propriétaire MOCK", "", true);
        TextView feedback = help("Après activation, MOCK pourra agréger les DAE appairés sur ce téléphone et choisir une route DAE/PoS. "
                + "Les transactions Camtel directes resteront interdites dans MOCK.");
        content.addView(explanation);
        content.addView(code);
        content.addView(feedback);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Activer le compte MOCK propriétaire")
                .setView(content)
                .setPositiveButton("ACTIVER", null)
                .setNegativeButton("Annuler", null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    String provided = code.getText().toString().trim();
                    if (!mockOwnerCodeMatches(provided)) {
                        code.setError("Code propriétaire incorrect.");
                        feedback.setText("Activation refusée. Aucun droit réseau n'a été modifié.");
                        return;
                    }
                    AppConfig.prefs(this).edit()
                            .putBoolean(MOCK_OWNER_ENABLED_KEY, true)
                            .putBoolean(MOCK_WORKSPACE_KEY, true)
                            .commit();
                    mockRouteProfile();
                    code.setText("");
                    dialog.dismiss();
                    Toast.makeText(this, "Compte MOCK propriétaire activé sur ce téléphone.", Toast.LENGTH_LONG).show();
                    recreate();
                }));
        dialog.show();
    }

    private boolean mockOwnerCodeMatches(String value) {
        if (value == null || value.length() < 32) return false;
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] actual = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            byte[] expected = hexBytes(MOCK_OWNER_CODE_SHA256);
            return MessageDigest.isEqual(actual, expected);
        } catch (Exception ignored) {
            return false;
        }
    }

    private static byte[] hexBytes(String value) {
        byte[] result = new byte[value.length() / 2];
        for (int i = 0; i < result.length; i++) {
            int high = Character.digit(value.charAt(i * 2), 16);
            int low = Character.digit(value.charAt(i * 2 + 1), 16);
            result[i] = (byte) ((high << 4) | low);
        }
        return result;
    }

    private JSONObject mockNationalSnapshot() throws Exception {
        if (!isMockWorkspaceActive()) throw new SecurityException("Compte MOCK propriétaire requis.");
        JSONObject result = new JSONObject();
        result.put("_action", "mock_national_snapshot");
        result.put("owner_scope", "NATIONAL_10_REGIONS");
        JSONArray regions = new JSONArray();
        for (int i = 0; i < MOCK_REGION_CODES.length; i++) {
            JSONObject region = new JSONObject();
            region.put("code", MOCK_REGION_CODES[i]);
            region.put("name", MOCK_REGION_NAMES[i]);
            region.put("paired", false);
            regions.put(region);
        }
        JSONArray networks = new JSONArray();
        String selectedRoute = mockRouteProfile();
        int daeProfiles = 0;
        int reachable = 0;
        String[] ids = AppConfig.profileIds(this);
        for (String id : ids) {
            if (!isDaeProfile(id)) continue;
            daeProfiles += 1;
            String node = AppConfig.nodeCode(this, id);
            String regionCode = node != null && node.length() >= 2 ? node.substring(0, 2).toUpperCase(Locale.ROOT) : "";
            for (int r = 0; r < regions.length(); r++) {
                JSONObject region = regions.optJSONObject(r);
                if (region != null && regionCode.equals(region.optString("code"))) region.put("paired", true);
            }
            JSONObject network = new JSONObject();
            network.put("profile_id", id);
            network.put("node_code", node);
            network.put("region_code", regionCode);
            network.put("selected", id.equals(selectedRoute));
            try {
                JSONObject dashboard = ApiClient.forProfile(this, id).dashboard();
                network.put("reachable", true);
                network.put("generated_at", dashboard.optString("generated_at", ""));
                JSONArray nodes = dashboard.optJSONArray("nodes");
                network.put("nodes", nodes == null ? new JSONArray() : nodes);
                reachable += 1;
            } catch (Exception error) {
                network.put("reachable", false);
                network.put("error", readable(error));
                network.put("nodes", new JSONArray());
            }
            networks.put(network);
        }
        result.put("regions", regions);
        result.put("networks", networks);
        result.put("paired_dae_profiles", daeProfiles);
        result.put("reachable_dae_profiles", reachable);
        result.put("selected_route_profile_id", selectedRoute);
        result.put("selected_route_node_code", selectedRoute.isEmpty() ? "" : AppConfig.nodeCode(this, selectedRoute));
        result.put("routing_rule", "Chaque action réelle utilise le jeton du DAE sélectionné; MOCK ne contourne jamais les droits du Worker.");
        return result;
    }

    private boolean mockDirectNetworkBlocked() {
        return isMockWorkspaceActive();
    }

'''
main = replace_once(main, old_block, new_block, 'mock owner methods')
main = replace_once(
    main,
    '        if (mockOwnerEligible()) {\n'
    '            labelsList.add((mockActive ? "✓ " : "") + "MOCK • ESPACE PROPRIÉTAIRE • HORS RÉSEAU");\n'
    '            idsList.add(MOCK_PROFILE_ID);\n'
    '        }\n',
    '        labelsList.add((mockActive ? "✓ " : "") + (mockOwnerEnrolled()\n'
    '                ? "MOCK • PROPRIÉTAIRE NATIONAL • 10 RÉGIONS"\n'
    '                : "🔒 MOCK • ACTIVER LE COMPTE PROPRIÉTAIRE NATIONAL"));\n'
    '        idsList.add(MOCK_PROFILE_ID);\n',
    'account manager mock visibility'
)
main = replace_once(
    main,
    '                    if (MOCK_PROFILE_ID.equals(ids[index])) {\n'
    '                        setMockWorkspaceActive(true);\n'
    '                        recreate();\n'
    '                        return;\n'
    '                    }\n',
    '                    if (MOCK_PROFILE_ID.equals(ids[index])) {\n'
    '                        if (!mockOwnerEnrolled()) {\n'
    '                            showMockActivationDialog();\n'
    '                            return;\n'
    '                        }\n'
    '                        setMockWorkspaceActive(true);\n'
    '                        mockRouteProfile();\n'
    '                        recreate();\n'
    '                        return;\n'
    '                    }\n',
    'account manager activation'
)
# Native hard-stop for direct financial command preview/creation while in MOCK.
main = replace_once(
    main,
    '        public void createCommand(String requestType, String targetNode, String targetPhone,\n'
    '                                  String amount, String clientRequestId,\n'
    '                                  String confirmationFingerprint, String capacityCheckId,\n'
    '                                  String commandArgument) {\n'
    '            new Thread(() -> {\n',
    '        public void createCommand(String requestType, String targetNode, String targetPhone,\n'
    '                                  String amount, String clientRequestId,\n'
    '                                  String confirmationFingerprint, String capacityCheckId,\n'
    '                                  String commandArgument) {\n'
    '            if (mockDirectNetworkBlocked()) {\n'
    '                callbackError("onCommandCreated", new SecurityException(\n'
    '                        "MOCK ne crée pas d’approvisionnement ou de vente Camtel directe. Utilisez un compte réseau normal; les ventes Mercenaires restent routables via le PoS choisi."));\n'
    '                return;\n'
    '            }\n'
    '            new Thread(() -> {\n',
    'create command mock guard'
)
main = replace_once(
    main,
    '        public void createCommandWithCommissionRate(String requestType, String targetNode, String targetPhone,\n'
    '                                                     String amount, String clientRequestId,\n'
    '                                                     String confirmationFingerprint, String capacityCheckId,\n'
    '                                                     String commandArgument, int commissionRateBps) {\n'
    '            new Thread(() -> {\n',
    '        public void createCommandWithCommissionRate(String requestType, String targetNode, String targetPhone,\n'
    '                                                     String amount, String clientRequestId,\n'
    '                                                     String confirmationFingerprint, String capacityCheckId,\n'
    '                                                     String commandArgument, int commissionRateBps) {\n'
    '            if (mockDirectNetworkBlocked()) {\n'
    '                callbackError("onCommandCreated", new SecurityException(\n'
    '                        "MOCK ne crée pas de transaction Camtel directe."));\n'
    '                return;\n'
    '            }\n'
    '            new Thread(() -> {\n',
    'create command commission mock guard'
)
main = replace_once(
    main,
    '        public void checkPurchaseCapacity(String amount, String clientRequestId) {\n'
    '            new Thread(() -> {\n',
    '        public void checkPurchaseCapacity(String amount, String clientRequestId) {\n'
    '            if (mockDirectNetworkBlocked()) {\n'
    '                callbackError("onPurchaseCapacity", new SecurityException(\n'
    '                        "Le compte MOCK ne s’approvisionne pas lui-même."));\n'
    '                return;\n'
    '            }\n'
    '            new Thread(() -> {\n',
    'capacity mock guard'
)
# Bridge methods for national aggregation and route selection.
main = replace_once(
    main,
    '        @JavascriptInterface\n'
    '        public void exitMockWorkspace() {\n'
    '            runOnUiThread(() -> {\n'
    '                setMockWorkspaceActive(false);\n'
    '                recreate();\n'
    '            });\n'
    '        }\n',
    '        @JavascriptInterface\n'
    '        public void exitMockWorkspace() {\n'
    '            runOnUiThread(() -> {\n'
    '                setMockWorkspaceActive(false);\n'
    '                recreate();\n'
    '            });\n'
    '        }\n\n'
    '        @JavascriptInterface\n'
    '        public void loadMockNationalSnapshot() {\n'
    '            new Thread(() -> {\n'
    '                try { callback("onMockNationalSnapshot", mockNationalSnapshot()); }\n'
    '                catch (Exception error) { callbackError("onMockNationalSnapshot", error); }\n'
    '            }).start();\n'
    '        }\n\n'
    '        @JavascriptInterface\n'
    '        public void setMockRouteProfile(String profileId) {\n'
    '            if (!isMockWorkspaceActive()) {\n'
    '                callbackError("onMockRouteChanged", new SecurityException("Compte MOCK propriétaire requis."));\n'
    '                return;\n'
    '            }\n'
    '            if (!isDaeProfile(profileId)) {\n'
    '                callbackError("onMockRouteChanged", new SecurityException("La route MOCK doit être un DAE réel appairé sur ce téléphone."));\n'
    '                return;\n'
    '            }\n'
    '            AppConfig.prefs(MainActivity.this).edit().putString(MOCK_ROUTE_PROFILE_KEY, profileId).commit();\n'
    '            try {\n'
    '                JSONObject data = new JSONObject();\n'
    '                data.put("profile_id", profileId);\n'
    '                data.put("node_code", AppConfig.nodeCode(MainActivity.this, profileId));\n'
    '                callback("onMockRouteChanged", data);\n'
    '            } catch (Exception error) { callbackError("onMockRouteChanged", error); }\n'
    '        }\n',
    'mock bridge snapshot and route'
)
# Route Mercenary APIs through selected real DAE token while MOCK is active.
main = replace_once(
    main,
    '                    JSONObject data = new ApiClient(MainActivity.this).platformAction(action, payload);\n'
    '                    data.put("_action", action == null ? "" : action);\n',
    '                    ApiClient client = new ApiClient(MainActivity.this);\n'
    '                    if (isMockWorkspaceActive() && normalizedAction.startsWith("mercenary_")) {\n'
    '                        String routeProfile = mockRouteProfile();\n'
    '                        if (!isDaeProfile(routeProfile)) {\n'
    '                            throw new SecurityException("Aucun DAE réel appairé n’est disponible comme route MOCK.");\n'
    '                        }\n'
    '                        client = ApiClient.forProfile(MainActivity.this, routeProfile);\n'
    '                    }\n'
    '                    JSONObject data = client.platformAction(action, payload);\n'
    '                    data.put("_action", action == null ? "" : action);\n'
    '                    if (isMockWorkspaceActive()) data.put("_mock_route_node_code",\n'
    '                            AppConfig.nodeCode(MainActivity.this, mockRouteProfile()));\n',
    'route mock platform actions'
)
# Raw USSD is never available in MOCK.
main = replace_once(
    main,
    '        public void executeRawUSSD(String raw) {\n'
    '            runOnUiThread(() -> {\n',
    '        public void executeRawUSSD(String raw) {\n'
    '            if (mockDirectNetworkBlocked()) {\n'
    '                runOnUiThread(() -> toast("Sandbox USSD refusée dans MOCK : choisissez un compte réseau réel."));\n'
    '                return;\n'
    '            }\n'
    '            runOnUiThread(() -> {\n',
    'raw ussd mock guard'
)
write(main_path, main)

# --- Make the Mercenary module render for MOCK even when the active real profile is not a DAE. ---
platform_path = 'app/src/main/assets/platform-v267.js'
platform = read(platform_path)
platform = replace_once(
    platform,
    '  function isDae() { return configuration.role === \'DAE\'; }\n'
    '  function isRobot() { return configuration.mode === \'ROBOT\'; }\n',
    '  function isDae() { return configuration.role === \'DAE\'; }\n'
    '  function isMockWorkspace() { var nativeBridge = bridge(); try { return !!(nativeBridge && nativeBridge.isMockWorkspace && nativeBridge.isMockWorkspace()); } catch (ignored) { return false; } }\n'
    '  function isRobot() { return configuration.mode === \'ROBOT\'; }\n',
    'platform mock helper'
)
platform = replace_once(platform, '  if (isDae()) {\n', '  if (isDae() || isMockWorkspace()) {\n', 'render mercenary in mock')
write(platform_path, platform)

# --- v2.7 national-owner UI ---
js_path = 'app/src/main/assets/control-tower-v270.js'
js = read(js_path)
js = replace_once(
    js,
    "function mockOffNetworkHtml(){return '<article class=\"panel v270-mock-card\"><p class=\"eyebrow\">HORS RÉSEAU DAE / DSM / POS</p><h3>Laboratoire propriétaire</h3><div class=\"v270-business-grid\"><div><b>Mercenaires</b><span>Vendeurs virtuels servis par des PoS Robots. Les fonctions serveur restent désactivées tant que le Worker compatible n\\'est pas autorisé en production.</span></div><div><b>B.I.R. Pay</b><span>NON OPÉRATIONNEL : aucune collecte, clé, débit Mobile Money ou webhook n\\'est activé.</span></div><div><b>Partenariats / services</b><span>Zone de conception pour offres, revendeurs externes, white-label et services non rattachés à une SIM Camtel hiérarchique.</span></div><div><b>Règle d\\'isolement</b><span>MOCK n\\'est pas un node_code Camtel et ne peut jamais devenir DAE, DSM, PoS, Robot ou propriétaire d\\'une SIM.</span></div></div></article>';}",
    "function mockOffNetworkHtml(){return '<article class=\"panel v270-mock-card\"><p class=\"eyebrow\">HORS RÉSEAU DAE / DSM / POS</p><h3>Laboratoire propriétaire</h3><div class=\"v270-business-grid\"><div><b>Mercenaires</b><span>Vendeurs virtuels servis par un PoS Robot choisi dans la flotte du DAE sélectionné. Le Worker 2.6.11 conserve la vérification de descendance et des soldes.</span></div><div><b>B.I.R. Pay</b><span>NON OPÉRATIONNEL : aucune collecte, clé, débit Mobile Money ou webhook n\\'est activé.</span></div><div><b>Partenariats / services</b><span>Zone de conception pour offres, revendeurs externes, white-label et services non rattachés à une SIM Camtel hiérarchique.</span></div><div><b>Règle d\\'isolement</b><span>MOCK n\\'est pas un node_code Camtel et ne peut jamais devenir DAE, DSM, PoS, Robot ou propriétaire d\\'une SIM.</span></div></div></article>';}",
    'mock off-network truth'
)
insert_after = "function setMercenaryCapability(ok,version){var merc=findMercenary(),buttons,i,status;if(!merc)return;merc.style.display='block';buttons=merc.querySelectorAll('button');for(i=0;i<buttons.length;i+=1)buttons[i].disabled=!ok;status=byId('v270MercenaryCapability');if(status)status.innerHTML=ok?'Serveur '+esc(version||'compatible')+' : fonctions Mercenaires disponibles pour essai contrôlé.':'Production '+esc(version||'non identifiée')+' : fonctions Mercenaires verrouillées pour éviter « Action API inconnue ». Aucun ordre ne sera envoyé.';}\n"
addition = r'''function mockNationalHtml(){return '<article class="panel v270-mock-card"><p class="eyebrow">TOUR NATIONALE</p><h3>MOCK • 10 régions</h3><p class="muted">Compte virtuel propriétaire, au-dessus des régions mais hors hiérarchie Camtel. Il n\'emprunte jamais l\'identité de SU1 ni d\'un autre DAE. Chaque action réelle est signée par le DAE sélectionné et reste contrôlée par le Worker.</p><div id="v270MockRegions" class="v270-region-strip"></div><label class="v270-route-label">Route DAE réelle</label><select id="v270MockDaeRoute" class="v270-route-select"><option value="">Chargement…</option></select><label class="v270-route-label">PoS Robot proposé pour Mercenaires</label><select id="v270MockPosRoute" class="v270-route-select"><option value="">Choisir après actualisation</option></select><div class="actions"><button id="v270MockRefresh" type="button">ACTUALISER LES 10 RÉGIONS</button></div><p id="v270MockNationalStatus" class="v270-capability">Lecture des DAE appairés…</p><p class="small">Sécurité : MOCK ne peut ni s\'approvisionner, ni vendre directement comme un PoS, ni lancer un USSD, ni gérer un PIN/SIM. Les ventes Mercenaires peuvent utiliser le PoS dédié de la route DAE choisie.</p></article>';}
function renderMockNational(data){var routes=byId('v270MockDaeRoute'),pos=byId('v270MockPosRoute'),regions=byId('v270MockRegions'),status=byId('v270MockNationalStatus'),nets=data&&data.networks||[],regs=data&&data.regions||[],selected=String(data&&data.selected_route_profile_id||''),i,j,nodes,node,opt,selectedNet=null,html=[];if(regions){for(i=0;i<regs.length;i+=1)html.push('<span class="v270-region-chip '+(regs[i].paired?'is-on':'')+'">'+esc(regs[i].code)+' · '+esc(regs[i].name)+'</span>');regions.innerHTML=html.join('');}if(routes){routes.innerHTML='';if(!nets.length){opt=document.createElement('option');opt.value='';opt.textContent='Aucun DAE appairé';routes.appendChild(opt);}for(i=0;i<nets.length;i+=1){opt=document.createElement('option');opt.value=nets[i].profile_id;opt.textContent=(nets[i].reachable?'● ':'○ ')+String(nets[i].node_code||'DAE')+' · '+String(nets[i].region_code||'');if(String(nets[i].profile_id)===selected){opt.selected=true;selectedNet=nets[i];}routes.appendChild(opt);}if(!selectedNet&&nets.length)selectedNet=nets[0];}if(pos){pos.innerHTML='';opt=document.createElement('option');opt.value='';opt.textContent='PoS à sélectionner';pos.appendChild(opt);nodes=selectedNet&&selectedNet.nodes||[];for(j=0;j<nodes.length;j+=1){node=nodes[j]||{};if(String(node.role||'').toUpperCase()!=='POS')continue;opt=document.createElement('option');opt.value=String(node.node_code||'');opt.textContent=String(node.node_code||'PoS')+(node.robot_live?' · Robot actif':'');pos.appendChild(opt);}}if(status)status.textContent='DAE appairés : '+Number(data&&data.paired_dae_profiles||0)+' • joignables : '+Number(data&&data.reachable_dae_profiles||0)+' • route : '+String(data&&data.selected_route_node_code||'aucune')+'. Les régions sans DAE appairé restent visibles mais ne sont pas inventées.';}
function bindMockNational(){var b=bridge(),route=byId('v270MockDaeRoute'),pos=byId('v270MockPosRoute'),refresh=byId('v270MockRefresh');window.BlueMagicNative=window.BlueMagicNative||{};window.BlueMagicNative.onMockNationalSnapshot=function(data){if(data&&data.error){var s=byId('v270MockNationalStatus');if(s)s.textContent=data.message||'Lecture nationale impossible.';return;}renderMockNational(data||{});};window.BlueMagicNative.onMockRouteChanged=function(data){if(data&&data.error){var s=byId('v270MockNationalStatus');if(s)s.textContent=data.message||'Route refusée.';return;}if(b&&b.loadMockNationalSnapshot)b.loadMockNationalSnapshot();};if(route)route.onchange=function(){if(b&&b.setMockRouteProfile)b.setMockRouteProfile(route.value);};if(pos)pos.onchange=function(){var input=byId('merc-pos');if(input&&pos.value)input.value=pos.value;};if(refresh)refresh.onclick=function(){if(b&&b.loadMockNationalSnapshot)b.loadMockNationalSnapshot();};if(b&&b.loadMockNationalSnapshot)b.loadMockNationalSnapshot();}
'''
js = replace_once(js, insert_after, insert_after + addition, 'national mock functions')
old_render = "function renderMock(){var main=document.querySelector('main'),merc=findMercenary(),shell,children,i,b;if(!main)return;document.body.className=(document.body.className?document.body.className+' ':'')+'v270-mock-active';shell=document.createElement('section');shell.id='birMockWorkspace';shell.className='v270-mock-workspace';shell.innerHTML='<article class=\"v270-mock-hero\"><div><p class=\"eyebrow\">COMPTE SPÉCIAL</p><h2>MOCK</h2><p>Espace propriétaire • Hors réseau Camtel • Aucune SIM sollicitée par l\\'ouverture de cet espace.</p></div><button id=\"v270ExitMock\" type=\"button\">REVENIR AU RÉSEAU</button></article><article class=\"panel v270-mock-card\"><p class=\"eyebrow\">MERCENAIRES / CLOUD VENDING</p><h3>Centre propriétaire</h3><p id=\"v270MercenaryCapability\" class=\"v270-capability\">Vérification du serveur…</p><div id=\"v270MercenaryMount\"></div></article>'+mockRevenueHtml()+mockOffNetworkHtml();main.insertBefore(shell,main.firstChild);if(merc){merc.style.display='block';merc.open=true;byId('v270MercenaryMount').appendChild(merc);}children=main.children;for(i=0;i<children.length;i+=1){if(children[i]!==shell)children[i].className+=' v270-network-hidden';}b=document.querySelector('.module-tabs');if(b)b.style.display='none';if(byId('birAccountRole'))byId('birAccountRole').textContent='MOCK';if(byId('birAccountNode'))byId('birAccountNode').textContent='PROPRIÉTAIRE';if(byId('birAccountPhone'))byId('birAccountPhone').textContent='HORS RÉSEAU';byId('v270ExitMock').onclick=function(){var n=bridge();if(n&&n.exitMockWorkspace)n.exitMockWorkspace();};installHealthGate();var n=bridge();if(n&&n.checkServerHealth){try{n.checkServerHealth();}catch(e){}}}"
new_render = "function renderMock(){var main=document.querySelector('main'),merc=findMercenary(),shell,children,i,b;if(!main)return;document.body.className=(document.body.className?document.body.className+' ':'')+'v270-mock-active';shell=document.createElement('section');shell.id='birMockWorkspace';shell.className='v270-mock-workspace';shell.innerHTML='<article class=\"v270-mock-hero\"><div><p class=\"eyebrow\">COMPTE SPÉCIAL PROPRIÉTAIRE</p><h2>MOCK</h2><p>National • 10 régions • Hors hiérarchie Camtel • Aucune SIM propre.</p></div><button id=\"v270ExitMock\" type=\"button\">REVENIR AU RÉSEAU</button></article>'+mockNationalHtml()+'<article class=\"panel v270-mock-card\"><p class=\"eyebrow\">MERCENAIRES / CLOUD VENDING</p><h3>Centre propriétaire</h3><p id=\"v270MercenaryCapability\" class=\"v270-capability\">Vérification du serveur…</p><div id=\"v270MercenaryMount\"></div></article>'+mockRevenueHtml()+mockOffNetworkHtml();main.insertBefore(shell,main.firstChild);if(merc){merc.style.display='block';merc.open=true;byId('v270MercenaryMount').appendChild(merc);}children=main.children;for(i=0;i<children.length;i+=1){if(children[i]!==shell)children[i].className+=' v270-network-hidden';}b=document.querySelector('.module-tabs');if(b)b.style.display='none';if(byId('birAccountRole'))byId('birAccountRole').textContent='MOCK';if(byId('birAccountNode'))byId('birAccountNode').textContent='NATIONAL';if(byId('birAccountPhone'))byId('birAccountPhone').textContent='HORS RÉSEAU';byId('v270ExitMock').onclick=function(){var n=bridge();if(n&&n.exitMockWorkspace)n.exitMockWorkspace();};bindMockNational();installHealthGate();var n=bridge();if(n&&n.checkServerHealth){try{n.checkServerHealth();}catch(e){}}}"
js = replace_once(js, old_render, new_render, 'render national mock')
write(js_path, js)

css_path = 'app/src/main/assets/control-tower-v270.css'
css = read(css_path)
css += '\n.v270-region-strip{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.v270-region-chip{display:inline-flex;padding:6px 8px;border:1px solid #d9e2ec;border-radius:999px;background:#f5f7fa;color:#6b7785;font-size:.65rem;font-weight:800}.v270-region-chip.is-on{background:#e8f7ee;border-color:#96d9ad;color:#176b37}.v270-route-label{display:block;margin:9px 0 4px;color:#0b3567;font-size:.7rem;font-weight:900}.v270-route-select{width:100%;min-height:42px;border:1px solid #b8cbe0;border-radius:12px;background:#fff;color:#102f58;padding:8px 10px}.v270-mock-active #merc-pos{font-weight:800;border-color:#d5a632}\n'
write(css_path, css)

# --- Contract: remove SU1 dependency and prove native privilege boundaries. ---
test_path = 'app/src/test/v270-finalization-contract.mjs'
test = read(test_path)
test = replace_once(test, "assert.match(main,/MOCK_OWNER_NODE_CODE = \"SU1\"/);\n", "assert.doesNotMatch(main,/MOCK_OWNER_NODE_CODE|\\\"SU1\\\"/);\nassert.match(main,/MOCK_OWNER_ENABLED_KEY = \"bir_mock_owner_enabled_v270\"/);\nassert.match(main,/MOCK_OWNER_CODE_SHA256 = \"[a-f0-9]{64}\"/);\nassert.match(main,/NATIONAL_10_REGIONS/);\nassert.match(main,/loadMockNationalSnapshot/);\nassert.match(main,/setMockRouteProfile/);\nassert.match(main,/MOCK ne crée pas d’approvisionnement ou de vente Camtel directe/);\nassert.match(main,/ApiClient\\.forProfile\\(MainActivity\\.this, routeProfile\\)/);\n", 'v270 owner assertions')
test = replace_once(test, "assert.match(overlay,/MOCK/);\n", "assert.match(overlay,/MOCK/);\nassert.match(overlay,/10 régions/);\nassert.match(overlay,/v270MockDaeRoute/);\nassert.match(overlay,/v270MockPosRoute/);\nassert.match(overlay,/ne sont pas inventées/);\n", 'overlay national assertions')
write(test_path, test)

owner_test = r'''import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const main = await readFile(new URL('main/java/com/profitloop/blueauto/MainActivity.java', root), 'utf8');
const platform = await readFile(new URL('main/assets/platform-v267.js', root), 'utf8');
const overlay = await readFile(new URL('main/assets/control-tower-v270.js', root), 'utf8');
const worker = await readFile(new URL('../../cloudflare/src/index.js', import.meta.url), 'utf8');
assert.doesNotMatch(main, /MOCK_OWNER_NODE_CODE|"SU1"/);
assert.match(main, /MOCK_OWNER_CODE_SHA256 = "[a-f0-9]{64}"/);
assert.match(main, /MessageDigest\.isEqual/);
assert.match(main, /owner_scope", "NATIONAL_10_REGIONS"/);
assert.match(main, /"AD", "CE", "ES", "EN", "LT", "NO", "NW", "OU", "SU", "SW"/);
assert.match(main, /ApiClient\.forProfile\(this, id\)\.dashboard\(\)/);
assert.match(main, /ApiClient\.forProfile\(MainActivity\.this, routeProfile\)/);
assert.match(main, /MOCK ne crée pas d’approvisionnement ou de vente Camtel directe/);
assert.match(main, /Sandbox USSD refusée dans MOCK/);
assert.match(platform, /isDae\(\) \|\| isMockWorkspace\(\)/);
assert.match(overlay, /Route DAE réelle/);
assert.match(overlay, /PoS Robot proposé pour Mercenaires/);
assert.match(overlay, /Chaque action réelle est signée par le DAE sélectionné/);
assert.match(worker, /if \(auth\.role !== 'DAE'\) throw new ApiError\('REQUEST_NOT_ALLOWED','Hub Mercenaires réservé au DAE\.'/);
assert.match(worker, /resolveDescendant\(env, auth\.node_code, account\.dedicated_pos_node_code, \['POS'\]\)/);
console.log('B.I.R. v2.7 owner MOCK: national virtual scope, DAE-token routing and transaction boundaries OK');
'''
write('app/src/test/v270-owner-mock-contract.mjs', owner_test)

state_path = 'docs/BIR_V270_MOCK_OWNER_STATE.md'
state = '''# B.I.R. v2.7.0 — compte MOCK propriétaire national\n\nDate : 2026-08-16\n\n## Décision\n\nLe compte MOCK n'utilise plus `SU1` ni aucun autre DAE comme identité propriétaire. Les dix régions officielles restent AD, CE, ES, EN, LT, NO, NW, OU, SU et SW. MOCK est un espace virtuel propriétaire au-dessus de ces régions, hors grammaire Camtel DAE/DSM/PoS.\n\n## Activation propriétaire\n\nMOCK est verrouillé par un code propriétaire haute entropie. Seul son SHA-256 est embarqué dans l'APK. Le code n'est jamais envoyé au Worker ni stocké en clair par cette modification. L'activation est locale au téléphone.\n\n## Portée réelle sans modification Cloudflare/D1\n\nLe Worker 2.6.11 authentifie chaque requête par un jeton d'appareil rattaché à un nœud réel. Par conséquent, sans modifier le Worker ni D1, MOCK ne peut pas inventer un super-token national. Il agrège à la place tous les profils DAE réellement appairés sur le téléphone et utilise explicitement le jeton du DAE sélectionné pour les actions Mercenaires. Les régions sans profil DAE appairé sont affichées comme non connectées.\n\n## Choix du PoS\n\nPour une route DAE donnée, le tableau national charge les descendants réellement visibles de ce DAE et propose les PoS de cette flotte. Le champ `dedicated_pos_node_code` du Hub Mercenaires peut être alimenté par ce sélecteur. Le Worker conserve son contrôle `resolveDescendant`: un PoS extérieur à la flotte du DAE choisi reste refusé.\n\n## Transactions interdites dans MOCK\n\nMOCK ne peut pas créer directement un approvisionnement DAE/DSM, une vente détail PoS, un précontrôle d'approvisionnement, un USSD brut ou une opération qui ferait de MOCK un Robot/SIM. Pour ces opérations, il faut revenir au compte réseau réel. La vente Mercenaire reste possible via le DAE sélectionné et son PoS dédié, car elle est explicitement contrôlée côté Worker.\n\n## Production\n\nAucune source `cloudflare/` ni migration D1 n'est modifiée par cette étape. Aucun déploiement Worker n'est effectué. La publication permanente précédemment autorisée pour le SHA `fbbb17d05e16f03dd82224df4b9aa67277272197` ne doit pas être lancée après cette correction, car ce SHA contient encore l'ancien verrou SU1. Un nouveau SHA exact devra être autorisé après validation.\n'''
write(state_path, state)

print('National owner MOCK patch prepared without Cloudflare/D1 changes')
