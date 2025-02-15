import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import requests
import uuid
from fastapi.templating import Jinja2Templates
from fastapi import Request
import logging
from fastapi.middleware.cors import CORSMiddleware
from langdetect import detect, LangDetectException
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Initialize FastAPI app
app = FastAPI()

# Set up CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants for Azure endpoint
AZURE_REGION = "eastus"
AZURE_ENDPOINT = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
AZURE_VOICES_LIST_ENDPOINT = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list"

# S3 bucket configuration
S3_BUCKET_NAME = "text-to-speech-files-123"  # Replace with your S3 bucket name
S3_INPUT_FOLDER = "input/"
S3_SSML_FOLDER = "ssml/"
S3_AUDIO_FOLDER = "audio/"

# Set up templates folder for serving HTML files
templates = Jinja2Templates(directory="templates")

# Serve static files (for audio and other static resources)
#app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html file as the homepage
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Function to clean up text (remove placeholders like [PH 0:01:06])
def clean_text(text):
    return re.sub(r'\[.*?\]', '', text)

# Function to convert CSV timestamp (mm:ss) to seconds
def convert_timestamp_to_seconds(timestamp):
    try:
        minutes, seconds = map(int, timestamp.split(':'))
        return minutes * 60 + seconds
    except ValueError:
        return 0  # Default to 0 if timestamp is not in correct format

# Use Cloud9 instance IAM role for credentials and generate a pre-signed URL for S3 objects
def upload_file_to_s3_and_get_url(file_data, filename, folder):
    try:
        # Use Cloud9 instance role credentials directly
        s3_client = boto3.client('s3')
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=f"{folder}{filename}", Body=file_data)
        
        # Generate a pre-signed URL for public access (expires in 1 hour)
        url = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': S3_BUCKET_NAME, 'Key': f"{folder}{filename}"},
                                               ExpiresIn=3600)  # URL expires in 1 hour
        logging.info(f"Uploaded {filename} to S3 in folder {folder} and generated URL.")
        return url
    except NoCredentialsError as e:
        logging.error("IAM role or credentials not set correctly")
        raise e
    except ClientError as e:
        logging.error(f"Failed to upload file to S3: {e}")
        raise e

# Fetch the Azure API key and region from AWS Secrets Manager using Cloud9 instance role
def get_azure_secrets(secret_name="azure-secrets", region_name="ap-south-1"):
    try:
        # Use Cloud9 instance role credentials directly to fetch secret from Secrets Manager
        client = boto3.client(service_name="secretsmanager", region_name=region_name)

        # Get the secret value from AWS Secrets Manager
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response["SecretString"]

        # Parse and return the secret as a dictionary (API key and region)
        return eval(secret)

    except NoCredentialsError as e:
        logging.error("IAM role or credentials not set correctly")
        raise e
    except ClientError as e:
        logging.error(f"Failed to retrieve secret: {e}")
        raise e

