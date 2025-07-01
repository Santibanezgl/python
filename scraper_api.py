# -----------------------------------------------------------------------------
# |                      API de Web Scraping con Flask                        |
# |---------------------------------------------------------------------------|
# |                                                                           |
# |  Instrucciones:                                                           |
# |  1. Instala las librerías necesarias:                                     |
# |     pip install Flask requests beautifulsoup4                             |
# |  2. Guarda este código como 'scraper_api.py'.                             |
# |  3. Ejecútalo desde tu terminal:                                          |
# |     python scraper_api.py                                                 |
# |  4. El servidor estará corriendo en http://127.0.0.1:5000                 |
# |  5. Para probar, abre en tu navegador o usa curl:                         |
# |     http://127.0.0.1:5000/scrape?url=URL_DEL_SITIO_A_SCRAPEAR              |
# |                                                                           |
# -----------------------------------------------------------------------------

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
    # Obtiene el parámetro 'url' de la petición. Ej: /scrape?url=https://unblog.com
    url_to_scrape = request.args.get('url')

    if not url_to_scrape:
        # Si no se proporciona una URL, devuelve un error 400 (Bad Request)
        return jsonify({"error": "El parámetro 'url' es obligatorio."}), 400

    try:
        # Es una buena práctica definir un User-Agent para que el servidor
        # no piense que eres un bot malicioso.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Realiza la petición GET para obtener el contenido HTML de la página
        response = requests.get(url_to_scrape, headers=headers, timeout=10)
        # Lanza una excepción si la petición no fue exitosa (ej. error 404, 500)
        response.raise_for_status()

        # Analiza (parsea) el contenido HTML con BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- ¡AQUÍ ESTÁ LA PARTE MÁS IMPORTANTE QUE DEBES PERSONALIZAR! ---
        #
        # Debes inspeccionar el HTML del sitio que quieres scrapear para encontrar
        # los selectores correctos para las "entradas" o artículos.
        #
        # Ejemplo: Si cada entrada está dentro de una etiqueta <article class="post-item">,
        # usarías: soup.find_all('article', class_='post-item')
        #
        # Este ejemplo genérico busca etiquetas <article>.
        
        entries = soup.find_all('article')
        scraped_data = []

        if not entries:
            # Si no se encontraron etiquetas <article>, puedes probar con otro selector común
            # Por ejemplo, <div class="post"> o <div class="entry-content">
            # entries = soup.find_all('div', class_='post')
            pass # Dejamos esto como un recordatorio para personalizar

        for entry in entries:
            # Dentro de cada entrada, busca el título y el enlace.
            # De nuevo, DEBES PERSONALIZAR estos selectores.
            
            # Intenta encontrar el título en una etiqueta <h2> o <h3> dentro de la entrada
            title_element = entry.find(['h2', 'h3'])
            # Busca el primer enlace <a> dentro de la entrada
            link_element = entry.find('a')

            if title_element and link_element and link_element.has_attr('href'):
                # Extrae el texto del título, limpiando espacios en blanco
                title = title_element.get_text(strip=True)
                
                # Obtiene el enlace (href) y lo convierte en un enlace absoluto
                # si es relativo (ej. /noticias/mi-noticia)
                link = urljoin(url_to_scrape, link_element['href'])

                # Opcional: Extraer un resumen o descripción
                # summary_element = entry.find('p', class_='summary')
                # summary = summary_element.get_text(strip=True) if summary_element else 'No summary found'

                scraped_data.append({
                    "title": title,
                    "link": link,
                    # "summary": summary # Descomenta si extraes un resumen
                })
        
        # Devuelve los datos scrapeados como una respuesta JSON
        return jsonify({"data": scraped_data})

    except requests.exceptions.RequestException as e:
        # Captura errores de red (ej. no se puede conectar, timeout)
        return jsonify({"error": "Error al obtener la URL.", "details": str(e)}), 500
    except Exception as e:
        # Captura cualquier otro error durante el proceso
        return jsonify({"error": "Ocurrió un error inesperado.", "details": str(e)}), 500

# Permite ejecutar el script directamente
if __name__ == '__main__':
