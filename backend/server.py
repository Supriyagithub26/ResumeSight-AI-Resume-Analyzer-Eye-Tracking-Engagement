#!/usr/bin/env python3
"""
ResumeSight Backend - Resume Analysis Server
Analyzes resumes and provides ATS scoring, skill matching, and JD comparison
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import re
from collections import Counter
from pathlib import Path

# Try to import PDF/DOCX parsers; fall back to text-only if not available
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000", "localhost:8000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = '/tmp'

KEYWORD_WEIGHTS = {
    "java": 10, "python": 10, "javascript": 10, "typescript": 10, "csharp": 10,
    "sql": 8, "aws": 8, "docker": 8, "kubernetes": 8, "gcp": 8, "azure": 8,
    "spring": 9, "react": 9, "angular": 9, "vue": 9, "node": 9, "express": 9,
    "microservices": 9, "rest": 8, "graphql": 8, "api": 7,
    "agile": 7, "scrum": 7, "git": 7, "ci/cd": 7, "jenkins": 7,
    "led": 6, "managed": 6, "developed": 6, "implemented": 6, "designed": 6, "optimized": 6,
    "improved": 5, "achieved": 5, "delivered": 5, "increased": 5, "reduced": 5,
    "html": 6, "css": 6, "linux": 7, "bash": 6, "powerShell": 6,
    "tensorflow": 8, "pytorch": 8, "machine learning": 9, "ai": 8, "nlp": 8
}

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    """Main resume analysis endpoint"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Extract text from file
        resume_text = extract_text_from_file(file)
        if not resume_text:
            return jsonify({"error": "Could not extract text from file"}), 400
        
        # Get optional JD and gaze data
        jd = request.form.get('jd', '').strip()
        gaze_data = request.form.get('gazeData', '')
        
        # Perform analysis
        analysis = perform_analysis(resume_text, jd, gaze_data)
        
        return jsonify(analysis), 200
    
    except Exception as e:
        print(f"Error analyzing resume: {e}")
        return jsonify({"error": str(e)}), 500

def extract_text_from_file(file):
    """Extract text from PDF, DOCX, or TXT files"""
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.pdf'):
            return extract_pdf(file)
        elif filename.endswith('.docx'):
            return extract_docx(file)
        elif filename.endswith('.doc'):
            return extract_docx(file)
        elif filename.endswith('.txt'):
            return file.read().decode('utf-8', errors='ignore')
        else:
            return file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def extract_pdf(file):
    """Extract text from PDF"""
    if not HAS_PDF:
        return None
    
    try:
        pdf = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text
    except:
        return None

def extract_docx(file):
    """Extract text from DOCX"""
    if not HAS_DOCX:
        return None
    
    try:
        doc = Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except:
        return None

def perform_analysis(resume_text, jd, gaze_data):
    """Analyze resume and generate report"""
    lower_text = resume_text.lower()
    
    # Extract sections from resume
    sections = extract_sections(resume_text)
    
    # Extract actual skills found in resume
    found_skills = extract_actual_skills(resume_text)
    
    # Calculate ATS score based on content quality
    ats_score = calculate_ats_score_detailed(resume_text, sections, found_skills)
    
    # Extract experience from actual content
    experience = extract_experience_from_sections(sections)
    
    # Analyze gaze data for engagement
    gaze_insights = analyze_gaze_data(gaze_data, resume_text)
    
    # Generate personalized recommendations
    recommendations = []
    jd_match = None
    
    if jd:
        jd_match = calculate_jd_match_detailed(resume_text, jd, found_skills)
        recommendations = generate_jd_specific_recommendations(resume_text, jd, found_skills, sections)
    else:
        recommendations = generate_resume_specific_recommendations(resume_text, found_skills, sections)
    
    # Add gaze-based insights
    if gaze_insights:
        recommendations.insert(0, gaze_insights)
    
    skills_matched = f"{len(found_skills)}/12"
    
    result = {
        "atsScore": ats_score,
        "skillsMatched": skills_matched,
        "experience": experience,
        "recommendations": recommendations,
        "foundSkills": list(found_skills)[:5]  # Top 5 skills found
    }
    
    if jd_match is not None:
        result["jdMatch"] = f"{jd_match}%"
    
    return result

