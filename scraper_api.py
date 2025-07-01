from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Inicializa la aplicación Flask
app = Flask(__name__)

@app.route('/scrape', methods=['GET'])
def scrape_website():
    """
    Endpoint que recibe una URL, extrae las entradas de un blog/noticias
    y devuelve los resultados en formato JSON.
    """
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

        # Aquí puedes personalizar el selector según el sitio que scrapearás
        entries = soup.find_all('article')
        scraped_data = []

        for entry in entries:
            title_element = entry.find(['h2', 'h3'])
            link_element = entry.find('a')

            if title_element and link_element and link_element.has_attr('href'):
                title = title_element.get_text(strip=True)
                link = urljoin(url_to_scrape, link_element['href'])

                scraped_data.append({
                    "title": title,
                    "link": link
                })

        return jsonify({"data": scraped_data})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Error al obtener la URL.", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Ocurrió un error inesperado.", "details": str(e)}), 500

# Esto permite ejecutar localmente
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
