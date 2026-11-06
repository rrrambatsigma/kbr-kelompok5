package org.kbr.kelompok5.config;

import org.kbr.kelompok5.reasoning.NoOpReasoningEngine;
import org.kbr.kelompok5.reasoning.ReasoningEngine;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ReasoningConfig {

    @Bean
    @ConditionalOnProperty(
            name = "reasoning.engine",
            havingValue = "noop",
            matchIfMissing = true)
    public ReasoningEngine noOpReasoningEngine() {
        return new NoOpReasoningEngine();
    }
}