def extract_sections(text):
    """Extract resume sections"""
    sections = {
        'experience': '',
        'education': '',
        'skills': '',
        'projects': '',
        'contact': '',
        'summary': ''
    }
    
    patterns = {
        'experience': r'(experience|work history|professional experience)(.*?)(?=\n\n|\Z)',
        'education': r'(education|qualification|degree)(.*?)(?=\n\n|\Z)',
        'skills': r'(skills|technical|competencies)(.*?)(?=\n\n|\Z)',
        'projects': r'(project|portfolio|achievement)(.*?)(?=\n\n|\Z)',
        'contact': r'(contact|phone|email)(.*?)(?=\n\n|\Z)',
        'summary': r'(summary|objective|profile)(.*?)(?=\n\n|\Z)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            sections[key] = match.group(2) if match.lastindex > 1 else match.group(0)
    
    return sections

def extract_actual_skills(text):
    """Extract skills actually mentioned in resume"""
    found_skills = set()
    text_lower = text.lower()
    
    # Check each keyword
    for keyword in KEYWORD_WEIGHTS.keys():
        if keyword.lower() in text_lower:
            found_skills.add(keyword)
    
    # Also look for skill patterns
    skill_patterns = [
        r'\b(sql|mysql|postgresql|mongodb|redis)\b',
        r'\b(html|css|javascript|typescript|react|vue|angular)\b',
        r'\b(python|java|cpp|csharp|golang|rust|ruby)\b',
        r'\b(aws|azure|gcp|docker|kubernetes|jenkins)\b',
        r'\b(git|svn|github|gitlab)\b',
        r'\b(agile|scrum|kanban|waterfall)\b',
    ]
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, text_lower)
        found_skills.update(matches)
    
    return found_skills

def calculate_ats_score_detailed(text, sections, skills):
    """Calculate ATS score based on detailed content analysis"""
    score = 50
    
    # Skills variety (0-20 points)
    score += min(20, len(skills) * 2)
    
    # Section completeness (0-15 points)
    complete_sections = sum(1 for section in sections.values() if len(section.strip()) > 50)
    score += min(15, complete_sections * 3)
    
    # Contact info (0-5 points)
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        score += 5
    
    # Action verbs and quantifiable metrics (0-15 points)
    action_verbs = ['led', 'managed', 'developed', 'implemented', 'designed', 'optimized',
                    'improved', 'achieved', 'delivered', 'increased', 'reduced', 'created',
                    'spearheaded', 'orchestrated', 'architected']
    action_count = sum(text.lower().count(verb) for verb in action_verbs)
    score += min(15, action_count)
    
    # Numbers/metrics (0-10 points)
    metrics = len(re.findall(r'\d+%|\$\d+|\d+\s*(?:years?|months?|projects?)', text))
    score += min(10, metrics)
    
    # Content length assessment (0-10 points)
    if 300 < len(text) < 6000:
        score += 10
    elif len(text) >= 300:
        score += 7
    
    # Professional language check (0-5 points)
    formal_words = ['professional', 'managed', 'leadership', 'strategic', 'innovative']
    if sum(text.lower().count(word) for word in formal_words) > 2:
        score += 5
    
    return min(100, max(0, score))

