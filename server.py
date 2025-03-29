from flask import Flask, request, jsonify, render_template
from rag import RAGSystem  # assume you moved your class into rag.py
import threading
from data_extractor import extract_user_data  # We'll create this function

app = Flask(__name__, static_folder='templates', static_url_path='/')

# Initialize your RAG system
######################################################################################################
FIREBASE_CRED_PATH = 'C:\\Users\\ASUS\\Desktop\\BRAINwave\\templates\\brainwave-de13c-firebase-adminsdk-fbsvc-344cfc4d95.json'
GEMINI_API_KEY = 'AIzaSyA66cf5Bh0mRJwBAOCTOBiu0Xrsc59nxjs'
#######################################################################################################

rag_system = RAGSystem(FIREBASE_CRED_PATH, GEMINI_API_KEY)

# Endpoint to serve the HTML page
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to handle queries
@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    user_query = data.get('query')
    if not user_query:
        return jsonify({'error': 'Missing query'}), 400

    # Run your RAG system query
    response_text = rag_system.query(user_query)
    return jsonify({'response': response_text})

# NEW ENDPOINT: Handle data extraction after sign-in
@app.route('/extract-data', methods=['POST'])
def extract_data():
    data = request.get_json()
    user_id = data.get('uid')
    user_email = data.get('email')
    
    if not user_id or not user_email:
        return jsonify({'error': 'Missing user information'}), 400
    
    # Run the data extraction in a background thread so it doesn't block the response
    def run_extraction():
        try:
            extract_user_data(user_id, user_email)
        except Exception as e:
            print(f"Error in data extraction: {e}")
    
    thread = threading.Thread(target=run_extraction)
    thread.daemon = True  # This ensures the thread will exit when the main program exits
    thread.start()
    
    return jsonify({'status': 'Data extraction started', 'user': user_id})

if __name__ == '__main__':
    app.run(debug=True)