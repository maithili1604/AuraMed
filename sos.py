import os
import subprocess
import requests
import speech_recognition as sr
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from twilio.rest import Client
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
from googletrans import Translator
import datetime
import time
import threading


sos_bp = Blueprint("sos", __name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load environment variables from .env file
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
HOSPITAL_PHONE_NUMBERS = ["+918582892588", "+919831455224"]  # Add multiple numbers here


# Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@sos_bp.route("/sos/upload", methods=["POST"])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Convert to proper WAV format
    wav_file_path = convert_to_wav(file_path)
    
    if wav_file_path is None or not os.path.exists(wav_file_path):
        return jsonify({"error": "Audio conversion failed"}), 500

    # Convert recorded audio to text
    emergency_message = transcribe_and_translate(wav_file_path)


    if not emergency_message:
        return jsonify({"error": "Failed to transcribe audio"}), 500

   # Use hardcoded coordinates
    latitude = 22.56263
    longitude = 88.36304

    
    if latitude and longitude:
        user_address = reverse_geocode(latitude, longitude)
        if user_address:
            emergency_message += f"Sent from Location: {user_address}"
    
    # Send SOS alert to multiple numbers
    send_sos_alert(emergency_message)

    return jsonify({
        "message": "SOS sent successfully!",
        "file": filename,
        "transcribed_message": emergency_message
    })



def convert_to_wav(audio_path):
    """ Converts an audio file to a proper PCM WAV format using FFmpeg """
    wav_path = audio_path.rsplit(".", 1)[0] + "_converted.wav"
    
    try:
        command = [
            "ffmpeg", "-y", "-i", audio_path,
            "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
            wav_path
        ]
        process = subprocess.run(command, capture_output=True, text=True)

        if process.returncode != 0:
            print(f"❌ FFmpeg Error: {process.stderr}")
            return None

        print(f"✅ Successfully converted to WAV: {wav_path}")
        return wav_path

    except Exception as e:
        print(f"🚨 Conversion error: {e}")
        return None
    


import whisper

def transcribe_and_translate(audio_path):
    """Transcribes speech from any language and translates it directly to English."""
    
    try:
        # Load the Whisper model (small or medium is recommended for good balance)
        model = whisper.load_model("medium")  

        # Transcribe and translate directly to English
        result = model.transcribe(audio_path, task="translate")

        translated_text = result["text"]
        print(f"🌍 Translated English Text: {translated_text}")
        return translated_text

    except Exception as e:
        print(f"🚨 Error: {e}")
        return None

def reverse_geocode(latitude, longitude):
    """ Get address from latitude and longitude using Google Maps API """
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{latitude},{longitude}",
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            return data["results"][0]["formatted_address"]
    
    return None

def send_sos_alert(emergency_message):
    """ Sends an emergency call and SMS with location details """
    for number in HOSPITAL_PHONE_NUMBERS:
        try:
            # Make a call
            call = twilio_client.calls.create(
                twiml=f'<Response><Say>{emergency_message}</Say></Response>',
                to=number,
                from_=TWILIO_PHONE_NUMBER
            )
            print(f"📞 SOS Call initiated to {number}: {call.sid}")

            # Send SMS
            message = twilio_client.messages.create(
                body=emergency_message,
                from_=TWILIO_PHONE_NUMBER,
                to=number
            )
            print(f"📩 SOS SMS sent to {number}: {message.sid}")

        except Exception as e:
            print(f"🚨 Twilio Error for {number}: {e}")




# MongoDB client
mongo_client = MongoClient("mongodb+srv://mahadiqbalaiml27:9Gx_qVZ-tpEaHUu@healthcaresystem.ilezc.mongodb.net/healthcaresystem?retryWrites=true&w=majority&appName=Healthcaresystem")
db = mongo_client["healthcaresystem"]
reminder_collection = db["medicine_reminders"]


# Update the schedule_reminder endpoint
@sos_bp.route("/schedule-reminder", methods=["POST"])
def schedule_reminder():
    try:
        data = request.json
        reminder = {
            "medicineName": data["medicineName"],
            "days": data["days"],  # List of days (e.g., ["Monday", "Wednesday", "Friday"])
            "times": data["times"],  # List of times (e.g., ["09:00", "14:00", "20:00"])
            "phone": data["phone"],
        }
        reminder_collection.insert_one(reminder)
        return jsonify({"message": "Reminder scheduled successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Modify the process_reminders function
def process_reminders():
    while True:
        try:
            # Get the current day and time
            current_day = datetime.datetime.now().strftime("%A")  # e.g., "Monday"
            current_time = datetime.datetime.now().strftime("%H:%M")  # e.g., "09:00"

            # Find reminders that match the current day and time
            reminders = reminder_collection.find({"days": current_day, "times": current_time})
            for reminder in reminders:
                message_body = f"Reminder: Take your medicine {reminder['medicineName']} now."
                try:
                    # Send SMS using Twilio
                    twilio_client.messages.create(
                        body=message_body,
                        from_=TWILIO_PHONE_NUMBER,
                        to=reminder["phone"],
                    )
                    print(f"SMS sent to {reminder['phone']} successfully.")
                except Exception as sms_error:
                    print(f"Failed to send SMS to {reminder['phone']}: {sms_error}")

            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error in process_reminders: {e}")



# Start the reminder thread
reminder_thread = threading.Thread(target=process_reminders, daemon=True)
reminder_thread.start()
