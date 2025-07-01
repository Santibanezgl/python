from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
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
        scraped_data = []

        # Posibles selectores que suelen contener posts o noticias
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
            # Agrega más si quieres
        ]

        # Intentamos recolectar entradas de cualquiera de estos selectores
        entries = []
        for sel in candidate_selectors:
            found = soup.select(sel)
            if found:
                entries.extend(found)

        # Si no encontró con esos selectores, por si acaso, intenta con todos los enlaces dentro de un contenedor principal
        if not entries:
            # Busca el contenedor principal, por ejemplo div#main o div.content
            main_container = soup.select_one('main, #main, #content, .content')
            if main_container:
                entries = main_container.find_all('a', href=True)

                # En este caso vamos a extraer títulos de texto de los enlaces
                for a in entries:
                    title = a.get_text(strip=True)
                    if title:
                        link = urljoin(url_to_scrape, a['href'])
                        scraped_data.append({"title": title, "link": link})

        else:
            # Recorremos las entradas encontradas para extraer título y link
            for entry in entries:
                # Buscamos títulos en encabezados h1-h4
                title_element = None
                for tag in ['h1', 'h2', 'h3', 'h4']:
                    title_element = entry.find(tag)
                    if title_element:
                        break
                
                # Si no hay título en encabezado, probamos algún texto en enlaces
                if not title_element:
                    title_element = entry.find('a')

                # Buscamos link en el primer <a> con href
                link_element = entry.find('a', href=True)

                if title_element and link_element:
                    title = title_element.get_text(strip=True)
                    link = urljoin(url_to_scrape, link_element['href'])
                    if title and link:
                        scraped_data.append({"title": title, "link": link})

        # Quitar duplicados (por si acaso)
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
