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

# Flask App
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global Variables for Rate Limiting
RATE_LIMIT_WINDOW = timedelta(minutes=1)
RATE_LIMIT_MAX_REQUESTS = 5

# Initialize the Ranker 
ranker = Ranker()

# Database Connection Function
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
        # Handle the error appropriately (e.g., retry, exit) 
        return None

# Rate Limiting Function
def is_rate_limited(user_id):
    conn = get_db_connection()
    if conn is None:  # Check if connection failed
        return True  # Assume rate limited on error

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

# Health Check Endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "OK"})

# Search Endpoint
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
    app.run(debug=True) 

    scraping_thread = threading.Thread(target=scrape_articles)
    scraping_thread.daemon = True 
    scraping_thread.start()