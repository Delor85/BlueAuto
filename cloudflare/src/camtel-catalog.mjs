export const CAMTEL_REGIONS = Object.freeze([
  {code: 'AD', name: 'Adamaoua'},
  {code: 'CE', name: 'Centre'},
  {code: 'ES', name: 'Est'},
  {code: 'EN', name: 'Extrême-Nord'},
  {code: 'LT', name: 'Littoral'},
  {code: 'NO', name: 'Nord'},
  {code: 'NW', name: 'Nord-Ouest'},
  {code: 'OU', name: 'Ouest'},
  {code: 'SU', name: 'Sud'},
  {code: 'SW', name: 'Sud-Ouest'}
]);

const REGION_CODES = new Set(CAMTEL_REGIONS.map(region => region.code));
const DAE_RE = /^([A-Z]{2})(\d{1,3})$/;
const DSM_LOCAL_RE = /^DSM([1-9]\d{0,2})$/;
const DSM_FULL_RE = /^DSM([1-9]\d{0,2})_([A-Z]{2}\d{1,3})$/;
const POS_LOCAL_RE = /^POS([1-9]\d{0,3})$/;
const POS_FULL_RE = /^POS([1-9]\d{0,3})_(DSM[1-9]\d{0,2}_[A-Z]{2}\d{1,3})$/;

export const CAMTEL_USSD = Object.freeze({
  testNumber: () => '*825*3*3#',
  distributionTransfer: (phone, amount) => `*550*2*${phone}*${amount}#`,
  retailTransfer: (phone, amount) => `*550*1*${phone}*${amount}#`,
  balanceOwn: pin => `*550*3*1*${pin}#`,
  historyLast5: pin => `*550*3*3*${pin}#`,
  transactionDetail: (transactionId, pin) => `*550*3*2*${transactionId}*${pin}#`,
  resetPinSelf: () => '*550*5*1#',
  modifyPin: (newPin, oldPin) => `*550*3*5*${newPin}*${newPin}*${oldPin}#`,
  balanceChild: (phone, pin) => `*550*5*2*${phone}*${pin}#`,
  freezeSelf: (phone, pin) => `*550*3*4*${phone}*${pin}#`,
  initChildPinReset: (phone, pin) => `*550*4*1*${phone}*${pin}#`,
  suspendChild: (phone, pin) => `*550*4*2*${phone}*${pin}#`,
  reactivateChild: (phone, pin) => `*550*4*3*${phone}*${pin}#`,
  freezeChild: (phone, pin) => `*550*5*3*${phone}*${pin}#`,
  reactivateFrozenChild: (phone, pin) => `*550*5*4*${phone}*${pin}#`
});

function regionCodeFromDae(dae) {
  const match = DAE_RE.exec(dae || '');
  return match && REGION_CODES.has(match[1]) && Number(match[2]) > 0 ? match[1] : '';
}

export function parseCamtelIdentity(value) {
  const node = String(value || '').trim().toUpperCase();
  let match = DAE_RE.exec(node);
  if (match && REGION_CODES.has(match[1]) && Number(match[2]) > 0) {
    return {ok: true, role: 'DAE', node_code: node, local_code: node,
      parent_node_code: '', dae_node_code: node, dsm_node_code: '', region_code: match[1]};
  }
  match = DSM_FULL_RE.exec(node);
  if (match) {
    const dae = match[2];
    const region = regionCodeFromDae(dae);
    if (region) return {ok: true, role: 'DSM', node_code: node, local_code: `DSM${match[1]}`,
      parent_node_code: dae, dae_node_code: dae, dsm_node_code: node, region_code: region};
  }
  match = POS_FULL_RE.exec(node);
  if (match) {
    const dsm = parseCamtelIdentity(match[2]);
    if (dsm.ok && dsm.role === 'DSM') return {ok: true, role: 'POS', node_code: node,
      local_code: `POS${match[1]}`, parent_node_code: dsm.node_code,
      dae_node_code: dsm.dae_node_code, dsm_node_code: dsm.node_code, region_code: dsm.region_code};
  }
  if (DSM_LOCAL_RE.test(node)) return {ok: true, role: 'DSM_LOCAL', node_code: node, local_code: node};
  if (POS_LOCAL_RE.test(node)) return {ok: true, role: 'POS_LOCAL', node_code: node, local_code: node};
  return {ok: false, error: 'INVALID_CAMTEL_IDENTITY'};
}

