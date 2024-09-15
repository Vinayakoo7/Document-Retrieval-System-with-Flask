import requests
import time
from bs4 import BeautifulSoup

def scrape_articles():
    from app import get_db_connection  # Ensure you have a proper app setup for DB connection
    url = "https://lite.cnn.com"
    print(f"Scraping CNN Lite: {url}")

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Debugging: print the fetched HTML to find the correct tags
        # Uncomment the following line to inspect the HTML structure
        # print(soup.prettify())

        # Correct selector based on the provided HTML structure
        article_links = soup.select('li.card--lite a')

        print(f"  - Found {len(article_links)} article links.")

        # Open database connection once for the whole scraping session
        conn = get_db_connection()
        if conn is None:
            print("Database connection error. Exiting.")
            return

        cursor = conn.cursor()

        for link in article_links:
            try:
                # Construct the absolute URL for the article
                article_url = link['href'] if link['href'].startswith('http') else url + link['href']
                print(f"    - Fetching article: {article_url}")

                article_response = requests.get(article_url, headers={'User-Agent': 'Mozilla/5.0'})
                article_response.raise_for_status()

                article_soup = BeautifulSoup(article_response.content, 'html.parser')

                # Improved error handling for missing elements
                title_tag = article_soup.find('h1')
                if title_tag:
                    title = title_tag.text.strip()
                else:
                    title = "No title found"

                content_paragraphs = article_soup.select('section.article__content p')
                if content_paragraphs:
                    content = "\n".join([p.text.strip() for p in content_paragraphs])
                else:
                    content = "No content found"

                cursor.execute(
                    "INSERT INTO documents (url, content) VALUES (%s, %s)",
                    (article_url, content)
                )
                conn.commit()
                print(f"        - Inserted article: {article_url}")

            except KeyError:
                print(f"      - Error: 'href' attribute not found in link: {link}")
            except requests.exceptions.RequestException as e:
                print(f"      - Error fetching article: {e}")
            except Exception as db_error:
                conn.rollback()
                print(f"        - Database error: {db_error}")

        # Close the cursor and connection once after processing all articles
        cursor.close()
        conn.close()

    except requests.exceptions.RequestException as e:
        print(f"  - Error fetching CNN Lite homepage: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    while True:
        scrape_articles()
        print("Sleeping for 1 hour...")
        time.sleep(3600)
