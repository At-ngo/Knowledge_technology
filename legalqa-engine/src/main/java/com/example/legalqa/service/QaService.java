package com.example.legalqa.service;

import com.example.legalqa.model.QaResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.text.Normalizer;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class QaService {
    private static final String PREFIX = """
            PREFIX legal: <http://example.org/legal-qa#>
            PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
            """;

    private static final Pattern ARTICLE_PATTERN = Pattern.compile("\\bdieu\\s+(\\d+)");
    private static final Pattern CLAUSE_PATTERN = Pattern.compile("\\bkhoan\\s+(\\d+)");
    private static final Pattern POINT_PATTERN = Pattern.compile("\\bdiem\\s+([a-z])");

    private static final Map<String, String> LAW_KEYWORDS = new LinkedHashMap<>();
    static {
        LAW_KEYWORDS.put("luat trat tu an toan giao thong duong bo", "TTATGTDB");
        LAW_KEYWORDS.put("luat giao thong duong bo", "TTATGTDB");
        LAW_KEYWORDS.put("luat duong bo", "LDB");
        LAW_KEYWORDS.put("bo luat lao dong", "LLD");
        LAW_KEYWORDS.put("luat lao dong", "LLD");
    }

    private static final Set<String> INFERENCE_INTENTS = Set.of(
            "ASK_VIOLATION_CHECK", "ASK_AGGRAVATION", "ASK_LIST_VIOLATIONS"
    );

    private static final Set<String> RELATION_INTENTS = Set.of(
            "ASK_DEFINITION", "ASK_INCLUDES", "ASK_PROHIBITION", "ASK_PERMISSION",
            "ASK_REQUIREMENT", "ASK_RESPONSIBILITY", "ASK_APPLIES_TO", "ASK_PURPOSE",
            "ASK_CONNECTION", "ASK_USAGE"
    );

    private final FusekiService fusekiService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${app.fuseki.base-endpoint:http://localhost:3030/legalqa/query}")
    private String baseEndpoint;

    @Value("${app.fuseki.inference-endpoint:http://localhost:3030/legalqa-inf/sparql}")
    private String inferenceEndpoint;

    private JsonNode mappingRoot;
    private JsonNode intentRelationMap;
    private List<EntityCandidate> entityCandidates = new ArrayList<>();
    private List<EntityCandidate> subjectCandidates = new ArrayList<>();
    private List<EntityCandidate> conditionCandidates = new ArrayList<>();

    public QaService(FusekiService fusekiService) {
        this.fusekiService = fusekiService;
    }

    @PostConstruct
    public void init() throws IOException {
        this.mappingRoot = readJson("mapping_dictionary.json");
        this.intentRelationMap = readJson("intent_relation_map.json");
        this.entityCandidates = buildCandidates(mappingRoot.path("entities"));
        this.subjectCandidates = buildCandidates(mappingRoot.path("subjects"));
        this.conditionCandidates = buildCandidates(mappingRoot.path("conditions"));
    }

    public QaResponse processQuestion(String question) {
        QaResponse response = new QaResponse();
        response.setSuccess(false);
        response.setMessage("INIT");
        response.setQuestion(question);

        String normalized = normalizeText(question);
        response.setQuestionNorm(normalized);

        String intent = detectIntent(normalized);
        response.setIntent(intent);

        Map<String, Object> entities = extractEntities(normalized);
        response.setEntities(entities);

        if ("UNKNOWN".equals(intent)) {
            String lawLabel = stringValue(entities.get("law_label"));
            if (!lawLabel.isBlank()) {
                response.setAnswer("Hệ thống nhận ra bạn đang hỏi " + lawLabel + " nhưng hiện chỉ hỗ trợ chi tiết theo từng Điều/Khoản. Vui lòng nêu rõ số điều hoặc nội dung cụ thể bạn cần.");
                response.setMessage("LAW_OVERVIEW_UNSUPPORTED");
            } else {
                response.setAnswer("Hệ thống chưa nhận diện được loại câu hỏi này. Em hãy thử hỏi rõ hơn, ví dụ: 'Điều 2 của Luật Đường bộ nói gì?' hoặc 'Giấy phép lái xe thuộc điều nào?'");
                response.setMessage("UNKNOWN_INTENT");
            }
            response.setResults(Collections.emptyList());
            return response;
        }

        if (isAmbiguousLawQuestion(intent, entities)) {
            response.setAnswer("Câu hỏi chưa đủ rõ vì hệ thống đang có nhiều bộ luật. Vui lòng nêu rõ tên luật, ví dụ: 'Điều 2 của Luật Đường bộ nói gì?'");
            response.setMessage("AMBIGUOUS_LAW");
            response.setResults(Collections.emptyList());
            return response;
        }

        String sparql = generateSparql(intent, entities);
        response.setSparql(sparql == null ? "" : sparql);

        if (sparql == null || sparql.isBlank()) {
            response.setAnswer(formatAnswer(intent, Collections.emptyList(), entities));
            response.setMessage("UNSUPPORTED_QUERY");
            response.setResults(Collections.emptyList());
            return response;
        }

        String endpoint = chooseEndpoint(intent);
        response.setEndpoint(endpoint);

        try {
            List<Map<String, String>> results = fusekiService.query(endpoint, sparql);
            response.setResults(results);
            response.setAnswer(formatAnswer(intent, results, entities));
            if (results == null || results.isEmpty()) {
                response.setMessage("NO_RESULT");
                response.setSuccess(false);
            } else {
                response.setMessage("OK");
                response.setSuccess(true);
            }
        } catch (Exception ex) {
            response.setError(ex.getMessage());
            response.setAnswer("Không truy vấn được Fuseki. Kiểm tra lại endpoint, dataset và service path /query hay /sparql.");
            response.setMessage("FUSEKI_ERROR");
            response.setResults(Collections.emptyList());
        }

        return response;
    }

    private JsonNode readJson(String classpathFile) throws IOException {
        try (InputStream in = new ClassPathResource(classpathFile).getInputStream()) {
            return objectMapper.readTree(in);
        }
    }

    private List<EntityCandidate> buildCandidates(JsonNode node) {
        List<EntityCandidate> out = new ArrayList<>();
        node.fields().forEachRemaining(entry -> {
            String key = entry.getKey();
            JsonNode value = entry.getValue();
            for (JsonNode synonymNode : value.path("synonyms")) {
                String synonym = normalizeText(synonymNode.asText(""));
                if (!synonym.isBlank()) out.add(new EntityCandidate(key, synonym, value));
            }
            String label = normalizeText(value.path("label").asText(""));
            if (!label.isBlank()) out.add(new EntityCandidate(key, label, value));
        });
        out.sort(Comparator.comparingInt((EntityCandidate c) -> c.normalizedSynonym.length()).reversed());
        return out;
    }

    private String normalizeText(String text) {
        if (text == null) return "";
        String s = text.toLowerCase(Locale.ROOT).trim();
        s = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        s = s.replace('đ', 'd');
        s = s.replaceAll("[^\\p{Alnum}\\s]", " ");
        s = s.replaceAll("\\s+", " ").trim();
        return s;
    }

    private String detectIntent(String q) {
        if (containsAny(q, "phat bao nhieu", "muc phat", "bi phat the nao")) return "ASK_PENALTY";
        if (matchesArticleContent(q)) return "ASK_ARTICLE_CONTENT";
        if (containsAny(q, "thuoc dieu nao", "dieu nao quy dinh", "can cu phap ly", "thuoc khoan nao")) return "ASK_LEGAL_BASIS";
        if (containsAny(q, "la gi", "dinh nghia", "khai niem")) return "ASK_DEFINITION";
        if (containsAny(q, "bao gom nhung gi", "gom nhung gi", "bao gom gi", "bao gom cac gi")) return "ASK_INCLUDES";
        if (containsAny(q, "co trach nhiem gi", "trach nhiem gi", "phai lam gi")) return "ASK_RESPONSIBILITY";
        if (containsAny(q, "co phai vi pham khong", "co vi pham khong")) return "ASK_VIOLATION_CHECK";
        if (containsAny(q, "nghiem trong khong", "co nghiem trong khong")) return "ASK_AGGRAVATION";
        if (containsAny(q, "nhung hanh vi vi pham nao", "danh sach hanh vi vi pham", "liet ke hanh vi vi pham")) return "ASK_LIST_VIOLATIONS";
        if (containsAny(q, "ap dung cho ai", "doi tuong ap dung", "ap dung cho")) return "ASK_APPLIES_TO";
        if (containsAny(q, "cho phep", "duoc phep")) return "ASK_PERMISSION";
        if (containsAny(q, "cam", "bi cam")) return "ASK_PROHIBITION";
        if (containsAny(q, "yeu cau", "can phai")) return "ASK_REQUIREMENT";
        if (containsAny(q, "muc dich", "de lam gi")) return "ASK_PURPOSE";
        if (containsAny(q, "ket noi", "noi voi")) return "ASK_CONNECTION";
        if (containsAny(q, "su dung nhu the nao", "su dung")) return "ASK_USAGE";
        return "UNKNOWN";
    }

    private boolean matchesArticleContent(String q) {
        boolean hasArticle = ARTICLE_PATTERN.matcher(q).find();
        boolean hasLaw = !detectLawCode(q).isBlank();
        return hasArticle && (containsAny(q, "noi gi", "noi dung", "quy dinh gi") || hasLaw);
    }

    private boolean containsAny(String q, String... phrases) {
        for (String p : phrases) if (q.contains(p)) return true;
        return false;
    }

    private String detectLawCode(String q) {
        for (Map.Entry<String, String> e : LAW_KEYWORDS.entrySet()) {
            if (q.contains(e.getKey())) return e.getValue();
        }
        return "";
    }

    private boolean isAmbiguousLawQuestion(String intent, Map<String, Object> entities) {
        return Set.of("ASK_ARTICLE_CONTENT", "ASK_LEGAL_BASIS").contains(intent)
                && !stringValue(entities.get("article")).isBlank()
                && stringValue(entities.get("law_code")).isBlank();
    }

    private Map<String, Object> extractEntities(String q) {
        Map<String, Object> entities = new LinkedHashMap<>();
        entities.put("question_norm", q);

        Matcher m = ARTICLE_PATTERN.matcher(q);
        if (m.find()) entities.put("article", m.group(1));
        m = CLAUSE_PATTERN.matcher(q);
        if (m.find()) entities.put("clause", m.group(1));
        m = POINT_PATTERN.matcher(q);
        if (m.find()) entities.put("point", m.group(1));

        String lawCode = detectLawCode(q);
        if (!lawCode.isBlank()) {
            entities.put("law_code", lawCode);
            entities.put("law_label", lawLabelFromCode(lawCode));
        }

        EntityCandidate entity = findFirstCandidate(q, entityCandidates);
        if (entity != null) fillEntityMap(entities, entity, "entity");
        EntityCandidate subject = findFirstCandidate(q, subjectCandidates);
        if (subject != null) fillEntityMap(entities, subject, "subject");
        EntityCandidate condition = findFirstCandidate(q, conditionCandidates);
        if (condition != null) fillEntityMap(entities, condition, "condition");

        return entities;
    }

    private EntityCandidate findFirstCandidate(String q, List<EntityCandidate> candidates) {
        for (EntityCandidate c : candidates) {
            if (q.contains(c.normalizedSynonym)) return c;
        }
        return null;
    }

    private void fillEntityMap(Map<String, Object> entities, EntityCandidate candidate, String prefix) {
        entities.put(prefix + "_key", candidate.key);
        entities.put(prefix + "_label", candidate.data.path("label").asText(""));
        if ("entity".equals(prefix)) {
            entities.put("domain", candidate.data.path("domain").asText(""));
            List<String> hints = new ArrayList<>();
            for (JsonNode hint : candidate.data.path("hints")) hints.add(hint.asText(""));
            entities.put("entity_hints", hints);
        }
    }

    private String lawLabelFromCode(String lawCode) {
        return switch (lawCode) {
            case "LDB" -> "Luật Đường bộ";
            case "TTATGTDB" -> "Luật Trật tự, an toàn giao thông đường bộ";
            case "LLD" -> "Bộ luật Lao động";
            default -> lawCode;
        };
    }

    private String chooseEndpoint(String intent) {
        return INFERENCE_INTENTS.contains(intent) ? inferenceEndpoint : baseEndpoint;
    }

    private String generateSparql(String intent, Map<String, Object> entities) {
        if ("ASK_PENALTY".equals(intent)) return "";

        if ("ASK_ARTICLE_CONTENT".equals(intent)) {
            String article = stringValue(entities.get("article"));
            if (article.isBlank()) return "";
            String clause = stringValue(entities.get("clause"));
            String point = stringValue(entities.get("point"));
            String lawCode = stringValue(entities.get("law_code"));
            String clauseFilter = clause.isBlank() ? "" : "FILTER(?clauseNumber = \"" + escape(clause) + "\")";
            String pointFilter = point.isBlank() ? "" : "FILTER(LCASE(STR(?pointNumber)) = \"" + escape(point.toLowerCase(Locale.ROOT)) + "\")";
            String lawFilter = lawCode.isBlank() ? "" : "FILTER(?lawCode = \"" + escape(lawCode) + "\")";
            return PREFIX + """
                    SELECT DISTINCT ?articleNumber ?articleLabel ?lawCode ?entityLabel ?rawS ?rawO ?clauseNumber ?pointNumber
                    WHERE {
                        ?article rdf:type legal:Article ;
                                 legal:articleNumber ?articleNumber .
                        FILTER(?articleNumber = "%s")

                        OPTIONAL { ?article legal:label ?articleLabel . }
                        OPTIONAL { ?article legal:rawSubject ?rawS . }
                        OPTIONAL { ?article legal:rawObject ?rawO . }
                        OPTIONAL { ?article legal:clauseNumber ?clauseNumber . }
                        OPTIONAL { ?article legal:pointNumber ?pointNumber . }
                        OPTIONAL {
                            ?law legal:hasChapter/legal:hasArticle ?article ;
                                 legal:lawCode ?lawCode .
                        }
                        OPTIONAL {
                            ?article legal:mentionsEntity ?entity .
                            ?entity legal:label ?entityLabel .
                        }
                        %s
                        %s
                        %s
                    }
                    ORDER BY ?lawCode ?clauseNumber ?pointNumber ?entityLabel
                    LIMIT 100
                    """.formatted(escape(article), lawFilter, clauseFilter, pointFilter);
        }

        if ("ASK_LEGAL_BASIS".equals(intent)) {
            if (stringValue(entities.get("entity_label")).isBlank()) return "";
            String lawFilter = stringValue(entities.get("law_code")).isBlank() ? "" :
                    "FILTER(?lawCode = \"" + escape(stringValue(entities.get("law_code"))) + "\")";
            return PREFIX + """
                    SELECT DISTINCT ?article ?articleNumber ?lawCode ?entityLabel
                    WHERE {
                        ?article rdf:type legal:Article ;
                                 legal:articleNumber ?articleNumber ;
                                 legal:mentionsEntity ?entity .
                        ?entity legal:label ?entityLabel .
                        OPTIONAL {
                            ?law legal:hasChapter/legal:hasArticle ?article ;
                                 legal:lawCode ?lawCode .
                        }
                        %s
                        %s
                    }
                    ORDER BY ?lawCode ?articleNumber
                    LIMIT 50
                    """.formatted(entityFilterBlock(entities, "?entity", "?entityLabel"), lawFilter);
        }

        if (RELATION_INTENTS.contains(intent)) {
            if (stringValue(entities.get("entity_label")).isBlank()) return "";
            return PREFIX + """
                    SELECT DISTINCT ?entity ?entityLabel ?subjectLabel ?relationName ?objectLabel ?lawCode ?articleNumber
                    WHERE {
                        ?entity legal:label ?entityLabel .
                        %s

                        ?subject ?rel ?object .
                        ?subject legal:label ?subjectLabel .
                        ?object legal:label ?objectLabel .
                        FILTER(?subject = ?entity)
                        FILTER(%s)

                        BIND(REPLACE(STR(?rel), ".*#", "") AS ?relationName)

                        OPTIONAL {
                            ?article rdf:type legal:Article ;
                                     legal:mentionsEntity ?subject ;
                                     legal:articleNumber ?articleNumber .
                            ?law legal:hasChapter/legal:hasArticle ?article ; legal:lawCode ?lawCode .
                        }
                    }
                    LIMIT 100
                    """.formatted(entityFilterBlock(entities, "?entity", "?entityLabel"), relationFilter(intent));
        }

        if ("ASK_VIOLATION_CHECK".equals(intent)) {
            if (stringValue(entities.get("entity_label")).isBlank()) return "";
            return PREFIX + """
                    SELECT DISTINCT ?entity ?entityLabel ?articleNumber ?lawCode
                    WHERE {
                        ?entity rdf:type legal:HanhViViPham ;
                                legal:label ?entityLabel .
                        %s
                        OPTIONAL {
                            ?article rdf:type legal:Article ;
                                     legal:mentionsEntity ?entity ;
                                     legal:articleNumber ?articleNumber .
                            ?law legal:hasChapter/legal:hasArticle ?article ;
                                 legal:lawCode ?lawCode .
                        }
                    }
                    LIMIT 20
                    """.formatted(entityFilterBlock(entities, "?entity", "?entityLabel"));
        }

        if ("ASK_AGGRAVATION".equals(intent)) {
            if (stringValue(entities.get("entity_label")).isBlank()) return "";
            return PREFIX + """
                    SELECT DISTINCT ?entity ?entityLabel ?articleNumber ?lawCode
                    WHERE {
                        ?entity rdf:type legal:SevereViolation ;
                                legal:label ?entityLabel .
                        %s
                        OPTIONAL {
                            ?article rdf:type legal:Article ;
                                     legal:mentionsEntity ?entity ;
                                     legal:articleNumber ?articleNumber .
                            ?law legal:hasChapter/legal:hasArticle ?article ;
                                 legal:lawCode ?lawCode .
                        }
                    }
                    LIMIT 20
                    """.formatted(entityFilterBlock(entities, "?entity", "?entityLabel"));
        }

        if ("ASK_LIST_VIOLATIONS".equals(intent)) {
            return PREFIX + """
                    SELECT DISTINCT ?entity ?entityLabel
                    WHERE {
                        ?entity rdf:type legal:HanhViViPham ;
                                legal:label ?entityLabel .
                    }
                    ORDER BY ?entityLabel
                    LIMIT 100
                    """;
        }

        return "";
    }

    private String relationFilter(String intent) {
        JsonNode rels = intentRelationMap.path(intent);
        List<String> conditions = new ArrayList<>();
        for (JsonNode rel : rels) {
            conditions.add("STRENDS(STR(?rel), \"#" + escape(rel.asText("")) + "\")");
        }
        return conditions.isEmpty() ? "true" : String.join(" || ", conditions);
    }

    private String entityFilterBlock(Map<String, Object> entities, String entityVar, String labelVar) {
        String label = stringValue(entities.get("entity_label"));
        @SuppressWarnings("unchecked")
        List<String> hints = (List<String>) entities.getOrDefault("entity_hints", Collections.emptyList());
        List<String> conditions = new ArrayList<>();
        for (String hint : hints) {
            conditions.add("STRENDS(STR(" + entityVar + "), \"#" + escape(hint) + "\")");
        }
        if (!label.isBlank()) {
            String esc = escape(label);
            conditions.add("LCASE(STR(" + labelVar + ")) = LCASE(\"" + esc + "\")");
            conditions.add("STRSTARTS(LCASE(STR(" + labelVar + ")), LCASE(\"" + esc + "\"))");
            conditions.add("CONTAINS(LCASE(STR(" + labelVar + ")), LCASE(\"" + esc + "\"))");
        }
        if (conditions.isEmpty()) return "";
        return "FILTER(" + String.join(" || ", conditions) + ")";
    }

    private String escape(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String formatAnswer(String intent, List<Map<String, String>> results, Map<String, Object> entities) {
        if ("ASK_PENALTY".equals(intent)) {
            return "Ontology hiện tại chưa mô hình hóa mức phạt cụ thể, nên hệ thống chưa trả lời chính xác câu hỏi về số tiền phạt.";
        }

        if (results == null || results.isEmpty()) {
            if ("ASK_ARTICLE_CONTENT".equals(intent)) {
                String article = stringValue(entities.get("article"));
                String lawLabel = stringValue(entities.get("law_label"));
                return lawLabel.isBlank()
                        ? "Không tìm thấy nội dung cho Điều " + article + "."
                        : "Không tìm thấy nội dung cho Điều " + article + " của " + lawLabel + ".";
            }
            Map<String, String> fallback = new HashMap<>();
            fallback.put("ASK_DEFINITION", "Không tìm thấy định nghĩa phù hợp.");
            fallback.put("ASK_INCLUDES", "Không tìm thấy nội dung bao gồm phù hợp.");
            fallback.put("ASK_PROHIBITION", "Không tìm thấy nội dung cấm phù hợp.");
            fallback.put("ASK_PERMISSION", "Không tìm thấy nội dung cho phép phù hợp.");
            fallback.put("ASK_REQUIREMENT", "Không tìm thấy yêu cầu phù hợp.");
            fallback.put("ASK_RESPONSIBILITY", "Không tìm thấy thông tin về trách nhiệm phù hợp.");
            fallback.put("ASK_APPLIES_TO", "Không tìm thấy đối tượng áp dụng phù hợp.");
            fallback.put("ASK_PURPOSE", "Không tìm thấy mục đích phù hợp.");
            fallback.put("ASK_CONNECTION", "Không tìm thấy nội dung kết nối phù hợp.");
            fallback.put("ASK_USAGE", "Không tìm thấy nội dung sử dụng phù hợp.");
            fallback.put("ASK_LEGAL_BASIS", "Không tìm thấy căn cứ pháp lý phù hợp.");
            fallback.put("ASK_VIOLATION_CHECK", "Chưa tìm thấy bằng chứng trong ontology suy luận rằng đây là hành vi vi phạm.");
            fallback.put("ASK_AGGRAVATION", "Chưa tìm thấy bằng chứng trong ontology suy luận rằng đây là vi phạm nghiêm trọng.");
            fallback.put("ASK_LIST_VIOLATIONS", "Không tìm thấy danh sách hành vi vi phạm.");
            return fallback.getOrDefault(intent, "Không tìm thấy thông tin phù hợp.");
        }

        if ("ASK_ARTICLE_CONTENT".equals(intent)) {
            String article = stringValue(firstNonBlank(results, "articleNumber", stringValue(entities.get("article"))));
            String lawCode = stringValue(firstNonBlank(results, "lawCode", stringValue(entities.get("law_code"))));
            String lawLabel = !lawCode.isBlank() ? lawLabelFromCode(lawCode) : stringValue(entities.get("law_label"));

            List<String> citations = collectCitations(results);
            List<String> excerpts = new ArrayList<>();
            for (Map<String, String> row : results) {
                String rawS = row.getOrDefault("rawS", "").trim();
                String rawO = row.getOrDefault("rawO", "").trim();
                String excerpt;
                if (!rawS.isBlank() && !rawO.isBlank()) excerpt = rawS + " → " + rawO;
                else if (!rawO.isBlank()) excerpt = rawO;
                else if (!rawS.isBlank()) excerpt = rawS;
                else excerpt = row.getOrDefault("entityLabel", "").trim();
                if (!excerpt.isBlank() && !excerpts.contains(excerpt)) excerpts.add(excerpt);
            }

            StringBuilder sb = new StringBuilder();
            sb.append("Trích dẫn điều luật: ");
            if (!citations.isEmpty()) sb.append(citations.get(0));
            else {
                sb.append("Điều ").append(article);
                if (!lawLabel.isBlank()) sb.append(" của ").append(lawLabel);
            }
            sb.append(".");
            if (!excerpts.isEmpty()) {
                sb.append("\nNội dung liên quan:");
                for (String excerpt : excerpts.subList(0, Math.min(excerpts.size(), 5))) {
                    sb.append("\n- ").append(excerpt);
                }
            }
            List<String> labels = uniqueValues(results, "entityLabel");
            if (!labels.isEmpty()) {
                sb.append("\nThực thể được nhắc tới: ")
                        .append(String.join(", ", labels.subList(0, Math.min(labels.size(), 8))));
            }
            return sb.toString();
        }

        if ("ASK_LEGAL_BASIS".equals(intent)) {
            List<String> citations = collectCitations(results);
            String target = stringValue(entities.get("entity_label"));
            if (citations.isEmpty()) return "Không tìm thấy căn cứ pháp lý phù hợp.";
            StringBuilder sb = new StringBuilder();
            if (!target.isBlank()) sb.append("Căn cứ pháp lý liên quan đến '").append(target).append("':");
            else sb.append("Các căn cứ pháp lý liên quan:");
            for (String citation : citations.subList(0, Math.min(citations.size(), 10))) {
                sb.append("\n- ").append(citation);
            }
            return sb.toString();
        }

        if ("ASK_VIOLATION_CHECK".equals(intent)) {
            String label = results.get(0).getOrDefault("entityLabel", stringValue(entities.get("entity_label")));
            List<String> citations = collectCitations(results);
            String base = "Có. Hệ thống suy luận cho thấy '" + label + "' được phân loại là hành vi vi phạm.";
            return citations.isEmpty() ? base : base + "\nCăn cứ pháp lý: " + String.join("; ", citations.subList(0, Math.min(citations.size(), 3))) + ".";
        }

        if ("ASK_AGGRAVATION".equals(intent)) {
            String label = results.get(0).getOrDefault("entityLabel", stringValue(entities.get("entity_label")));
            List<String> citations = collectCitations(results);
            String base = "Có. Hệ thống suy luận cho thấy '" + label + "' được phân loại là vi phạm nghiêm trọng.";
            return citations.isEmpty() ? base : base + "\nCăn cứ pháp lý: " + String.join("; ", citations.subList(0, Math.min(citations.size(), 3))) + ".";
        }

        if ("ASK_LIST_VIOLATIONS".equals(intent)) {
            List<String> labels = uniqueValues(results, "entityLabel");
            int max = Math.min(labels.size(), 20);
            return labels.isEmpty()
                    ? "Không tìm thấy danh sách hành vi vi phạm."
                    : "Một số hành vi vi phạm: " + String.join(", ", labels.subList(0, max)) + (labels.size() > 20 ? ", ..." : ".");
        }

        Map<String, List<String>> grouped = new LinkedHashMap<>();
        for (Map<String, String> row : results) {
            String subj = row.getOrDefault("subjectLabel", stringValue(entities.get("entity_label")));
            String obj = row.getOrDefault("objectLabel", "");
            if (obj.isBlank()) continue;
            grouped.computeIfAbsent(subj, k -> new ArrayList<>());
            if (!grouped.get(subj).contains(obj)) grouped.get(subj).add(obj);
        }
        if (!grouped.isEmpty()) {
            StringBuilder sb = new StringBuilder();
            int count = 0;
            for (Map.Entry<String, List<String>> entry : grouped.entrySet()) {
                if (count++ > 0) sb.append("\n");
                List<String> objs = entry.getValue();
                sb.append(entry.getKey()).append(": ")
                        .append(String.join("; ", objs.subList(0, Math.min(objs.size(), 10))));
                if (count >= 5) break;
            }
            List<String> citations = collectCitations(results);
            if (!citations.isEmpty()) {
                sb.append("\nCăn cứ pháp lý: ");
                sb.append(String.join("; ", citations.subList(0, Math.min(citations.size(), 5))));
                sb.append(".");
            }
            return sb.toString();
        }
        return "Đã tìm thấy dữ liệu nhưng chưa định dạng được câu trả lời phù hợp.";
    }

    private String firstNonBlank(List<Map<String, String>> results, String key, String fallback) {
        for (Map<String, String> row : results) {
            String value = row.getOrDefault(key, "").trim();
            if (!value.isBlank()) return value;
        }
        return fallback;
    }

    private List<String> collectCitations(List<Map<String, String>> results) {
        LinkedHashSet<String> citations = new LinkedHashSet<>();
        for (Map<String, String> row : results) {
            String article = row.getOrDefault("articleNumber", "").trim();
            if (article.isBlank()) article = row.getOrDefault("article", "").trim();
            String clause = row.getOrDefault("clauseNumber", "").trim();
            String point = row.getOrDefault("pointNumber", "").trim();
            String lawCode = row.getOrDefault("lawCode", "").trim();

            List<String> parts = new ArrayList<>();
            if (!lawCode.isBlank()) parts.add(lawLabelFromCode(lawCode));
            if (!article.isBlank()) parts.add("Điều " + article);
            if (!clause.isBlank()) parts.add("Khoản " + clause);
            if (!point.isBlank()) parts.add("Điểm " + point);
            if (!parts.isEmpty()) citations.add(String.join(", ", parts));
        }
        return new ArrayList<>(citations);
    }

    private List<String> uniqueValues(List<Map<String, String>> results, String key) {
        Set<String> values = new LinkedHashSet<>();
        for (Map<String, String> row : results) {
            String value = row.getOrDefault(key, "");
            if (!value.isBlank()) values.add(value);
        }
        return new ArrayList<>(values);
    }

    private static class EntityCandidate {
        private final String key;
        private final String normalizedSynonym;
        private final JsonNode data;

        private EntityCandidate(String key, String normalizedSynonym, JsonNode data) {
            this.key = key;
            this.normalizedSynonym = normalizedSynonym;
            this.data = data;
        }
    }
}
