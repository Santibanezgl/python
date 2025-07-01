from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin
import re

app = Flask(__name__)

@app.route('/scrape', methods=['GET'])
def scrape_website():
    url_to_scrape = request.args.get('url')

    if not url_to_scrape:
        return jsonify({"error": "El parámetro 'url' es obligatorio."}), 400

    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            )
        }

        response = requests.get(url_to_scrape, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Limpiar estilos, scripts, noscript y comentarios para evitar CSS y JS
        for tag in soup(['style', 'script', 'noscript']):
            tag.decompose()

        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for c in comments:
            c.extract()

        scraped_data = []

        candidate_selectors = [
            'article',
            'div.post',
            'div.post-item',
            'div.article',
            'div.blog-post',
            'li.post',
            'li.article',
            'div.news-item',
            'div.item',
            'section.article',
            'section.post',
        ]

        entries = []
        for sel in candidate_selectors:
            found = soup.select(sel)
            if found:
                entries.extend(found)

        if not entries:
            main_container = soup.select_one('main, #main, #content, .content')
            if main_container:
                links = main_container.find_all('a', href=True)
                for a in links:
                    title = a.get_text(separator=' ', strip=True)
                    title = re.sub(r'\s+', ' ', title)
                    if title:
                        link = urljoin(url_to_scrape, a['href']).strip()
                        scraped_data.append({"title": title, "link": link})

        else:
            for entry in entries:
                title_element = None
                for tag in ['h1', 'h2', 'h3', 'h4']:
                    title_element = entry.find(tag)
                    if title_element:
                        break

                if not title_element:
                    title_element = entry.find('a')

                link_element = entry.find('a', href=True)

                if title_element and link_element:
                    title = title_element.get_text(separator=' ', strip=True)
                    title = re.sub(r'\s+', ' ', title)

                    link = urljoin(url_to_scrape, link_element['href']).strip()
                    link = link.split('#')[0]  # eliminar anclas
                    # link = link.split('?')[0]  # si quieres eliminar query params también

                    if title and link:
                        scraped_data.append({"title": title, "link": link})

        # Eliminar duplicados
        unique = []
        seen = set()
        for item in scraped_data:
            key = (item['title'], item['link'])
            if key not in seen:
                unique.append(item)
                seen.add(key)

        return jsonify({"data": unique})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Error al obtener la URL.", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Ocurrió un error inesperado.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
