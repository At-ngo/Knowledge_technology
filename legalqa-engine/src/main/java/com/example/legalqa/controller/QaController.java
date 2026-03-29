package com.example.legalqa.controller;

import com.example.legalqa.model.QaResponse;
import com.example.legalqa.service.QaService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class QaController {

    @Autowired
    private QaService qaService;

    @PostMapping("/ask")
    public Map<String, String> ask(@RequestBody Map<String, String> request) {
        String question = request.getOrDefault("question", "").trim();

        QaResponse full = qaService.processQuestion(question);

        Map<String, String> simple = new LinkedHashMap<>();
        simple.put("question", full.getQuestion());
        simple.put("answer", full.getAnswer());

        return simple;
    }

    @PostMapping("/ask/debug")
    public QaResponse askDebug(@RequestBody Map<String, String> request) {
        String question = request.getOrDefault("question", "").trim();
        return qaService.processQuestion(question);
    }
}