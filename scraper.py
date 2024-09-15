import requests
import time
from bs4 import BeautifulSoup
#from app import get_db_connection 

NEWS_WEBSITES = [ {"url": "https://www.nbcnews.com", "selector": ".wide-tease__link"},
                 {"url": "https://www.indianexpress.com/news", "selector": "h2.title a"} ]


def scrape_articles():
    from app import get_db_connection 
    print("Entering scrape_articles() function")
    while True:
        print("Starting scraping cycle")
        for website in NEWS_WEBSITES:
            url = website['url']
            article_selector = website['selector']
            print(f"Scraping: {url}") 

            try:
                print("  - Sending request...")
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                print("  - Response received.")
                response.raise_for_status()  

                soup = BeautifulSoup(response.content, 'html.parser')
                article_elements = soup.select(article_selector)  
                print(f"  - Found {len(article_elements)} article elements.")

                for article_element in article_elements:
                    try:
                        article_url = article_element['href']
                        if not article_url.startswith('http'):
                            article_url = url + article_url  # Construct full URL if relative
                        print(f"    - Found article: {article_url}")

                        article_response = requests.get(article_url)
                        article_response.raise_for_status() 

                        article_soup = BeautifulSoup(article_response.content, 'html.parser')

                        title = article_soup.find('h1').text.strip() 
                        content_elements = article_soup.select('article p')
                        content = "\n".join([p.text.strip() for p in content_elements])

                        conn = get_db_connection()
                        if conn is None:
                            print("      - Database connection error. Skipping article.")
                            continue  # Skip to the next article

                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO documents (url, content) VALUES (%s, %s)",
                            (article_url, content)
                        )
                        conn.commit()
                        print(f"        - Inserted article: {article_url}")

                    except KeyError as e:
                        print(f"    - Error extracting article URL: {e}")
                    except requests.exceptions.RequestException as e:
                        print(f"    - Error fetching article: {e}")
                    except mysql.connector.errors.IntegrityError:
                        print(f"        - Duplicate article skipped: {article_url}")
                    except Exception as db_error:
                        print(f"        - Database error: {db_error}")
                    finally:
                        if conn:
                            cursor.close()
                            conn.close()

            except requests.exceptions.RequestException as e:
                print(f"  - Scraping error: {e}")

        print("Sleeping for 1 hour...")
        time.sleep(3600) 


if __name__ == "__main__":
    scrape_articles()