import pdfplumber
import os
import re
import json
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

# Groq API Key from .env
groq_api_key = os.getenv("GROQ_API_KEY")

# LangChain Groq Chat setup
llm = ChatGroq(
    api_key=groq_api_key,
    model_name="llama-3.3-70b-versatile"
)

# Extract text from PDF
def extract_resume_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# LangChain prompt logic
def parse_resume_text_with_langchain(text):
    prompt = f"""
From the following resume text, extract:
- Full Name
- Job Title
- Phone Number
- Email Address
- Location 
- LinkedIn Profile URL
- GitHub Profile URL
- Technical Skills
- Soft Skills
- Work Experience (job title, company, start_date,end_date, description)- use the same field names as in the example
- Achievements
- Summary or professional summary
- Education (field_of_study, degree, institution, year,percentage_or_cgpa - use the same field names as in the example)
- Certifications
- Projects (title, description, tools, duration, github_url - use the same field names as in the example)

Omit missing fields.

Format the result in clean JSON like:
{{
  "name": "",
  "job_title": "",
  "phone": "",
  "email": "",
  "location": "",
  "linkedin": "",
  "github": "",
  "technical_skills": [],
  "soft_skills": [],
  "experience": [],
  "achievements": [],
  "summary": "",
  "education": [],
  "certifications": [],
  "projects": []
}}

Resume Text:
{text}

*Deliverables*:
- Return the parsed resume fields in JSON format as specified above.
- DO NOT include any additional text or explanations, just the JSON output.
"""

    messages = [
        SystemMessage(content="You are a professional resume parser."),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    return response.content


# Optional cleaning function (removes empty strings, trims whitespace)
def clean_parsed_data(data):
    if isinstance(data, dict):
        return {k: clean_parsed_data(v) for k, v in data.items() if v not in ["", None, [], {}]}
    elif isinstance(data, list):
        return [clean_parsed_data(i) for i in data if i not in ["", None, [], {}]]
    elif isinstance(data, str):
        return data.strip()
    return data


# Main function
def main(pdf_path):
    # Step 1: Extract raw text from PDF
    resume_text = extract_resume_text(pdf_path)

    # Step 2: Get raw response from LLM
    llm_response = parse_resume_text_with_langchain(resume_text)
    
    if not llm_response:
        print("Empty response from LLM.")
        return {}

    # Step 3: Remove CropBox logs (pdfplumber logs show up in stdout, not in response — safe to skip)

    # Step 4: Remove triple quotes or code blocks
    cleaned = llm_response.strip()

    # Remove surrounding triple quotes (""") or triple backticks (```)
    cleaned = re.sub(r'^[`"]{3}', '', cleaned)
    cleaned = re.sub(r'[`"]{3}$', '', cleaned)

    # Step 5: Try parsing JSON
    try:
        parsed_data = json.loads(cleaned)
        return clean_parsed_data(parsed_data)
    except json.JSONDecodeError as e:
        print(f"Error parsing cleaned response: {e}")
        return {}
    

if __name__ == "__main__":
    result = main("flowbite-flask/data/Nilofer_Data_scientist.pdf")
    print(result)
