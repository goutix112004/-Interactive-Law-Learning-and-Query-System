import os
import speech_recognition as sr
import pandas as pd
import random
import PyPDF2
from gtts import gTTS
import pygame
import tempfile
from googletrans import Translator
import spacy
from sentence_transformers import SentenceTransformer, util

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

# Load spaCy + Sentence-BERT for NLP
nlp = spacy.load("en_core_web_sm")
embedder = SentenceTransformer("paraphrase-MiniLM-L6-v2")

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

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        filename = fp.name

    tts = gTTS(text=text, lang=lang)
    tts.save(filename)

    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass

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

CRIME_KEYWORDS = {
    "rape": {
        "synonyms": ["rape", "sexual assault", "molest", "forced sex", "harassed sexually", "gang rape"],
        "sections": ["IPC 375 - Rape", "IPC 376 - Punishment for rape"]
    },
    "murder": {
        "synonyms": ["murder", "kill", "homicide", "stabbed", "shot dead", "assassinate", "strangled"],
        "sections": ["IPC 302 - Punishment for murder"]
    },
    "theft": {
        "synonyms": ["theft", "stole", "snatched", "pickpocket", "stolen bike", "burglary"],
        "sections": ["IPC 378 - Theft", "IPC 379 - Punishment for theft"]
    },
    "robbery": {
        "synonyms": ["robbery", "robbed", "chain snatching", "armed theft", "looted"],
        "sections": ["IPC 390 - Robbery", "IPC 392 - Punishment for robbery"]
    },
    "kidnapping": {
        "synonyms": ["kidnap", "abduct", "taken away", "hostage", "child missing"],
        "sections": ["IPC 359 - Kidnapping", "IPC 363 - Punishment for kidnapping"]
    },
    "dowry_death": {
        "synonyms": ["dowry death", "bride burning", "harassed for dowry"],
        "sections": ["IPC 304B - Dowry death"]
    },
    "suicide": {
        "synonyms": ["suicide", "self harm", "took own life", "hung himself"],
        "sections": ["IPC 306 - Abetment of suicide"]
    },
    "attempt_suicide": {
        "synonyms": ["attempt suicide", "attempted suicide", "self harm", "failed suicide", "tried to hang self"],
        "sections": ["IPC 309 - Attempt to commit suicide"]
    },
    "attempt_murder": {
        "synonyms": ["attempt murder", "tried to kill", "stab attempt", "shooting attempt"],
        "sections": ["IPC 307 - Attempt to murder"]
    },
    "acid_attack": {
        "synonyms": ["acid attack", "threw acid", "acid violence"],
        "sections": ["IPC 326A - Acid attack", "IPC 326B - Attempted acid attack"]
    },
    "domestic_violence": {
        "synonyms": ["domestic violence", "beaten by husband", "wife abuse", "marital abuse"],
        "sections": ["IPC 498A - Cruelty by husband or relatives"]
    },
    "cheating": {
        "synonyms": ["cheating", "fraud", "tricked", "dishonest deal", "scam"],
        "sections": ["IPC 415 - Cheating", "IPC 420 - Cheating and dishonestly inducing delivery of property"]
    },
    "cheating_marriage": {
        "synonyms": ["cheated in marriage", "false promise of marriage", "marriage fraud"],
        "sections": ["IPC 493 - Cohabitation caused by deceitful marriage"]
    },
    "dacoity": {
        "synonyms": ["dacoity", "armed gang robbery", "group loot"],
        "sections": ["IPC 391 - Dacoity", "IPC 395 - Punishment for dacoity"]
    },
    "human_trafficking": {
        "synonyms": ["human trafficking", "sold woman", "sold child", "forced prostitution"],
        "sections": ["IPC 370 - Trafficking of persons"]
    },
    "child_labour": {
        "synonyms": ["child labour", "underage work", "forced child labour"],
        "sections": ["Child Labour Act", "IPC 374 - Unlawful compulsory labour"]
    },
    "sexual_harassment": {
        "synonyms": ["sexual harassment", "inappropriate touch", "eve teasing", "verbal abuse"],
        "sections": ["IPC 354A - Sexual harassment"]
    },
    "stalking": {
        "synonyms": ["stalking", "followed me", "kept chasing", "online stalking"],
        "sections": ["IPC 354D - Stalking"]
    },
    "voyeurism": {
        "synonyms": ["voyeurism", "took pictures secretly", "video without consent"],
        "sections": ["IPC 354C - Voyeurism"]
    },
    "terrorism": {
        "synonyms": ["terrorism", "terror attack", "bomb blast"],
        "sections": ["UAPA Act", "IPC 121 - Waging war against the state"]
    },
    "drug_possession": {
        "synonyms": ["drugs", "caught with drugs", "narcotics", "weed", "smuggling drugs"],
        "sections": ["NDPS Act - Narcotics offences"]
    },
    "drug_trafficking": {
        "synonyms": ["drug trafficking", "smuggling narcotics", "heroin supply"],
        "sections": ["NDPS Act Section 21", "NDPS Act Section 23"]
    },
    "smuggling": {
        "synonyms": ["smuggling", "illegal trade", "gold smuggling"],
        "sections": ["Customs Act", "IPC 135 - Smuggling related offences"]
    },
    "money_laundering": {
        "synonyms": ["money laundering", "hawala", "illegal cash", "black money"],
        "sections": ["PMLA Act - Prevention of Money Laundering"]
    },
    "cyber_crime": {
        "synonyms": ["cyber crime", "hacked", "online fraud", "phishing", "cyber bullying"],
        "sections": ["IT Act 66C - Identity theft", "IT Act 66D - Cheating by impersonation using computer"]
    },
    "identity_theft": {
        "synonyms": ["identity theft", "used my details", "fake Aadhaar", "fake PAN"],
        "sections": ["IT Act 66C - Identity theft"]
    },
    "credit_card_fraud": {
        "synonyms": ["credit card fraud", "debit card scam", "atm fraud"],
        "sections": ["IT Act 66D - Cheating by impersonation"]
    },
    "cyber_bullying": {
        "synonyms": ["cyber bullying", "online harassment", "trolled online"],
        "sections": ["IT Act provisions on cyber harassment"]
    },
    "phishing": {
        "synonyms": ["phishing", "fake email scam", "fake link fraud"],
        "sections": ["IT Act 66C/66D"]
    },
    "data_breach": {
        "synonyms": ["data breach", "hacked database", "stolen data"],
        "sections": ["IT Act 43 - Data theft"]
    },
    "arson": {
        "synonyms": ["arson", "set fire", "burned house", "burnt property"],
        "sections": ["IPC 435 - Mischief by fire", "IPC 436 - Mischief by fire with intent to destroy house"]
    },
    "assault": {
        "synonyms": ["assault", "attacked me", "beaten up", "hit", "slapped", "punch"],
        "sections": ["IPC 351 - Assault", "IPC 352 - Punishment for assault"]
    },
    "grievous_hurt": {
        "synonyms": ["grievous hurt", "serious injury", "fracture", "acid burn", "crippled"],
        "sections": ["IPC 320 - Grievous hurt", "IPC 325 - Punishment for voluntarily causing grievous hurt"]
    },
    "hurt": {
        "synonyms": ["hurt", "injured", "slight injury", "hurt by weapon"],
        "sections": ["IPC 319 - Hurt", "IPC 323 - Punishment for voluntarily causing hurt"]
    },
    "extortion": {
        "synonyms": ["extortion", "blackmail", "forced money", "threatened to pay"],
        "sections": ["IPC 383 - Extortion", "IPC 384 - Punishment for extortion"]
    },
    "criminal_intimidation": {
        "synonyms": ["criminal intimidation", "threatened", "life threat", "death threat"],
        "sections": ["IPC 503 - Criminal intimidation", "IPC 506 - Punishment for criminal intimidation"]
    },
    "trespass": {
        "synonyms": ["trespass", "entered illegally", "broke into property"],
        "sections": ["IPC 441 - Criminal trespass", "IPC 447 - Punishment for criminal trespass"]
    },
    "house_trespass": {
        "synonyms": ["house trespass", "entered house illegally", "broke into home", "unauthorized entry"],
        "sections": ["IPC 442 - House trespass", "IPC 448 - Punishment for house trespass"]
    },
    "lurking_house_trespass": {
        "synonyms": ["lurking trespass", "hidden entry", "entered secretly"],
        "sections": ["IPC 443 - Lurking house trespass", "IPC 456 - Punishment for lurking house trespass at night"]
    },
    "criminal_breach_trust": {
        "synonyms": ["breach of trust", "embezzlement", "misappropriation", "betrayal of trust"],
        "sections": ["IPC 405 - Criminal breach of trust", "IPC 406 - Punishment for criminal breach of trust"]
    },
    "cheque_bounce": {
        "synonyms": ["cheque bounce", "dishonoured cheque", "bounced payment"],
        "sections": ["NI Act Section 138 - Dishonour of cheque"]
    },
    "counterfeit": {
        "synonyms": ["counterfeit", "fake currency", "fake coin", "fake note"],
        "sections": ["IPC 489A - Counterfeiting currency notes or bank-notes"]
    },
    "obscenity": {
        "synonyms": ["obscene", "vulgar", "porn distribution", "indecent exposure"],
        "sections": ["IPC 292 - Sale of obscene books", "IPC 294 - Obscene acts in public"]
    },
    "obscene_act": {
        "synonyms": ["obscene act", "public indecency", "indecent behaviour"],
        "sections": ["IPC 294 - Obscene acts in public"]
    },
    "obscene_publication": {
        "synonyms": ["obscene book", "pornographic material", "vulgar publication"],
        "sections": ["IPC 292 - Sale of obscene books"]
    },
    "public_nuisance": {
        "synonyms": ["public nuisance", "blocking road", "causing disturbance", "disturbing peace"],
        "sections": ["IPC 268 - Public nuisance", "IPC 290 - Punishment for public nuisance"]
    },
    "unlawful_assembly": {
        "synonyms": ["unlawful assembly", "illegal gathering", "protest turned violent", "riot group"],
        "sections": ["IPC 141 - Unlawful assembly", "IPC 143 - Punishment for unlawful assembly"]
    },
    "rioting_with_weapon": {
        "synonyms": ["rioting with weapons", "mob with weapons", "violent protest", "armed riot"],
        "sections": ["IPC 146 - Rioting", "IPC 148 - Rioting armed with deadly weapon"]
    },
    "sedition": {
        "synonyms": ["sedition", "anti national speech", "inciting rebellion"],
        "sections": ["IPC 124A - Sedition"]
    },
    "waging_war": {
        "synonyms": ["waging war", "declared war against India", "armed rebellion"],
        "sections": ["IPC 121 - Waging war against Government of India"]
    },
    "dowry_harassment": {
        "synonyms": ["dowry harassment", "harassed for dowry", "forced dowry"],
        "sections": ["IPC 498A - Cruelty by husband or relatives of husband"]
    },
    "custodial_death": {
        "synonyms": ["custodial death", "killed in custody", "police torture"],
        "sections": ["IPC 302 - Murder", "Human Rights Act provisions"]
    },
    "negligence": {
        "synonyms": ["negligence", "careless", "medical negligence", "accident due to negligence"],
        "sections": ["IPC 304A - Causing death by negligence"]
    },
    "rash_driving": {
        "synonyms": ["rash driving", "overspeeding", "reckless driving", "dangerous driving"],
        "sections": ["IPC 279 - Rash driving or riding on a public way"]
    },
    "drunk_driving": {
        "synonyms": ["drunk driving", "drunk and drive", "alcohol driving"],
        "sections": ["Motor Vehicles Act Section 185 - Drunken driving"]
    },
    "hit_and_run": {
        "synonyms": ["hit and run", "ran away after accident"],
        "sections": ["IPC 304A - Causing death by negligence", "MV Act Section 134 - Duty of driver"]
    },
    "corruption": {
        "synonyms": ["corruption", "took bribe", "government corruption"],
        "sections": ["Prevention of Corruption Act, 1988"]
    },
    "tax_evasion": {
        "synonyms": ["tax evasion", "did not pay tax", "black money hiding"],
        "sections": ["Income Tax Act Section 276C - Tax evation"]
    },
    "environmental_pollution": {
        "synonyms": ["pollution", "toxic waste", "industrial waste dumped"],
        "sections": ["Environment Protection Act Section 15"]
    },
    "illegal_logging": {
        "synonyms": ["illegal logging", "cut trees", "deforestation"],
        "sections": ["Forest Act provisions"]
    },
    "wildlife_poaching": {
        "synonyms": ["wildlife poaching", "hunting", "killed tiger", "animal poaching"],
        "sections": ["Wildlife Protection Act Section 51"]
    },
    "smuggling_arms": {
        "synonyms": ["arms smuggling", "illegal guns", "weapon trafficking"],
        "sections": ["Arms Act Section 25 - Possession of illegal arms"]
    },
    "illegal_mining": {
        "synonyms": ["illegal mining", "sand mining", "mining without permit"],
        "sections": ["Mines and Minerals Act Section 21"]
    },
    "food_adulteration": {
        "synonyms": ["food adulteration", "fake milk", "spurious food"],
        "sections": ["IPC 272 - Adulteration of food", "FSSAI Act provisions"]
    },
    "espionage": {
        "synonyms": ["espionage", "spying", "passed secrets", "leaked defense info"],
        "sections": ["Official Secrets Act", "IPC 121"]
    },
    "passport_fraud": {
        "synonyms": ["passport fraud", "fake passport", "forged travel document"],
        "sections": ["Passport Act", "IPC 465 Forgery"]
    },
    "immigration_violation": {
        "synonyms": ["immigration violation", "illegal immigrant", "visa overstay"],
        "sections": ["Foreigners Act provisions"]
    },
    "blasphemy": {
        "synonyms": ["blasphemy", "insulted religion", "hurt religious sentiments"],
        "sections": ["IPC 295A - Outraging religious feelings"]
    },
    "public_drunkenness": {
        "synonyms": ["public drunkenness", "drunk in public", "caused scene drunk"],
        "sections": ["IPC 268 - Public nuisance", "Excise Act provisions"]
    },
    "gambling": {
        "synonyms": ["gambling", "betting", "illegal lottery"],
        "sections": ["Public Gambling Act Section 12"]
    },
    "defamation": {
        "synonyms": ["defamation", "false allegations", "slander", "libel", "maligned reputation"],
        "sections": ["IPC 499 - Defamation", "IPC 500 - Punishment"]
    },
    "forgery": {
        "synonyms": ["forgery", "fake signature", "false document", "fake certificate"],
        "sections": ["IPC 463 - Forgery", "IPC 465 - Punishment for forgery"]
    },
    "bribery": {
        "synonyms": ["bribery", "gave bribe", "took bribe", "corruption"],
        "sections": ["Prevention of Corruption Act", "IPC 171E - Bribery"]
    },
    "riot": {
        "synonyms": ["riot", "mob violence", "communal clash"],
        "sections": ["IPC 147 - Punishment for rioting"]
    },
    "unlawful_restraint": {
        "synonyms": ["unlawful restraint", "held against will", "stopped movement"],
        "sections": ["IPC 339 - Wrongful restraint"]
    },
    "wrongful_confinement": {
        "synonyms": ["wrongful confinement", "locked up", "held captive"],
        "sections": ["IPC 340 - Wrongful confinement"]
    },
    "disobedience_order": {
        "synonyms": ["disobedience", "ignored order", "violated order of authority"],
        "sections": ["IPC 188 - Disobedience to order by public servant"]
    },
    "adultery": {
        "synonyms": ["adultery", "extramarital affair", "illicit relationship"],
        "sections": ["IPC 497 - Adultery (struck down by SC, but historically present)"]
    },
    "affray": {
        "synonyms": ["public fight", "affray", "street fight", "riot in public"],
        "sections": ["IPC 159 - Affray", "IPC 160 - Punishment for affray"]
    },
    "mischief_by_fire": {
        "synonyms": ["fire damage", "burnt property", "mischief by fire"],
        "sections": ["IPC 435 - Mischief by fire"]
    }
}

