import os
import google.generativeai as genai
from firebase_admin import firestore, initialize_app, credentials, get_app

class RAGSystem:
    def __init__(self, firebase_cred_path, gemini_api_key):
        """
        Initialize Firebase and Gemini connections
        
        Args:
            firebase_cred_path (str): Path to Firebase credentials JSON
            gemini_api_key (str): Gemini API key
        """
        # Initialize Firebase (with check if already initialized)
        try:
            # Try to get the default app - if it exists, we'll use it
            app = get_app()
            print("Using existing Firebase app")
        except ValueError:
            # If it doesn't exist, initialize a new one
            cred = credentials.Certificate(firebase_cred_path)
            initialize_app(cred)
            print("Initialized new Firebase app")
            
        self.firestore_client = firestore.client()
        
        # Configure Gemini with error handling
        try:
            genai.configure(api_key=gemini_api_key)
            
            # Preferred models in order
            preferred_models = [
                'gemini-1.5-flash',  # Latest recommended model
                'gemini-pro',
                'models/gemini-1.0-pro'
            ]
            
            # Find the first available model
            available_model = None
            for model_name in preferred_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Verify the model can generate content
                    model.generate_content("Test")
                    available_model = model
                    print(f"Using model: {model_name}")
                    break
                except Exception as model_error:
                    print(f"Could not use model {model_name}: {model_error}")
            
            if not available_model:
                raise ValueError("No suitable Gemini model found")
            
            self.gemini_model = available_model
        
        except Exception as e:
            print(f"Gemini API Configuration Error: {e}")
            self.gemini_model = None

    def search_firebase(self, collection_name, query, top_k=5):
        """
        Search Firebase collection for relevant documents based on text similarity
        
        Args:
            collection_name (str): Firebase collection to search
            query (str): Search query
            top_k (int): Number of top results to return
        
        Returns:
            list: Top matching documents
        """
        # Retrieve all documents from the collection
        docs = self.firestore_client.collection(collection_name).stream()
        
        # Basic text-based relevance scoring
        results = []
        for doc in docs:
            doc_data = doc.to_dict()
            
            # Check different text fields
            text_fields = ['text', 'title', 'query', 'url', 'search_query']
            doc_text = ' '.join([str(doc_data.get(field, '')) for field in text_fields])
            
            # Simple relevance scoring (you can replace with more advanced techniques)
            relevance_score = self._calculate_relevance(query, doc_text)
            
            results.append({
                'data': doc_data,
                'relevance': relevance_score
            })
        
        # Sort by relevance and return top K
        return sorted(results, key=lambda x: x['relevance'], reverse=True)[:top_k]

    def _calculate_relevance(self, query, document_text):
        """
        Calculate basic text relevance using word overlap
        
        Args:
            query (str): Search query
            document_text (str): Document text to compare
        
        Returns:
            float: Relevance score
        """
        query_words = set(query.lower().split())
        doc_words = set(document_text.lower().split())
        
        overlap = len(query_words.intersection(doc_words))
        return overlap / (len(query_words) + 1)  # Prevent division by zero

    def construct_prompt(self, query, context_docs):
        """
        Construct a prompt for Gemini using retrieved context
        
        Args:
            query (str): Original user query
            context_docs (list): Relevant documents from Firebase
        
        Returns:
            str: Augmented prompt
        """
        # If no context documents are found, provide a generic response
        if not context_docs:
            return f"No specific context found for the query: {query}. Provide a general response."
        
        context_str = "\n\n".join([
            f"Context Document {i+1}: {doc['data']}"
            for i, doc in enumerate(context_docs)
        ])
        
        augmented_prompt = f"""
        You are an AI assistant providing context-aware responses.

        User Query: {query}

        Retrieved Context Documents:
        {context_str}

        Based on the context documents and the user query, provide a comprehensive and accurate response.
        If the context is insufficient, provide a general informative response.
        """
        
        return augmented_prompt

    def query(self, query, collection_name='browsing_history'):
        """
        Main method to perform RAG query
        
        Args:
            query (str): User's search query
            collection_name (str): Firebase collection to search
        
        Returns:
            str: AI-generated response with context
        """
        # Check if Gemini model is configured
        if not self.gemini_model:
            return "Gemini API is not properly configured. Please check your API key and settings."
        
        # Step 1: Retrieve relevant documents
        context_docs = self.search_firebase(collection_name, query)
        
        # Step 2: Construct augmented prompt
        augmented_prompt = self.construct_prompt(query, context_docs)
        
        # Step 3: Generate response using Gemini
        try:
            response = self.gemini_model.generate_content(augmented_prompt)
            return response.text
        except Exception as e:
            return f"Error generating response: {str(e)}"
# # Example Usage
# def main():
#     # Replace with your actual paths and API keys
#     FIREBASE_CRED_PATH = 'C:\\Users\\ASUS\\Desktop\\BRAINwave\\templates\\brainwave-de13c-firebase-adminsdk-fbsvc-344cfc4d95.json'
#     GEMINI_API_KEY = 'AIzaSyDaVubXN0ku7Au-3GZRAp2yU3R41s5Wj7M'
    
#     rag_system = RAGSystem(FIREBASE_CRED_PATH, GEMINI_API_KEY)
    
#     # Example queries
#     while True:
#         a=int(input("?"))
#         if a==1:
#             query=input("yout prompt: ")
#         elif a==0:
#             break
        

#     print(f"\nQuery: {query}")
#     response = rag_system.query(query)
#     print("Response:", response)

# if __name__ == "__main__":
#     main()