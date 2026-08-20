package com.profitloop.blueauto;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Canonical DAE → DSM → PoS identity grammar shared by pairing and field recovery. */
final class CamtelIdentity {
    private static final String REGIONS = "(?:AD|CE|ES|EN|LT|NO|NW|OU|SU|SW)";
    private static final Pattern DAE = Pattern.compile("^" + REGIONS + "[1-9]\\d{0,2}$");
    private static final Pattern DSM_LOCAL = Pattern.compile("^DSM[1-9]\\d{0,2}$");
    private static final Pattern DSM_FULL = Pattern.compile("^(DSM[1-9]\\d{0,2})_(" + REGIONS + "[1-9]\\d{0,2})$");
    private static final Pattern POS_LOCAL = Pattern.compile("^POS[1-9]\\d{0,3}$");
    private static final Pattern POS_FULL = Pattern.compile("^(POS[1-9]\\d{0,3})_(DSM[1-9]\\d{0,2}_" + REGIONS + "[1-9]\\d{0,2})$");

    final boolean valid;
    final String officialNode;
    final String officialParent;
    final String localNode;
    final String legacyNode;
    final String legacyParent;
    final String error;

    private CamtelIdentity(boolean valid, String officialNode, String officialParent,
                           String localNode, String legacyNode, String legacyParent, String error) {
        this.valid = valid;
        this.officialNode = officialNode;
        this.officialParent = officialParent;
        this.localNode = localNode;
        this.legacyNode = legacyNode;
        this.legacyParent = legacyParent;
        this.error = error;
    }

    static String normalize(String value) {
        return value == null ? "" : value.toUpperCase(Locale.ROOT).replaceAll("\\s+", "").trim();
    }

    static CamtelIdentity resolve(String rawNode, String rawRole, String rawParent) {
        String node = normalize(rawNode);
        String role = normalize(rawRole);
        String parent = normalize(rawParent);
        if ("DAE".equals(role)) {
            return DAE.matcher(node).matches()
                    ? valid(node, "", node, node, "")
                    : invalid("Identifiant DAE attendu : SU1, OU3, CE4…");
        }
        if ("DSM".equals(role)) {
            Matcher full = DSM_FULL.matcher(node);
            if (full.matches()) {
                String derivedParent = full.group(2);
                if (!parent.isEmpty() && !parent.equals(derivedParent)) {
                    return invalid("Le DAE saisi ne correspond pas au nom complet du DSM.");
                }
                return valid(node, derivedParent, full.group(1), full.group(1), derivedParent);
            }
            if (!DSM_LOCAL.matcher(node).matches()) {
                return invalid("DSM attendu : DSM1_SU1, ou DSM1 avec le DAE complet SU1.");
            }
            if (!DAE.matcher(parent).matches()) {
                return invalid("Indiquez le DAE complet pour former le nom officiel du DSM.");
            }
            return valid(node + "_" + parent, parent, node, node, parent);
        }
        if ("POS".equals(role)) {
            Matcher full = POS_FULL.matcher(node);
            if (full.matches()) {
                String derivedParent = full.group(2);
                String localParent = derivedParent.substring(0, derivedParent.indexOf('_'));
                if (!parent.isEmpty() && !parent.equals(derivedParent) && !parent.equals(localParent)) {
                    return invalid("Le DSM saisi ne correspond pas à la filiation complète du PoS.");
                }
                return valid(node, derivedParent, full.group(1),
                        full.group(1) + "_" + localParent, localParent);
            }
            if (!POS_LOCAL.matcher(node).matches()) {
                return invalid("PoS attendu : POS1_DSM1_SU1, ou POS1 avec DSM1_SU1.");
            }
            if (!DSM_FULL.matcher(parent).matches()) {
                return invalid("Pour un PoS abrégé, le supérieur doit être complet : DSM1_SU1.");
            }
            String localParent = parent.substring(0, parent.indexOf('_'));
            return valid(node + "_" + parent, parent, node, node + "_" + localParent,
                    localParent);
        }
        return invalid("Rôle Camtel inconnu.");
    }

    private static CamtelIdentity valid(String node, String parent, String local,
                                        String legacyNode, String legacyParent) {
        return new CamtelIdentity(true, node, parent, local, legacyNode, legacyParent, "");
    }

    private static CamtelIdentity invalid(String error) {
        return new CamtelIdentity(false, "", "", "", "", "", error);
    }
}
