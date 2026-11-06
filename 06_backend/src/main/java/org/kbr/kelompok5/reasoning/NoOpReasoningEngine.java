package org.kbr.kelompok5.reasoning;

public class NoOpReasoningEngine implements ReasoningEngine {

    @Override
    public ReasoningResult analyze(ReasoningInput input) {
        return ReasoningResult.notConfigured();
    }

    @Override
    public boolean isAvailable() {
        return false;
    }

    @Override
    public String name() {
        return "noop";
    }
}
