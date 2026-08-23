package com.profitloop.blueauto;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class CamtelIdentityTest {
    @Test public void dsmFullRecoversLegacyAccountWithoutLosingOfficialName() {
        CamtelIdentity identity = CamtelIdentity.resolve("DSM1_SU1", "DSM", "SU1");
        assertTrue(identity.valid);
        assertEquals("DSM1_SU1", identity.officialNode);
        assertEquals("DSM1", identity.localNode);
        assertEquals("SU1", identity.officialParent);
    }

    @Test public void posShortRequiresCompleteParentLineage() {
        assertFalse(CamtelIdentity.resolve("POS1", "POS", "DSM1").valid);
        CamtelIdentity identity = CamtelIdentity.resolve("POS1", "POS", "DSM1_SU1");
        assertTrue(identity.valid);
        assertEquals("POS1_DSM1_SU1", identity.officialNode);
        assertEquals("DSM1_SU1", identity.officialParent);
        assertEquals("POS1_DSM1", identity.legacyNode);
        assertEquals("DSM1", identity.legacyParent);
    }

    @Test public void completePosMayRepeatOnlyItsShortOrFullParent() {
        assertTrue(CamtelIdentity.resolve("POS1_DSM1_SU1", "POS", "DSM1").valid);
        assertTrue(CamtelIdentity.resolve("POS1_DSM1_SU1", "POS", "DSM1_SU1").valid);
        assertFalse(CamtelIdentity.resolve("POS1_DSM1_SU1", "POS", "DSM2_SU1").valid);
    }

    @Test public void accidentalSpacesCannotCorruptOfficialCode() {
        CamtelIdentity identity = CamtelIdentity.resolve("POS1_ DSM1_SU1", "POS", "DSM1_SU1");
        assertTrue(identity.valid);
        assertEquals("POS1_DSM1_SU1", identity.officialNode);
    }
}
