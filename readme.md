# Document Retrieval System

## Overview
This project is a backend system for document retrieval, designed to provide context for chat applications using large language models (LLMs). The system scrapes news articles, stores them in a database, and allows for efficient retrieval and ranking of documents based on user queries.

## Features
- **Health Check Endpoint**: `/health` to check if the API is active.
- **Search Endpoint**: `/search` to retrieve and rank documents based on a query.
- **Rate Limiting**: Limits users to 5 requests per minute.
- **Caching**: Caches search results to improve performance.
- **Background Scraping**: Continuously scrapes news articles in the background.
- **Dockerized**: The application is containerized using Docker.

## Requirements
- Python 3.12
- Flask
- BeautifulSoup
- Requests
- MySQL Connector
- Sentence Transformers
- Scikit-learn
- Docker

## Setup

### Database
Ensure you have a MySQL database set up with the following configuration:
- Host: `localhost`
- User: `root`
- Password: `2812`
- Database: `document_retrieval`

Create the necessary table:
```sql
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url TEXT NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    request_count INT DEFAULT 0,
    last_request_time DATETIME
);
```
## Endpoints

### Health Check
- **URL**: `/health`
- **Method**: GET
- **Description**: Returns a status message to check if the API is active.

### Search
- **URL**: `/search`
- **Method**: GET
- **Parameters**:
  - `text`: The query text.
  - `top_k`: Number of top results to fetch (default: 10).
  - `threshold`: Similarity score threshold (default: 0.5).
  - `user_id`: Unique identifier for the user.
- **Description**: Returns a list of top results for the query.

## Code Structure

### app.py
Handles the main application logic, including the Flask server, endpoints, and rate limiting.

### scraper.py
Contains the logic for scraping news articles from CNN Lite and storing them in the database.

### ranker.py
Implements the `Ranker` class, which uses TF-IDF and cosine similarity to rank documents based on a query.

## Logging and Error Handling
The application logs important events and errors to the console. This includes database connection issues, scraping errors, and search errors. Proper error handling ensures that the application can recover gracefully from unexpected issues.

## Conclusion
This document retrieval system provides a robust backend for fetching and ranking documents, with features like rate limiting, caching, and background scraping. The use of Docker ensures that the application can be easily deployed and scaled.