def extract_experience_from_sections(sections):
    """Extract years of experience from experience section"""
    exp_section = sections.get('experience', '') + ' ' + sections.get('summary', '')
    
    patterns = [
        r'(\d+)\s*\+?\s*years?\s+of\s+(?:professional\s+)?experience',
        r'(\d+)\s*\+?\s*years?\s+in\s+(?:the\s+)?(?:field|industry)',
        r'(\d+)\s*\+?\s*years?\s+(?:professional)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, exp_section, re.IGNORECASE)
        if match:
            years = match.group(1)
            return f"{years}+ years"
    
    # Count years from dates if available
    year_matches = re.findall(r'(20\d{2})', exp_section)
    if len(year_matches) >= 2:
        years_diff = int(year_matches[-1]) - int(year_matches[0])
        if years_diff > 0:
            return f"{years_diff}+ years"
    
    return "Not specified"

def analyze_gaze_data(gaze_data_str, resume_text):
    """Analyze gaze data for engagement insights"""
    if not gaze_data_str:
        return None
    
    try:
        gaze_points = json.loads(gaze_data_str)
        if not gaze_points or len(gaze_points) < 5:
            return None
        
        # Calculate engagement metrics
        engagement_level = min(100, len(gaze_points) * 2)
        avg_time = sum(p.get('time', 0) for p in gaze_points) / len(gaze_points) if gaze_points else 0
        
        if engagement_level > 70:
            return f"👁️ Strong engagement detected - user focused intently on content ({len(gaze_points)} gaze points recorded)"
        elif engagement_level > 40:
            return f"👁️ Moderate engagement - eye tracking captured {len(gaze_points)} focus points"
        else:
            return f"👁️ User attention captured - {len(gaze_points)} gaze data points"
    except:
        return None

def calculate_jd_match_detailed(resume_text, jd_text, resume_skills):
    """Calculate detailed JD match percentage"""
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()
    
    # Extract required skills from JD
    jd_skills = set()
    for keyword in KEYWORD_WEIGHTS.keys():
        if keyword.lower() in jd_lower:
            jd_skills.add(keyword)
    
    # Skills match
    skill_matches = resume_skills.intersection(jd_skills)
    skill_score = (len(skill_matches) / max(len(jd_skills), 1)) * 40
    
    # Keywords/phrases match
    jd_keywords = extract_keywords(jd_lower)
    resume_keywords = extract_keywords(resume_lower)
    keyword_matches = jd_keywords.intersection(resume_keywords)
    keyword_score = (len(keyword_matches) / max(len(jd_keywords), 1)) * 35
    
    # Experience level match
    exp_score = 15
    if 'senior' in jd_lower and ('senior' in resume_lower or 'lead' in resume_lower):
        exp_score = 15
    elif 'junior' in jd_lower and ('junior' in resume_lower or 'entry' in resume_lower):
        exp_score = 15
    elif 'mid' in jd_lower or 'mid-level' in jd_lower:
        exp_score = 15
    
    total = int(skill_score + keyword_score + exp_score)
    return min(100, total)

def generate_jd_specific_recommendations(resume_text, jd, found_skills, sections):
    """Generate JD-specific recommendations"""
    jd_lower = jd.lower()
    resume_lower = resume_text.lower()
    recs = []
    
    # Check for specific missing keywords
    jd_keywords = extract_keywords(jd_lower)
    missing = jd_keywords - extract_keywords(resume_lower)
    
    if missing:
        top_missing = list(missing)[:3]
        recs.append(f"✓ Add missing JD keywords: {', '.join(top_missing)}")
    
    # Experience section feedback
    exp_section = sections.get('experience', '')
    if len(exp_section) < 200:
        recs.append("✓ Expand experience section with more details matching JD requirements")
    elif not any(verb in exp_section.lower() for verb in ['led', 'managed', 'architected', 'spearheaded']):
        recs.append("✓ Add leadership/impact metrics to align with JD expectations")
    
    # Skills alignment
    jd_skills = {k for k in KEYWORD_WEIGHTS.keys() if k in jd_lower}
    missing_skills = jd_skills - found_skills
    if missing_skills:
        recs.append(f"✓ Highlight or add relevant skills: {', '.join(list(missing_skills)[:3])}")
    
    # Projects section for JD
    if 'project' not in sections.get('projects', '').lower() and len(sections.get('projects', '')) < 100:
        recs.append("✓ Add relevant projects that demonstrate JD-required skills")
    
    recs.append("✓ Tailor bullet points to match JD language and requirements")
    
    return recs

def generate_resume_specific_recommendations(resume_text, found_skills, sections):
    """Generate resume-specific improvement recommendations"""
    recs = []
    
    # Skills feedback
    if len(found_skills) < 5:
        recs.append(f"✓ Add more technical skills ({len(found_skills)}/8 detected)")
    else:
        recs.append(f"✓ Good skill variety detected ({len(found_skills)} skills)")
    
    # Section analysis
    exp_section = sections.get('experience', '')
    if len(exp_section) < 150:
        recs.append("✓ Expand experience section with specific achievements and metrics")
    elif not any(char.isdigit() for char in exp_section):
        recs.append("✓ Add quantifiable metrics (percentages, numbers) to experience")
    
    edu_section = sections.get('education', '')
    if len(edu_section) < 50:
        recs.append("✓ Include education details (degree, university, graduation year)")
    
    # Format/presentation
    action_verbs = ['led', 'managed', 'developed', 'implemented', 'designed', 'optimized']
    if not any(verb in resume_text.lower() for verb in action_verbs):
        recs.append("✓ Use strong action verbs to describe accomplishments")
    
    # Contact info
    if '@' not in resume_text:
        recs.append("✓ Include email address and professional contact information")
    
    if 'linkedin' not in resume_text.lower():
        recs.append("✓ Add LinkedIn profile URL for better visibility")
    
    return recs

def extract_skills(text):
    """Extract recognized skills from resume text (kept for compatibility)"""
    skills = set()
    for keyword in KEYWORD_WEIGHTS.keys():
        if keyword.lower() in text:
            skills.add(keyword)
    return skills

def extract_keywords(text):
    """Extract meaningful keywords from text"""
    # Split into words and filter
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Common stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'that', 'this', 'is', 'are', 'was', 'be',
        'have', 'has', 'do', 'does', 'did', 'will', 'should', 'would', 'could',
        'your', 'our', 'their', 'should', 'experience', 'role', 'position',
        'job', 'work', 'candidate', 'required', 'skills', 'you', 'we', 'us'
    }
    
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    return set(keywords)

def generate_jd_recommendations(resume_text, jd, skills):
    """Generate recommendations based on JD matching (legacy - use new version)"""
    recs = [
        "✓ Align experience descriptions with JD requirements",
        "✓ Incorporate specific keywords from the job posting",
        "✓ Highlight skills that match the JD most closely",
        "✓ Use similar terminology as the job description",
        "✓ Add missing qualifications if you possess them"
    ]
    return recs

def generate_generic_recommendations(resume_text, skills):
    """Generate general resume improvement recommendations (legacy - use new version)"""
    recs = [
        "✓ Add more technical keywords relevant to your target role",
        "✓ Restructure bullet points with quantifiable achievements (numbers, %)",
        "✓ Include professional certifications and credentials",
        "✓ Add LinkedIn URL and contact information",
        "✓ Ensure consistent formatting throughout the document",
        "✓ Use strong action verbs to describe accomplishments"
    ]
    
    if len(skills) < 5:
        recs.insert(0, "✓ Add more technical skills to increase visibility")
    
    return recs

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    print("ResumeSight Backend Server Starting...")
    print("🚀 Server running on http://localhost:8080")
    print("📄 Upload resumes to /api/analyze")
    print()
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False,
        threaded=True
    )
