from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
import mysql.connector 
from datetime import datetime, timedelta
import threading
import time
from scraper import scrape_articles  
from ranker import Ranker

# Database Configuration
DB_HOST = "localhost" 
DB_USER = "root"
DB_PASSWORD = "2812"
DB_NAME = "document_retrieval"

# Initialize Flask App
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False  # Keep JSON responses in the order we add keys

# Global Variables for Rate Limiting
RATE_LIMIT_WINDOW = timedelta(minutes=1)  # Time window for rate limiting
RATE_LIMIT_MAX_REQUESTS = 5  # Max requests allowed in the time window

# Initialize the Ranker (Load your TF-IDF model here)
ranker = Ranker()

# Function to get a database connection
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Function to check if a user is rate limited
def is_rate_limited(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT request_count, last_request_time FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data: 
            request_count, last_request_time = user_data
            if datetime.now() - last_request_time < RATE_LIMIT_WINDOW and request_count >= RATE_LIMIT_MAX_REQUESTS:
                return True  # User is rate limited
            else:
                cursor.execute("UPDATE users SET request_count = request_count + 1, last_request_time = %s WHERE user_id = %s", (datetime.now(), user_id))
        else:
            cursor.execute("INSERT INTO users (user_id, request_count, last_request_time) VALUES (%s, 1, %s)", (user_id, datetime.now()))
        conn.commit()
        return False  # User is not rate limited
    except Exception as e:
        conn.rollback() 
        app.logger.error(f"Database error during rate limiting: {e}")
        return True  # Assume rate limited on error
    finally:
        cursor.close()
        conn.close()

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "OK"})

# Search endpoint
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

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Retrieve potentially relevant documents
        cursor.execute(
            "SELECT id, content FROM documents WHERE MATCH(content) AGAINST (%s IN NATURAL LANGUAGE MODE)", 
            (query,)
        )
        retrieved_docs = cursor.fetchall()

        # Rank documents using TF-IDF
        results = ranker.rank_documents(query, retrieved_docs, top_k) 

        end_time = time.time()
        inference_time = end_time - start_time

        app.logger.info(f"Search query: {query}, Inference time: {inference_time:.4f} seconds")

        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Search error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Start the Flask web server
    app.run(debug=True)  

    # Start the scraping thread in the background
    scraping_thread = threading.Thread(target=scrape_articles)
    scraping_thread.daemon = True  # Allow the main thread to exit even if scraping is running
    scraping_thread.start()