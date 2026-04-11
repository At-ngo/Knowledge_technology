package com.example.legalqa.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class FusekiService {
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .build();
    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<Map<String, String>> query(String endpoint, String sparql) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(endpoint))
                .timeout(Duration.ofSeconds(30))
                .header("Content-Type", "application/sparql-query; charset=UTF-8")
                .header("Accept", "application/sparql-results+json, application/json")
                .POST(HttpRequest.BodyPublishers.ofString(sparql, StandardCharsets.UTF_8))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new IOException("Fuseki returned status " + response.statusCode() + ": " + response.body());
        }

        JsonNode root = objectMapper.readTree(response.body());
        JsonNode bindings = root.path("results").path("bindings");
        List<Map<String, String>> rows = new ArrayList<>();

        for (JsonNode binding : bindings) {
            Map<String, String> row = new LinkedHashMap<>();
            Iterator<String> fields = binding.fieldNames();
            while (fields.hasNext()) {
                String field = fields.next();
                row.put(field, binding.path(field).path("value").asText(""));
            }
            rows.add(row);
        }
        return rows;
    }
}
