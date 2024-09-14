import requests
from bs4 import BeautifulSoup
from app import get_db_connection  

# List of news websites to scrape
NEWS_WEBSITES = [
    "https://www.example-news-site-1.com",
    "https://www.another-news-site-2.com/news"
]

def scrape_articles():
    while True:
        for url in NEWS_WEBSITES:
            try:
                # Fetch the webpage
                response = requests.get(url)
                response.raise_for_status()  # Raise an error if the request was unsuccessful

                # Parse the webpage content
                soup = BeautifulSoup(response.content, 'html.parser')
                articles = soup.find_all('article')  # Find all article elements (adjust as needed)

                # Connect to the database
                conn = get_db_connection() 
                cursor = conn.cursor()

                for article in articles:
                    # Extract the title and content from the article
                    # Adjust these lines based on the actual structure of the website
                    title = article.find('h2').text.strip()
                    content = article.find('p').text.strip() 

                    # Insert the article into the database
                    try:
                        cursor.execute(
                            "INSERT INTO documents (url, content) VALUES (%s, %s)",
                            (article_url, content)  # Make sure article_url is defined
                        )
                        conn.commit()
                    except mysql.connector.errors.IntegrityError:  
                        # If there's a duplicate entry, just skip it
                        conn.rollback()
                        pass

            except requests.exceptions.RequestException as e:
                # Print an error message if the request fails
                print(f"Scraping error: {e}")
            finally:
                # Close the database connection
                cursor.close()
                conn.close()
        
        # Wait for an hour before scraping again
        time.sleep(3600)