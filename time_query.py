import json
import spacy
from datetime import datetime

# Load spaCy's English NLP model
nlp = spacy.load("en_core_web_sm")

# Load doctor data
def load_doctors_data():
    file_path = "D:\\Ayan\\Skin_disease_prediction\\healthcaresystem.doctors.json"
    with open(file_path, 'r') as file:
        return json.load(file)

doctors_data = load_doctors_data()

# Extract keywords from query
def extract_keywords(query):
    doc = nlp(query.lower())
    keywords = {token.lemma_ for token in doc if token.pos_ in ["NOUN", "PROPN", "ADJ"]}
    return keywords

# Format availability data
def format_availability(availability):
    formatted_slots = []
    for date, slots in availability.items():
        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")  # Convert to readable format
        
        if isinstance(slots, list):  # Handles list format (e.g., ["08:00"])
            for time in slots:
                formatted_slots.append(f"- {formatted_date} at {time} (1 slot available)")
        elif isinstance(slots, dict):  # Handles dictionary format with slots count
            for time, count in slots.items():
                if count > 0:
                    formatted_slots.append(f"- {formatted_date} at {time} ({count} slots available)")
    
    return formatted_slots if formatted_slots else ["No available slots listed."]

# Search for doctor availability
def search_doctor_availability(query):
    keywords = extract_keywords(query)
    if not keywords:
        return "I couldn't understand the query. Please ask about a doctor's availability."

    for doctor in doctors_data:
        doctor_name = doctor.get("name", "").lower()
        availability = doctor.get("availability", {})

        if any(keyword in doctor_name for keyword in keywords):
            formatted_slots = format_availability(availability)
            return f"Dr. {doctor['name']} is available during the following time slots:\n" + "\n".join(formatted_slots)
    
    return "No availability information found for the requested doctor."

# Function to handle user queries
def get_doctor_availability():
    while True:
        query = input("Ask about a doctor's availability (or type 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        response = search_doctor_availability(query)
        print(response)

if __name__ == '__main__':
    get_doctor_availability()
