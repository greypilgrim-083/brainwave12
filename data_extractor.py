import os
import json
import sqlite3
from datetime import datetime
import google_auth_oauthlib.flow

# Gmail API libraries
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# NLP libraries (using scikit-learn as an example)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# =====================
# CONFIGURATION SETUP
# =====================

# Gmail API SCOPES
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]
GMAIL_CREDENTIALS_FILE = 'C:\\Users\\ASUS\\Desktop\\BRAINwave\\templates\\brainwave-de13c-firebase-adminsdk-fbsvc-344cfc4d95.json'

# Firebase Admin initialization
FIREBASE_CRED_PATH = 'C:\\Users\\ASUS\\Desktop\\BRAINwave\\templates\\brainwave-de13c-firebase-adminsdk-fbsvc-344cfc4d95.json'

# Initialize Firebase if not already initialized
try:
    db = firestore.client()
except:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

# =====================
# FUNCTIONS FOR DATA RETRIEVAL
# =====================

def get_gmail_data(user_email=None):
    """Retrieve Gmail messages using Gmail API."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    token_file = f'token_{user_email.replace("@", "_at_").replace(".", "_dot_")}.json' if user_email else 'token.json'
    
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)
    if not creds or not creds.valid:
        # For fixed port 8080:
        flow = InstalledAppFlow.from_client_secrets_file(
            GMAIL_CREDENTIALS_FILE,
            GMAIL_SCOPES,
            redirect_uri='http://localhost:8080/'  # Explicitly match registered URI
        )
        # Use the correct method name
        creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])
    data = []
    for msg in messages:
        msg_id = msg['id']
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        # Extract snippet or body text as needed.
        snippet = message.get('snippet')
        data.append(snippet)
    return data

def get_browsing_history():
    # Import necessary modules
    import os
    import sqlite3
    import shutil
    import re
    from pathlib import Path
    from datetime import datetime, timedelta
    from urllib.parse import urlparse, parse_qs
    
    # Path to Chrome's History database (varies by OS)
    chrome_history_path = Path(os.path.expanduser('~')) / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / 'Profile 1' / 'History'
    
    # Check if the file exists
    if not chrome_history_path.exists():
        # Try default profile
        chrome_history_path = Path(os.path.expanduser('~')) / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'History'
        if not chrome_history_path.exists():
            return [{"error": "Chrome history file not found"}]
    
    # Create a temporary copy of the database
    temp_history_path = 'temp_history_db'
    
    try:
        shutil.copy2(chrome_history_path, temp_history_path)
    except Exception as e:
        return [{"error": f"Could not copy history file: {str(e)}"}]
    
    try:
        # Connect to the database
        conn = sqlite3.connect(temp_history_path)
        cursor = conn.cursor()
        
        # Get all browsing history
        cursor.execute("""
            SELECT url, title, visit_count, last_visit_time 
            FROM urls 
            ORDER BY last_visit_time DESC 
            LIMIT 10000
        """)
        history_data = cursor.fetchall()
        
        # Format the data, filtering for search queries
        search_history = []
        for url, title, visit_count, timestamp in history_data:
            # Convert timestamp
            chrome_epoch = datetime(1601, 1, 1)
            visit_time = chrome_epoch + timedelta(microseconds=timestamp)
            visit_time_str = visit_time.strftime('%Y-%m-%d %H:%M:%S')
            
            search_query = None
            search_engine = None
            
            # Extract Google searches
            if 'google.com/search' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'q' in query_params:
                    search_query = query_params['q'][0]
                    search_engine = 'Google'
            
            # Extract Bing searches
            elif 'bing.com/search' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'q' in query_params:
                    search_query = query_params['q'][0]
                    search_engine = 'Bing'
            
            # Extract DuckDuckGo searches
            elif 'duckduckgo.com' in url and '?q=' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'q' in query_params:
                    search_query = query_params['q'][0]
                    search_engine = 'DuckDuckGo'
            
            # Extract Yahoo searches
            elif 'search.yahoo.com/search' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'p' in query_params:
                    search_query = query_params['p'][0]
                    search_engine = 'Yahoo'
            
            # YouTube searches
            elif 'youtube.com/results' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'search_query' in query_params:
                    search_query = query_params['search_query'][0]
                    search_engine = 'YouTube'
            
            # Amazon searches
            elif 'amazon.com/s' in url:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if 'k' in query_params:
                    search_query = query_params['k'][0]
                    search_engine = 'Amazon'
            
            # Direct URL navigation (typing in address bar)
            elif re.match(r'^https?://[^/]+/?$', url):
                domain = urlparse(url).netloc
                search_query = f"[Direct visit to {domain}]"
                search_engine = "Direct Navigation"
            
            # If we found a search query, add it to our results
            if search_query:
                search_history.append({
                    'query': search_query,
                    'engine': search_engine,
                    'url': url,
                    'title': title or 'No Title',
                    'timestamp': visit_time_str
                })
        
        return search_history
        
    except Exception as e:
        return [{"error": f"Error accessing browsing history: {str(e)}"}]
    finally:
        # Clean up
        if 'conn' in locals() and conn:
            conn.close()
        if os.path.exists(temp_history_path):
            try:
                os.remove(temp_history_path)
            except:
                pass

# =====================
# NLP CLASSIFIER SETUP
# =====================

def train_dummy_classifier(texts, labels):
    """
    Trains a simple classifier. In practice, replace this with your actual model.
    texts: list of text samples
    labels: list of corresponding labels
    """
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(texts)
    clf = LogisticRegression()
    clf.fit(X, labels)
    return vectorizer, clf

def classify_text(text, vectorizer, clf):
    """Classify a single text using the trained classifier."""
    X = vectorizer.transform([text])
    prediction = clf.predict(X)
    return prediction[0]

# For demonstration, we create a dummy classifier
# In a real scenario, you would train this with your dataset
dummy_texts = ["important message", "casual update", "meeting schedule", "social media post"]
dummy_labels = ["work", "personal", "work", "social"]
vectorizer, clf = train_dummy_classifier(dummy_texts, dummy_labels)

# =====================
# FIREBASE STORAGE FUNCTIONS
# =====================

def store_in_firebase(collection_name, data_list, user_id=None):
    """
    Stores each item in data_list in the specified Firebase Firestore collection.
    Each document will have a 'text' field and a 'classified' field.
    """
    if not data_list:
        print(f"No data to store in {collection_name}")
        return
        
    # If user_id is provided, use a user-specific collection
    if user_id:
        collection_name = f"users/{user_id}/{collection_name}"
    
    for idx, item in enumerate(data_list):
        # Check if the item is a dictionary (like browsing history data)
        if isinstance(item, dict):
            # Extract text from the dictionary - use title or URL
            text_to_classify = item.get('title', '') or item.get('url', '') or item.get('query', '')
            # Store the whole item
            doc_data = item.copy()
        else:
            # For text items like Gmail or other sources
            text_to_classify = item
            doc_data = {'text': item}
            
        # Classify the text content
        try:
            classification = classify_text(text_to_classify, vectorizer, clf)
            doc_data['classified'] = classification
        except:
            doc_data['classified'] = 'unknown'
        
        # Add timestamp
        doc_data['timestamp'] = datetime.utcnow()
        
        # Store in Firebase
        doc_ref = db.collection(collection_name).document(f'doc_{idx}_{int(datetime.utcnow().timestamp())}')
        doc_ref.set(doc_data)
        print(f"Stored document in {collection_name}: {doc_data}")

# =====================
# MAIN FUNCTION FOR WEB SERVER
# =====================

def extract_user_data(user_id, user_email=None):
    """Function to extract data for a specific user after sign-in"""
    print(f"Starting data extraction for user: {user_id}, email: {user_email}")
    
    try:
        # Store user info in Firebase
        user_ref = db.collection('users').document(user_id)
        user_ref.set({
            'email': user_email,
            'last_extraction': datetime.utcnow()
        }, merge=True)
        
        # Try to get Gmail data if email is provided
        gmail_data = []
        if user_email:
            try:
                gmail_data = get_gmail_data(user_email)
                print(f"Retrieved {len(gmail_data)} Gmail messages")
            except Exception as e:
                print(f"Error getting Gmail data: {e}")
                # Store the error in Firebase
                error_ref = db.collection(f'users/{user_id}/errors').document('gmail_error')
                error_ref.set({
                    'error': str(e),
                    'timestamp': datetime.utcnow()
                })
        
        # Try to get browsing history
        try:
            browsing_history_data = get_browsing_history()
            print(f"Retrieved {len(browsing_history_data)} browsing history items")
        except Exception as e:
            print(f"Error getting browsing history: {e}")
            browsing_history_data = []
            # Store the error in Firebase
            error_ref = db.collection(f'users/{user_id}/errors').document('browsing_error')
            error_ref.set({
                'error': str(e),
                'timestamp': datetime.utcnow()
            })
        
        # Store the data in Firebase with user ID
        if gmail_data:
            store_in_firebase('gmail_data', gmail_data, user_id)
        if browsing_history_data:
            store_in_firebase('browsing_history', browsing_history_data, user_id)
            
        # Update user record with completion status
        user_ref.update({
            'last_extraction_complete': datetime.utcnow(),
            'extraction_status': 'complete'
        })
            
        print(f"Data extraction completed for user: {user_id}")
        return True
        
    except Exception as e:
        print(f"Error in data extraction process: {e}")
        # Store the error in Firebase
        error_ref = db.collection(f'users/{user_id}/errors').document('general_error')
        error_ref.set({
            'error': str(e),
            'timestamp': datetime.utcnow()
        })
        return False

# For command-line testing
if __name__ == "__main__":
    # Test with a dummy user ID
    extract_user_data('test_user_123', 'test@example.com')