export function canonicalCamtelIdentity(value, expectedRole, parentCode = '') {
  const node = String(value || '').trim().toUpperCase();
  const role = String(expectedRole || '').trim().toUpperCase();
  const parent = String(parentCode || '').trim().toUpperCase();
  const parsed = parseCamtelIdentity(node);
  if (role === 'DAE') {
    return parsed.ok && parsed.role === 'DAE' ? parsed
      : {ok: false, error: 'INVALID_DAE_IDENTITY'};
  }
  if (role === 'DSM') {
    const parentIdentity = parseCamtelIdentity(parent);
    if (!parentIdentity.ok || parentIdentity.role !== 'DAE') {
      return {ok: false, error: 'INVALID_DAE_PARENT'};
    }
    if (parsed.ok && parsed.role === 'DSM') {
      return parsed.parent_node_code === parent ? parsed
        : {ok: false, error: 'NODE_PARENT_MISMATCH'};
    }
    const local = DSM_LOCAL_RE.exec(node);
    if (!local) return {ok: false, error: 'INVALID_DSM_IDENTITY'};
    return parseCamtelIdentity(`DSM${local[1]}_${parent}`);
  }
  if (role === 'POS') {
    const parentIdentity = parseCamtelIdentity(parent);
    if (!parentIdentity.ok || parentIdentity.role !== 'DSM') {
      return {ok: false, error: 'INVALID_DSM_PARENT'};
    }
    if (parsed.ok && parsed.role === 'POS') {
      return parsed.parent_node_code === parent ? parsed
        : {ok: false, error: 'NODE_PARENT_MISMATCH'};
    }
    const local = POS_LOCAL_RE.exec(node);
    if (!local) return {ok: false, error: 'INVALID_POS_IDENTITY'};
    return parseCamtelIdentity(`POS${local[1]}_${parent}`);
  }
  return {ok: false, error: 'INVALID_ROLE'};
}

export function publicCamtelCatalog() {
  return {
    catalog_version: '2026-08-v1',
    national_master_sim_name: 'SIM Nationale',
    regions: CAMTEL_REGIONS,
    identity: {
      dae: 'XXY (ex. OU3, CE04, LT10)',
      dsm: 'DSMZ_XXY (ex. DSM7_OU3)',
      pos: 'POSA_DSMZ_XXY (ex. POS16_DSM7_OU3)',
      short_alias_rule: 'DSMZ seulement dans son DAE; POSA seulement dans son DSM; accès direct DAE→PoS exige le nom complet.'
    },
    ussd_templates: {
      TEST_NUMBER: '*825*3*3#',
      DISTRIBUTION_TRANSFER: '*550*2*{phone}*{amount}#',
      RETAIL_TRANSFER: '*550*1*{phone}*{amount}#',
      BALANCE_OWN: '*550*3*1*{PIN_LOCAL}#',
      HISTORY_LAST5: '*550*3*3*{PIN_LOCAL}#',
      TRANSACTION_DETAIL: '*550*3*2*{transaction_id}*{PIN_LOCAL}#',
      RESET_PIN_SELF: '*550*5*1#',
      MODIFY_PIN_LOCAL: '*550*3*5*{new_pin}*{new_pin}*{old_pin}#',
      BALANCE_CHILD: '*550*5*2*{phone}*{PIN_LOCAL}#',
      FREEZE_SELF: '*550*3*4*{phone}*{PIN_LOCAL}#',
      INIT_CHILD_PIN_RESET: '*550*4*1*{phone}*{PIN_LOCAL}#',
      SUSPEND_CHILD: '*550*4*2*{phone}*{PIN_LOCAL}#',
      REACTIVATE_CHILD: '*550*4*3*{phone}*{PIN_LOCAL}#',
      FREEZE_CHILD: '*550*5*3*{phone}*{PIN_LOCAL}#',
      REACTIVATE_FROZEN_CHILD: '*550*5*4*{phone}*{PIN_LOCAL}#'
    }
  };
}
