package com.example.legalqa.model;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class QaResponse {
    private boolean success;
    private String message;
    private String question;
    private String questionNorm;
    private String intent;
    private Map<String, Object> entities = new LinkedHashMap<>();
    private String endpoint;
    private String sparql;
    private String answer;
    private List<Map<String, String>> results = new ArrayList<>();
    private String error;

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public String getQuestion() { return question; }
    public void setQuestion(String question) { this.question = question; }

    public String getQuestionNorm() { return questionNorm; }
    public void setQuestionNorm(String questionNorm) { this.questionNorm = questionNorm; }

    public String getIntent() { return intent; }
    public void setIntent(String intent) { this.intent = intent; }

    public Map<String, Object> getEntities() { return entities; }
    public void setEntities(Map<String, Object> entities) { this.entities = entities; }

    public String getEndpoint() { return endpoint; }
    public void setEndpoint(String endpoint) { this.endpoint = endpoint; }

    public String getSparql() { return sparql; }
    public void setSparql(String sparql) { this.sparql = sparql; }

    public String getAnswer() { return answer; }
    public void setAnswer(String answer) { this.answer = answer; }

    public List<Map<String, String>> getResults() { return results; }
    public void setResults(List<Map<String, String>> results) { this.results = results; }

    public String getError() { return error; }
    public void setError(String error) { this.error = error; }
}
