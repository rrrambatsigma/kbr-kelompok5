package org.kbr.kelompok5.reasoning;

/**
 * Seam integrasi reasoning engine. Backend tidak mengetahui implementasi
 * OWLAPI/HermiT maupun transport yang dipakai.
 */
public interface ReasoningEngine {

    ReasoningResult analyze(ReasoningInput input);

    boolean isAvailable();

    String name();
}
