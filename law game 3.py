import os
import speech_recognition as sr
import pandas as pd
import random
import PyPDF2
from gtts import gTTS
import pygame
import tempfile
from googletrans import Translator

# Fixed path for Indian Penal Code PDF
IPC_PDF_PATH = r"C:\Users\91810\OneDrive\Desktop\law based llm\indina penal code.pdf"

# Translator
translator = Translator()

# Language mapping
LANGUAGE_CODES = {
    "english": ("en-IN", "en"),
    "hindi": ("hi-IN", "hi"),
    "telugu": ("te-IN", "te"),
    "tamil": ("ta-IN", "ta"),
    "kannada": ("kn-IN", "kn"),
    "malayalam": ("ml-IN", "ml")
}

# Default language
current_recognition_lang = "en-IN"
current_tts_lang = "en"

# Detect Constitution CSV + Index CSV files
def find_files():
    folder = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(folder)
    constitution_file = None
    index_file = None
    
    for f in files:
        if "constitution" in f.lower() and f.lower().endswith(".csv"):
            constitution_file = os.path.join(folder, f)
        if "index" in f.lower() and f.lower().endswith(".csv"):
            index_file = os.path.join(folder, f)
    
    if not constitution_file or not index_file:
        raise FileNotFoundError("Could not find Constitution or Index CSV files.")
    
    return constitution_file, index_file, None

# Load Constitution & Index CSV
def load_csv_files(constitution_path, index_path):
    encodings = ["utf-8", "cp1252"]
    for enc in encodings:
        try:
            constitution_df = pd.read_csv(constitution_path, encoding=enc)
            index_df = pd.read_csv(index_path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("Could not read CSV files. Unsupported encoding.")

    constitution_text = "\n".join(constitution_df.iloc[:, 0].astype(str).tolist())
    index_text = "\n".join(index_df.iloc[:, 0].astype(str).tolist())

    return constitution_text, index_text

# Load IPC PDF
def load_ipc_pdf(ipc_pdf_path):
    ipc_text = ""
    with open(ipc_pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            if page.extract_text():
                ipc_text += page.extract_text() + "\n"
    return ipc_text

# Text to Speech using gTTS + pygame (safe temp file handling)
def speak(text, lang=None):
    global current_tts_lang
    if not lang:
        lang = current_tts_lang

    # Create unique temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        filename = fp.name

    # Generate speech
    tts = gTTS(text=text, lang=lang)
    tts.save(filename)

    # Play speech
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass

    # Cleanup temp file
    try:
        os.remove(filename)
    except PermissionError:
        pass

# Speech to Text
def listen(language=None):
    global current_recognition_lang
    if not language:
        language = current_recognition_lang

    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print(f"Listening in {language}... Speak now:")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language=language)
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return ""
    except sr.RequestError:
        print("API error")
        return ""

# Crime keywords → IPC section mapping
CRIME_KEYWORDS = {
    "rape": ["IPC Section 375 - Rape", "IPC Section 376 - Punishment for rape"],
    "murder": ["IPC Section 302 - Punishment for murder"],
    "theft": ["IPC Section 378 - Theft", "IPC Section 379 - Punishment for theft"],
    "robbery": ["IPC Section 390 - Robbery", "IPC Section 392 - Punishment for robbery"],
    "kidnapping": ["IPC Section 359 - Kidnapping", "IPC Section 363 - Punishment for kidnapping"],
    "cheating": ["IPC Section 415 - Cheating", "IPC Section 420 - Cheating and dishonestly inducing delivery of property"],
    "dacoity": ["IPC Section 391 - Dacoity", "IPC Section 395 - Punishment for dacoity"],
    "dowry": ["IPC Section 304B - Dowry death"],
    "suicide": ["IPC Section 306 - Abetment of suicide"]
}

# Search laws
def search_laws(query, constitution_text, index_text, ipc_text):
    found = []
    q_lower = query.lower()

    for line in constitution_text.split("\n"):
        if q_lower in line.lower():
            found.append("Constitution: " + line.strip())
    for line in index_text.split("\n"):
        if q_lower in line.lower():
            found.append("Index: " + line.strip())
    for line in ipc_text.split("\n"):
        if q_lower in line.lower():
            found.append("IPC: " + line.strip())

    for keyword, sections in CRIME_KEYWORDS.items():
        if keyword in q_lower:
            found.extend(sections)

    return found if found else ["No direct law/article/section found."]

# Case Outcome Simulation
def simulate_case(prosecution, defense, constitution_text, index_text, ipc_text):
    prosecution_laws = search_laws(prosecution, constitution_text, index_text, ipc_text)
    defense_laws = search_laws(defense, constitution_text, index_text, ipc_text)

    prosecution_win = random.randint(40, 80)
    defense_win = 100 - prosecution_win

    outcome = f"""
    Case Simulation Result:

    Prosecution Evidence: {prosecution}
    Relevant Laws/Sections Found:
    - {chr(10).join(prosecution_laws[:5])}

    Defense Evidence: {defense}
    Relevant Laws/Sections Found:
    - {chr(10).join(defense_laws[:5])}

    Possible Ruling:
    - If prosecution proves case → Win chance: {prosecution_win}%
    - If defense proves case → Win chance: {defense_win}%
    """
    return outcome

# ----------------- MAIN PROGRAM -----------------
if __name__ == "__main__":
    constitution_path, index_path, _ = find_files()
    print(f"Found Constitution CSV: {constitution_path}")
    print(f"Found Index CSV: {index_path}")

    constitution_text, index_text = load_csv_files(constitution_path, index_path)

    print(f"Loading IPC PDF from: {IPC_PDF_PATH}")
    ipc_text = load_ipc_pdf(IPC_PDF_PATH)
    print("IPC PDF loaded successfully.")

    # Ask user which language to use
    speak("Which language do you want to use? Hindi, Telugu, Tamil, Kannada, Malayalam, or English.", lang="en")
    chosen_lang = listen(language="en-IN").lower()

    if chosen_lang in LANGUAGE_CODES:
        current_recognition_lang, current_tts_lang = LANGUAGE_CODES[chosen_lang]
        print(f"Language set to {chosen_lang.capitalize()} ({current_recognition_lang}, {current_tts_lang})")
        speak(f"You have chosen {chosen_lang}", lang=current_tts_lang)
    else:
        print("Language not recognized. Defaulting to English.")
        current_recognition_lang, current_tts_lang = LANGUAGE_CODES["english"]

    # Prosecution input
    speak("Please speak Prosecution's Argument or Evidence", lang=current_tts_lang)
    prosecution_input = listen()

    # Defense input
    speak("Please speak Defense's Argument or Evidence", lang=current_tts_lang)
    defense_input = listen()

    result = simulate_case(prosecution_input, defense_input, constitution_text, index_text, ipc_text)
    print(result)
    speak(result, lang=current_tts_lang)
