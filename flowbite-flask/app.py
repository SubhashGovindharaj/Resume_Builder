from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import google.generativeai as genai
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
import magic
import re
import traceback
import logging
from authlib.integrations.flask_client import OAuth

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup
app = Flask(__name__)
load_dotenv()

# Load keys
app.secret_key = os.getenv("SECRET_KEY")
api_key = os.getenv("GEMINI_API_KEY")
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

if not api_key:
    logger.error("GEMINI_API_KEY not found in environment variables")
else:
    logger.info(f"GEMINI_API_KEY loaded: {api_key[:10]}...")
    genai.configure(api_key=api_key)

# OAuth config
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=client_id,
    client_secret=client_secret,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v2/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v2/userinfo',
    client_kwargs={'scope': 'openid email profile'},
    redirect_uri='http://127.0.0.1:5000/authorize'
)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Routes
@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)



@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    session['user'] = user_info
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/resume-options')
def resume_options():
    return render_template('resume-options.html')

@app.route('/upload-resume', methods=['GET'])
def upload_resume():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if file:
            secured_filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], secured_filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(path)
            return jsonify({
                'success': True,
                'filename': secured_filename,
                'originalName': file.filename
            }), 200
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/templates.html')
def templates():
    return render_template('templates.html')

@app.route('/download.html')
def download():
    session_id = request.args.get('session')
    return render_template('download.html', session=session_id)

@app.route('/build-resume', methods=['GET'])
def build_resume():
    return render_template('build-resume.html')

@app.route('/ats-score')
def ats_score():
    file_param = request.args.get('file')
    enhanced_param = request.args.get('enhanced')
    return render_template('ats-score.html', file=file_param, enhanced=enhanced_param)

@app.route('/api/analyze-ats', methods=['POST'])
def analyze_ats():
    try:
        data = request.get_json()
        file_name = data.get('fileName')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)

        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on server'}), 404

        resume_text = extract_text(file_path)
        if not resume_text or resume_text == 'Unsupported file type':
            return jsonify({'error': 'Could not extract text from file'}), 400

        if not api_key:
            return jsonify(get_mock_data())

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
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        if not response or not response.text:
            raise Exception("Empty response from Gemini")
        return jsonify(parse_gemini_output(response.text))

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Helpers
def extract_text(file_path):
    try:
        mime = magic.Magic(mime=True).from_file(file_path)
        if mime == 'application/pdf':
            reader = PdfReader(file_path)
            return '\n'.join([p.extract_text() or '' for p in reader.pages])
        elif mime in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            doc = Document(file_path)
            return '\n'.join([p.text for p in doc.paragraphs])
        else:
            return 'Unsupported file type'
    except:
        return 'Error extracting text'

def parse_gemini_output(text):
    try:
        score = int(re.search(r'OVERALL ATS COMPATIBILITY SCORE:\s*(\d+)', text).group(1))
    except:
        score = 75
    breakdown = [
        {'category': cat, 'score': score, 'description': f'Analysis for {cat.lower()}'}
        for cat in ['Keywords Match', 'Format Compatibility', 'Section Organization', 'Contact Information', 'Skills Alignment']
    ]
    recommendations = re.findall(r'\d+\.\s(.+)', text)
    if not recommendations:
        recommendations = [
            'Add more industry-specific keywords',
            'Include quantifiable achievements',
            'Ensure consistent formatting',
            'Add relevant technical skills',
            'Use action verbs in bullet points'
        ]
    return {
        'overallScore': score,
        'breakdown': breakdown,
        'recommendations': recommendations[:5]
    }

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
            'Include quantifiable achievements with numbers and percentages',
            'Ensure consistent formatting',
            'Add a comprehensive skills section',
            'Use action verbs to start bullet points'
        ]
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)