# Search laws
def search_laws(query, constitution_text, index_text, ipc_text):
    found = []
    q_lower = query.lower()

    # Constitution + Index + IPC search
    for line in constitution_text.split("\n"):
        if q_lower in line.lower():
            found.append("Constitution: " + line.strip())
    for line in index_text.split("\n"):
        if q_lower in line.lower():
            found.append("Index: " + line.strip())
    for line in ipc_text.split("\n"):
        if q_lower in line.lower():
            found.append("IPC: " + line.strip())

    # Keyword + Synonym matching
    for crime, data in CRIME_KEYWORDS.items():
        for synonym in data["synonyms"]:
            if synonym in q_lower:
                found.extend(data["sections"])
                break

    # Named Entity Recognition
    doc = nlp(query)
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "ORG", "MONEY", "DATE", "GPE"]:
            found.append(f"Context Entity Detected: {ent.text} ({ent.label_})")

    # Semantic Similarity
    crime_descriptions = []
    crime_mapping = []
    for crime, data in CRIME_KEYWORDS.items():
        for synonym in data["synonyms"]:
            crime_descriptions.append(synonym)
            crime_mapping.append(data["sections"])

    query_embedding = embedder.encode(query, convert_to_tensor=True)
    desc_embeddings = embedder.encode(crime_descriptions, convert_to_tensor=True)

    cos_scores = util.cos_sim(query_embedding, desc_embeddings)[0]
    best_match_idx = int(cos_scores.argmax())
    best_score = float(cos_scores[best_match_idx])

    if best_score > 0.6:
        found.extend(crime_mapping[best_match_idx])

    return found if found else ["No direct law/article/section found."]

# Case Outcome Simulation
def simulate_case(prosecution, defense, constitution_text, index_text, ipc_text):
    prosecution_laws = search_laws(prosecution, constitution_text, index_text, ipc_text)
    defense_laws = search_laws(defense, constitution_text, index_text, ipc_text)

    prosecution_win = random.randint(40, 80)
    defense_win = 100 - prosecution_win

    prosecution_laws_text = "\n".join(prosecution_laws[:5])
    defense_laws_text = "\n".join(defense_laws[:5])

    outcome = f"""
Case Simulation Result:

Prosecution Evidence: {prosecution}
Relevant Laws/Sections Found:
- {prosecution_laws_text}

Defense Evidence: {defense}
Relevant Laws/Sections Found:
- {defense_laws_text}

Possible Ruling:
- If prosecution proves case → Win chance: {prosecution_win}%
- If defense proves case → Win chance: {defense_win}%
""".strip()
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

    # Ask user which language
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