# Function to retrieve supported voices from Azure Speech API
def get_supported_voices():
    azure_secrets = get_azure_secrets()
    AZURE_API_KEY = azure_secrets["AZURE_API_KEY"]
    AZURE_REGION = azure_secrets["AZURE_REGION"]
    
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_API_KEY,
    }
    response = requests.get(f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch Azure voices: {response.status_code} {response.text}")
        raise Exception("Unable to retrieve supported voices from Azure.")

# Function to generate SSML file for the selected language and upload to S3
def generate_ssml(df, lang_column, male_voice, female_voice, xml_lang):
    if lang_column not in df.columns:
        raise ValueError(f"Column '{lang_column}' not found in the CSV file.")

    ssml_filename = f"{uuid.uuid4()}.ssml"

    ssml_content = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{xml_lang}'>\n"
    last_timestamp = 0

    for index, row in df.iterrows():
        speaker = row.get('Speaker', 'spk_0')
        transcription = clean_text(row.get(lang_column, ''))
        if not transcription:
            continue

        timestamp_seconds = convert_timestamp_to_seconds(row.get('Time Markers', '0:00'))
        delay = max(0, timestamp_seconds - last_timestamp)
        last_timestamp = timestamp_seconds

        if delay > 0:
            ssml_content += f"<break time='{delay}s' />\n"

        voice = male_voice if speaker == 'spk_0' else female_voice
        ssml_content += f"<voice name='{voice}'>{transcription}</voice>\n"
    
    ssml_content += "</speak>"

    # Upload SSML content directly to S3 and return pre-signed URL
    ssml_s3_url = upload_file_to_s3_and_get_url(ssml_content.encode('utf-8'), ssml_filename, S3_SSML_FOLDER)

    return ssml_s3_url

# Function to convert SSML file to audio using Azure TTS API and upload to S3
async def convert_ssml_to_audio(ssml_s3_url):
    azure_secrets = get_azure_secrets()
    AZURE_API_KEY = azure_secrets["AZURE_API_KEY"]
    AZURE_REGION = azure_secrets["AZURE_REGION"]

    # Initialize S3 client to fetch SSML content
    s3_client = boto3.client('s3')
    ssml_data = requests.get(ssml_s3_url).text  # Fetch SSML content via the URL

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_API_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm"
    }

    response = requests.post(f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1", headers=headers, data=ssml_data)

    logging.info(f"Azure API Response Status: {response.status_code}")

    if response.status_code == 200:
        audio_filename = f"{uuid.uuid4()}.wav"
        # Upload audio content directly to S3 and return pre-signed URL
        audio_s3_url = upload_file_to_s3_and_get_url(response.content, audio_filename, S3_AUDIO_FOLDER)

        return audio_s3_url
    else:
        logging.error(f"Error from Azure API: {response.text}")
        raise Exception(f"Error from Azure API: {response.text}")

# Helper function to detect language
def detect_language(text):
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"

# Helper function to find the transcription column based on partial locale code
def find_transcription_column(df, locale_code):
    for column in df.columns:
        if locale_code in column and column.endswith('--Transcription'):
            return column
    return None

# Endpoint to handle file upload, locale selection, and SSML processing
@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...), source: str = Form(...)):
    try:
        source_cleaned = source.strip().replace("\\", "").replace("\n", "").replace("\t", "")

        # Read the CSV file
        contents = await file.read()
        try:
            df = pd.read_csv(pd.io.common.StringIO(contents.decode("utf-8")), encoding="utf-8")
        except UnicodeDecodeError:
            logging.error("File encoding is not supported. Please ensure the file is UTF-8 encoded.")
            return {"error": "File encoding is not supported. Please ensure the file is UTF-8 encoded."}

        # Ensure the DataFrame is not empty
        if df.empty:
            logging.error("The uploaded CSV is empty.")
            return {"error": "The uploaded CSV is empty."}

        # Upload the input CSV to S3
        input_filename = f"{uuid.uuid4()}.csv"
        upload_file_to_s3_and_get_url(contents, input_filename, S3_INPUT_FOLDER)

        # Retrieve the supported voices from Azure
        supported_voices = get_supported_voices()

        # Find the matching voices for the given locale
        source_voices = [v for v in supported_voices if source_cleaned == v['Locale']]
        if not source_voices:
            logging.error(f"Invalid locale input: {source_cleaned}")
            return {"error": "Invalid locale specified or locale not supported."}

        male_voice = next((v['ShortName'] for v in source_voices if "Male" in v['Gender']), None)
        female_voice = next((v['ShortName'] for v in source_voices if "Female" in v['Gender']), None)
        if not male_voice or not female_voice:
            logging.error(f"Male or female voice not found for {source_cleaned}")
            return {"error": f"Male or female voice not found for {source_cleaned}."}

        # Check for the transcription column
        locale_code = source_cleaned.split('-')[-1]
        transcription_column = find_transcription_column(df, locale_code)
        if transcription_column is None:
            logging.error(f"CSV is missing a column containing '{locale_code}--Transcription' for the specified language.")
            return {"error": f"CSV must contain a column with '{locale_code}--Transcription' for the specified language."}

        # Ensure the transcription column has data
        non_empty_rows = df[transcription_column].dropna()
        if non_empty_rows.empty:
            logging.error(f"The transcription column '{transcription_column}' is empty.")
            return {"error": f"The transcription column '{transcription_column}' is empty."}

        # Generate the audio files for both English and the selected language
        ssml_file_path_en = generate_ssml(df, 'EN--Transcription', 'en-US-GuyNeural', 'en-US-JennyNeural', 'en-US')
        audio_file_en_url = await convert_ssml_to_audio(ssml_file_path_en)

        ssml_file_path_source = generate_ssml(df, transcription_column, male_voice, female_voice, source_cleaned)
        audio_file_source_url = await convert_ssml_to_audio(ssml_file_path_source)

        # Return URLs for the generated audio files
        return {
            "message": "Audio files generated successfully",
            "english_audio_url": audio_file_en_url,  # This will be the S3 pre-signed URL
            "language_audio_url": audio_file_source_url  # This will be the S3 pre-signed URL
        }

    except ValueError as ve:
        logging.error(f"ValueError: {str(ve)}")
        return {"error": str(ve)}
    except IndexError as ie:
        logging.error(f"IndexError: {str(ie)}. Likely missing rows or data.")
        return {"error": "The CSV file might be missing some data. Please check the file content."}
    except Exception as e:
        logging.error(f"Error processing file. {str(e)}")
        return {"error": f"Error processing file. {str(e)}"}
