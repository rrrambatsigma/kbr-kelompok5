package org.kbr.kelompok5;

import static org.hamcrest.Matchers.closeTo;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class BackendApiIntegrationTest {

    private static final String BLAS_SYMPTOM_1 =
            "GejalaBlasDaunMenunjukkanBercakBerwarna_2a00d88b";
    private static final String BLAS_SYMPTOM_2 =
            "GejalaGejalaPenyakitBlasDapatDitandai_c0feda66";
    private static final String BLAS_SYMPTOM_3 =
            "GejalaBercakBerwarnaAbuAbuAtauPutih_29ab0d31";
    private static final String TUNGRO_SYMPTOM =
            "GejalaIndikasiAdanyaInfeksiVirusTungro_02918429";
    private static final String KEDELAI_SYMPTOM =
            "GejalaGejalaPenyakitAntraknosaPadaKedelai_9344da2f";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointWorks() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void ontologyStatusExposesCounts() throws Exception {
        mockMvc.perform(get("/api/ontology/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.loaded").value(true))
                .andExpect(jsonPath("$.tripleCount").value(5436))
                .andExpect(jsonPath("$.counts.plants").value(7))
                .andExpect(jsonPath("$.counts.diseases").value(57))
                .andExpect(jsonPath("$.counts.symptoms").value(240))
                .andExpect(jsonPath("$.counts.pathogens").value(59))
                .andExpect(jsonPath("$.counts.controls").value(261))
                .andExpect(jsonPath("$.reasoning.engine").value("noop"))
                .andExpect(jsonPath("$.reasoning.available").value(false));
    }

    @Test
    void plantsEndpointReturnsSevenPlants() throws Exception {
        mockMvc.perform(get("/api/plants"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(7))
                .andExpect(jsonPath("$.items[?(@.id == 'Padi')]").exists())
                .andExpect(jsonPath("$.items[?(@.id == 'Kedelai')].scientificName")
                        .value("Glycine max L. Merril"));
    }

    @Test
    void plantDetailContainsDiseasesAndVarieties() throws Exception {
        mockMvc.perform(get("/api/plants/Padi"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value("Padi"))
                .andExpect(jsonPath("$.scientificName").doesNotExist())
                .andExpect(jsonPath("$.diseases.length()").value(5))
                .andExpect(jsonPath("$.varieties.length()").value(4))
                .andExpect(jsonPath("$.generalControls.length()").value(0))
                .andExpect(jsonPath("$.warnings", hasItem("SCIENTIFIC_NAME_NOT_AVAILABLE")))
                .andExpect(jsonPath("$.warnings", hasItem("DESCRIPTION_NOT_AVAILABLE")));
    }

    @Test
    void unknownPlantReturns404() throws Exception {
        mockMvc.perform(get("/api/plants/TidakAda"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("RESOURCE_NOT_FOUND"))
                .andExpect(jsonPath("$.detail", notNullValue()));
    }

    @Test
    void diseasesEndpointReturnsAllAndFiltered() throws Exception {
        mockMvc.perform(get("/api/diseases"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(57));

        mockMvc.perform(get("/api/diseases").param("plantId", "Padi"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(5));
    }

    @Test
    void diseaseDetailContainsEvidence() throws Exception {
        mockMvc.perform(get("/api/diseases/PenyakitBlasPadi"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.label").value("Penyakit Blas"))
                .andExpect(jsonPath("$.plant.id").value("Padi"))
                .andExpect(jsonPath("$.category").doesNotExist())
                .andExpect(jsonPath("$.description").doesNotExist())
                .andExpect(jsonPath("$.pathogens.length()").value(3))
                .andExpect(jsonPath("$.pathogens[0].id").value("MagnaportheGrisea"))
                .andExpect(jsonPath("$.pathogens[0].type").value("Jamur"))
                .andExpect(jsonPath("$.symptoms.length()").value(7))
                .andExpect(jsonPath("$.controls.length()").value(8))
                .andExpect(jsonPath("$.affectedParts[0].id").value("Daun"))
                .andExpect(jsonPath("$.environmentalFactors[0].id").value("KondisiMusimHujan"))
                .andExpect(jsonPath("$.references.length()").value(1))
                .andExpect(jsonPath("$.warnings", hasItem("DESCRIPTION_NOT_AVAILABLE")));
    }

    @Test
    void diseaseWithoutPathogenIsReportedAsWarning() throws Exception {
        mockMvc.perform(get("/api/diseases/NekrosisPadaTitikTunasCassavaBudNecrosisUbiKayu"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pathogens").isEmpty())
                .andExpect(jsonPath("$.warnings", hasItem("PATHOGEN_NOT_AVAILABLE")));
    }

    @Test
    void symptomsEndpointsApplyFilters() throws Exception {
        mockMvc.perform(get("/api/symptoms"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(240));

        mockMvc.perform(get("/api/symptoms").param("plantId", "Kedelai"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(94));

        mockMvc.perform(get("/api/symptoms").param("diseaseId", "PenyakitBlasPadi"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(7));

        mockMvc.perform(get("/api/plants/Padi/symptoms"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(32));
    }

    @Test
    void diagnosisReturnsRankedCandidate() throws Exception {
        String body = """
                {
                  "plantId": "Padi",
                  "symptomIds": [
                    "%s",
                    "%s",
                    "%s"
                  ],
                  "partIds": ["Daun"],
                  "environmentalFactorIds": ["KondisiMusimHujan"]
                }
                """.formatted(BLAS_SYMPTOM_1, BLAS_SYMPTOM_2, BLAS_SYMPTOM_3);

        mockMvc.perform(post("/api/diagnosis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.input.plantId").value("Padi"))
                .andExpect(jsonPath("$.input.symptomCount").value(3))
                .andExpect(jsonPath("$.candidates.length()").value(1))
                .andExpect(jsonPath("$.candidates[0].disease.id").value("PenyakitBlasPadi"))
                .andExpect(jsonPath("$.candidates[0].disease.category").doesNotExist())
                .andExpect(jsonPath("$.candidates[0].score", closeTo(0.83, 0.01)))
                .andExpect(jsonPath("$.candidates[0].matchRatio").value(1.0))
                .andExpect(jsonPath("$.candidates[0].evidence.controls.length()").value(8))
                .andExpect(jsonPath("$.reasoning.engine").value("noop"))
                .andExpect(jsonPath("$.reasoning.status").value("NOT_CONFIGURED"))
                .andExpect(jsonPath("$.warnings", hasItem("REASONING_NOT_CONFIGURED")));
    }

    @Test
    void diagnosisRejectsMissingSymptoms() throws Exception {
        mockMvc.perform(post("/api/diagnosis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"plantId":"Padi","symptomIds":[]}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"))
                .andExpect(jsonPath("$.errors").isArray());
    }

    @Test
    void diagnosisRejectsUnknownSymptom() throws Exception {
        mockMvc.perform(post("/api/diagnosis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"plantId":"Padi","symptomIds":["GejalaTidakAda"]}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"))
                .andExpect(jsonPath("$.errors[0].message", notNullValue()));
    }

    @Test
    void diagnosisRejectsSymptomFromAnotherPlant() throws Exception {
        mockMvc.perform(post("/api/diagnosis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"plantId":"Padi","symptomIds":["%s"]}
                                """.formatted(KEDELAI_SYMPTOM)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void diagnosisWarnsWhenSymptomsComeFromDifferentDiseases() throws Exception {
        String body = """
                {
                  "plantId": "Padi",
                  "symptomIds": [
                    "%s",
                    "%s",
                    "%s"
                  ]
                }
                """.formatted(BLAS_SYMPTOM_1, BLAS_SYMPTOM_2, TUNGRO_SYMPTOM);

        mockMvc.perform(post("/api/diagnosis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.candidates.length()").value(2))
                .andExpect(jsonPath("$.warnings", hasItem("MIXED_DISEASE_SYMPTOMS")));
    }

    @Test
    void malformedJsonReturnsBadRequest() throws Exception {
        mockMvc.perform(post("/api/diagnosis")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_JSON"));
    }

    @Test
    void corsPreflightAllowsConfiguredFrontendOrigin() throws Exception {
        mockMvc.perform(options("/api/plants")
                        .header("Origin", "http://localhost:5173")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string(
                        "Access-Control-Allow-Origin", "http://localhost:5173"));
    }
}
