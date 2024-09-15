import json
import os
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
import mysql.connector
from sentence_transformers import SentenceTransformer, util
from scraper import scrape_articles
from ranker import Ranker

# Database configuration details
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "2812"
DB_NAME = "document_retrieval"

# Initialize Flask application
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Rate limiting settings
RATE_LIMIT_WINDOW = timedelta(minutes=1)
RATE_LIMIT_MAX_REQUESTS = 5

# Initialize the Ranker
ranker = Ranker()

# Load the BERT model for sentence embeddings
bert_model = SentenceTransformer('bert-base-uncased')  

# Caching configuration
CACHE_FILE = "search_cache.json"
CACHE_EXPIRY = 3600 

def load_cache():
    try:
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        return cache_data
    except FileNotFoundError:
        return {}  

def save_cache(cache_data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=4)

cache = load_cache() 

# Function to establish a database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        app.logger.error(f"Database connection error: {err}")
        return None

# Function to check if a user is rate limited
def is_rate_limited(user_id):
    conn = get_db_connection()
    if conn is None: 
        return True 

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT request_count, last_request_time FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            request_count, last_request_time = user_data
            if datetime.now() - last_request_time < RATE_LIMIT_WINDOW and request_count >= RATE_LIMIT_MAX_REQUESTS:
                return True 
            else:
                cursor.execute(
                    "UPDATE users SET request_count = request_count + 1, last_request_time = %s WHERE user_id = %s",
                    (datetime.now(), user_id)
                )
        else:
            cursor.execute(
                "INSERT INTO users (user_id, request_count, last_request_time) VALUES (%s, 1, %s)",
                (user_id, datetime.now())
            )
        conn.commit()
        return False 
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Database error during rate limiting: {e}")
        return True 
    finally:
        cursor.close()
        conn.close()

# Endpoint to check the health of the service
@app.route('/health')
def health_check():
    return jsonify({"status": "OK"})

# Search endpoint with caching and BERT re-ranking
@app.route('/search')
def search():
    start_time = time.time()
    user_id = request.headers.get('user_id')
    if not user_id:
        return jsonify({"error": "Missing user_id header"}), 400

    if is_rate_limited(user_id):
        return jsonify({"error": "Rate limit exceeded"}), 429 

    query = request.args.get('text')
    top_k = int(request.args.get('top_k', 10))
    threshold = float(request.args.get('threshold', 0.5))

    if not query:
        return jsonify({"error": "Missing 'text' parameter in query string"}), 400

    # Check cache first
    cache_key = f"{query}_{top_k}_{threshold}"
    if cache_key in cache and (time.time() - cache[cache_key]['timestamp'] < CACHE_EXPIRY):
        print("Cache hit!")
        results = cache[cache_key]['results']
    else:
        print("Cache miss.")
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection error"}), 500

        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, content FROM documents WHERE MATCH(content) AGAINST (%s IN NATURAL LANGUAGE MODE)", 
                (query,)
            )
            retrieved_docs = cursor.fetchall()

            results = []
            # Re-rank documents using BERT
            query_embedding = bert_model.encode(query, convert_to_tensor=True)
            document_embeddings = bert_model.encode([doc[1] for doc in retrieved_docs], convert_to_tensor=True)
            cosine_scores = util.cos_sim(query_embedding, document_embeddings)[0]

            # Combine BERT scores with TF-IDF scores
            for i, doc in enumerate(retrieved_docs):
                doc_id, doc_content = doc
                tfidf_score = ranker.rank_documents(query, [(doc_id, doc_content)], top_k=1)[0]['score']
                combined_score = (tfidf_score + cosine_scores[i].item()) / 2 
                results.append({"document_id": doc_id, "score": combined_score})

            results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_k] 

            # Save results to cache
            cache[cache_key] = {'results': results, 'timestamp': time.time()}
            save_cache(cache) 

        except Exception as e:
            app.logger.error(f"Search error: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
        finally:
            cursor.close()
            conn.close()

    end_time = time.time()
    inference_time = end_time - start_time
    app.logger.info(f"Search query: {query}, Inference time: {inference_time:.4f} seconds")

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True) 

    scraping_thread = threading.Thread(target=scrape_articles)
    scraping_thread.daemon = True
    scraping_thread.start()