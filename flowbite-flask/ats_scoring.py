import os
import re
import magic
import traceback
from PyPDF2 import PdfReader
from docx import Document
import google.generativeai as genai
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Configure Gemini API if key is available
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY not found. Using mock data.")

def generate_prompt(resume_text):
    prompt = f"""
You are an ATS (Applicant Tracking System) analysis expert. 
Analyze the following resume text and provide a structured response in the exact format below:

OVERALL ATS COMPATIBILITY SCORE: [number from 0-100]

BREAKDOWN:
Keywords Match: [score 0-100] - [brief description]
Format Compatibility: [score 0-100] - [brief description]  
Section Organization: [score 0-100] - [brief description]
Contact Information: [score 0-100] - [brief description]
Skills Alignment: [score 0-100] - [brief description]

RECOMMENDATIONS:
1. [specific improvement recommendation]
2. [specific improvement recommendation]
3. [specific improvement recommendation]
4. [specific improvement recommendation]
5. [specific improvement recommendation]

Resume Text:
{resume_text[:3000]}
"""
    return prompt

def analyze_ats_with_gemini(prompt):
    if not api_key:
        logger.warning("Gemini API key missing. Returning mock data.")
        return get_mock_data()

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")  # or gemini-pro
        response = model.generate_content(prompt)

        if not response or not response.text:
            raise ValueError("Empty response from Gemini API.")

        return parse_gemini_output(response.text)

    except Exception as e:
        logger.error(f"Error during Gemini API call: {e}")
        return get_mock_data()

def extract_text(file_path):
    try:
        logger.info(f"Extracting text from: {file_path}")
        mime = magic.Magic(mime=True).from_file(file_path)
        logger.info(f"File mime type: {mime}")

        if mime == 'application/pdf':
            reader = PdfReader(file_path)
            text = '\n'.join([p.extract_text() or '' for p in reader.pages])
            return text

        elif mime in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            doc = Document(file_path)
            text = '\n'.join([p.text for p in doc.paragraphs])
            return text

        else:
            logger.error(f"Unsupported file type: {mime}")
            return 'Unsupported file type'

    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return 'Error extracting text'

def parse_gemini_output(text):
    try:
        logger.info("Parsing Gemini output")

        overall_score = 70  # default
        match = re.search(r'OVERALL ATS COMPATIBILITY SCORE:\s*(\d+)', text, re.IGNORECASE)
        if match:
            overall_score = int(match.group(1))

        categories = [
            'Keywords Match', 'Format Compatibility',
            'Section Organization', 'Contact Information', 'Skills Alignment'
        ]
        breakdown = []

        for cat in categories:
            match = re.search(rf'{cat}:\s*(\d+)\s*-\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                desc = match.group(2).strip()
                breakdown.append({'category': cat, 'score': score, 'description': desc})
            else:
                breakdown.append({
                    'category': cat,
                    'score': overall_score,
                    'description': f'No specific feedback found for {cat}'
                })

        recs = re.findall(r'(?:^|\n)\s*\d+\.\s*(.+?)(?=\n\d+\.|\n[A-Z]|\Z)', text, re.MULTILINE | re.DOTALL)
        if not recs:
            recs = [
                'Add more industry-specific keywords',
                'Include quantifiable achievements',
                'Ensure clear section headers and formatting',
                'Include relevant technical skills',
                'Use action verbs in bullet points'
            ]

        return {
            'overallScore': overall_score,
            'breakdown': breakdown,
            'recommendations': recs[:5]
        }

    except Exception as e:
        logger.error(f"Error parsing Gemini output: {str(e)}")
        return get_mock_data()

def get_mock_data():
    return {
        'overallScore': 75,
        'breakdown': [
            {'category': 'Keywords Match', 'score': 70, 'description': 'Some relevant keywords present'},
            {'category': 'Format Compatibility', 'score': 85, 'description': 'Good ATS-friendly format'},
            {'category': 'Section Organization', 'score': 80, 'description': 'Well-structured sections'},
            {'category': 'Contact Information', 'score': 90, 'description': 'Complete contact details'},
            {'category': 'Skills Alignment', 'score': 65, 'description': 'Skills section needs improvement'}
        ],
        'recommendations': [
            'Add more industry-specific keywords',
            'Include quantifiable achievements with metrics',
            'Ensure consistent formatting',
            'Add a detailed skills section',
            'Use action verbs in bullet points'
        ]
    }
