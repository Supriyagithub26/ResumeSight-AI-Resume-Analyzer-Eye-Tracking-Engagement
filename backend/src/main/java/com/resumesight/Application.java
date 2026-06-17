package com.resumesight;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.*;
import java.util.*;
import java.util.regex.*;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:8000")
class ResumeController {
    
    private final ResumeAnalyzer analyzer = new ResumeAnalyzer();
    
    @PostMapping("/analyze")
    public AnalysisResponse analyze(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "jd", required = false) String jobDescription,
            @RequestParam(value = "gazeData", required = false) String gazeData) {
        
        try {
            String resumeText = extractText(file);
            return analyzer.analyze(resumeText, jobDescription, gazeData);
        } catch (Exception e) {
            e.printStackTrace();
            return new AnalysisResponse(0, "Error analyzing resume", null, null);
        }
    }
    
    private String extractText(MultipartFile file) throws Exception {
        String filename = file.getOriginalFilename();
        if (filename.endsWith(".pdf")) {
            return extractFromPDF(file);
        } else if (filename.endsWith(".docx")) {
            return extractFromDOCX(file);
        } else if (filename.endsWith(".txt")) {
            return new String(file.getBytes());
        }
        return "";
    }
    
    private String extractFromPDF(MultipartFile file) throws Exception {
        try (InputStream is = file.getInputStream()) {
            org.apache.pdfbox.pdmodel.PDDocument doc = org.apache.pdfbox.pdmodel.PDDocument.load(is);
            org.apache.pdfbox.text.PDFTextStripper stripper = new org.apache.pdfbox.text.PDFTextStripper();
            String text = stripper.getText(doc);
            doc.close();
            return text;
        }
    }
    
    private String extractFromDOCX(MultipartFile file) throws Exception {
        try (InputStream is = file.getInputStream()) {
            org.apache.poi.xwpf.usermodel.XWPFDocument doc = new org.apache.poi.xwpf.usermodel.XWPFDocument(is);
            StringBuilder text = new StringBuilder();
            for (org.apache.poi.xwpf.usermodel.XWPFParagraph para : doc.getParagraphs()) {
                text.append(para.getText()).append("\n");
            }
            doc.close();
            return text.toString();
        }
    }
}

class ResumeAnalyzer {
    private static final Map<String, Integer> KEYWORD_WEIGHTS = Map.ofEntries(
        Map.entry("java", 10), Map.entry("python", 10), Map.entry("javascript", 10),
        Map.entry("sql", 8), Map.entry("aws", 8), Map.entry("docker", 8),
        Map.entry("spring", 9), Map.entry("react", 9), Map.entry("microservices", 9),
        Map.entry("agile", 7), Map.entry("scrum", 7), Map.entry("git", 7),
        Map.entry("led", 6), Map.entry("managed", 6), Map.entry("developed", 6),
        Map.entry("implemented", 6), Map.entry("designed", 6), Map.entry("optimized", 6),
        Map.entry("improved", 5), Map.entry("achieved", 5), Map.entry("delivered", 5)
    );
    
    public AnalysisResponse analyze(String resumeText, String jd, String gazeData) {
        String lower = resumeText.toLowerCase();
        
        // Extract skills
        Set<String> skills = extractSkills(lower);
        
        // Calculate ATS score
        int atsScore = calculateAtsScore(lower, skills);
        
        // Extract experience years
        String experience = extractExperience(lower);
        
        // Calculate JD match if provided
        String jdMatch = null;
        List<String> recommendations = new ArrayList<>();
        
        if (jd != null && !jd.isEmpty()) {
            jdMatch = calculateJDMatch(lower, jd.toLowerCase(), skills) + "%";
            recommendations.addAll(generateJDBasedRecommendations(lower, jd, skills));
        } else {
            recommendations.addAll(generateGenericRecommendations(lower, skills));
        }
        
        // Include gaze insights if available
        if (gazeData != null && !gazeData.isEmpty()) {
            recommendations.add("💡 Eye tracking detected focus on key sections - areas reviewed are engagement signals");
        }
        
        String skillsMatched = skills.size() + "/12";
        return new AnalysisResponse(atsScore, skillsMatched, experience, jdMatch, recommendations);
    }
    
    private Set<String> extractSkills(String text) {
        Set<String> skills = new HashSet<>();
        for (String keyword : KEYWORD_WEIGHTS.keySet()) {
            if (text.contains(keyword)) {
                skills.add(keyword);
            }
        }
        return skills;
    }
    
    private int calculateAtsScore(String text, Set<String> skills) {
        int score = 50; // baseline
        
        // Keywords boost
        score += skills.size() * 2;
        
        // Format indicators
        if (text.contains("email") || text.contains("phone")) score += 5;
        if (text.contains("linkedin")) score += 5;
        if (text.contains("experience") && text.contains("education")) score += 10;
        if (text.matches(".*\\b\\d{4}\\b.*")) score += 5; // years
        
        // Deductions
        if (text.length() < 500) score -= 10;
        if (!text.contains("@") && !text.contains("phone")) score -= 5;
        
        return Math.min(100, Math.max(0, score));
    }
    
    private String extractExperience(String text) {
        Pattern p = Pattern.compile("(\\d+)\\s*\\+?\\s*years");
        Matcher m = p.matcher(text);
        if (m.find()) {
            return m.group(1) + "+ years";
        }
        return "Not specified";
    }
    
    private int calculateJDMatch(String resume, String jd, Set<String> skills) {
        Set<String> jdKeywords = extractKeywords(jd);
        int matched = 0;
        for (String keyword : jdKeywords) {
            if (resume.contains(keyword)) matched++;
        }
        return jdKeywords.isEmpty() ? 0 : (int) ((matched * 100.0) / jdKeywords.size());
    }
    
    private Set<String> extractKeywords(String text) {
        Set<String> keywords = new HashSet<>();
        for (String word : text.split("\\s+")) {
            if (word.length() > 4 && !isCommonWord(word)) {
                keywords.add(word.toLowerCase());
            }
        }
        return keywords;
    }
    
    private boolean isCommonWord(String word) {
        String[] common = {"the", "and", "with", "from", "that", "this", "your", "should", "experience"};
        return Arrays.asList(common).contains(word.toLowerCase());
    }
    
    private List<String> generateJDBasedRecommendations(String resume, String jd, Set<String> skills) {
        List<String> recs = new ArrayList<>();
        recs.add("✓ Add missing skills from JD: Highlight relevant certifications");
        recs.add("✓ Align bullet points with JD requirements");
        recs.add("✓ Use JD terminology in your experience section");
        return recs;
    }
    
    private List<String> generateGenericRecommendations(String resume, Set<String> skills) {
        List<String> recs = new ArrayList<>();
        recs.add("✓ Add more technical keywords relevant to your target role");
        recs.add("✓ Restructure bullet points with quantifiable achievements");
        recs.add("✓ Include certifications and LinkedIn URL");
        recs.add("✓ Improve formatting consistency");
        return recs;
    }
}

record AnalysisResponse(
    int atsScore,
    String skillsMatched,
    String experience,
    String jdMatch,
    List<String> recommendations
) {
    public AnalysisResponse(int atsScore, String message, String skills, String experience) {
        this(atsScore, skills, experience, null, List.of(message));
    }
}