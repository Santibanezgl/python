from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        
        # Configurar reintentos automáticos
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers más realistas
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def clean_soup(self, soup):
        """Limpia el HTML de elementos innecesarios de forma más agresiva"""
        
        # Elementos a eliminar completamente
        unwanted_tags = [
            'style', 'script', 'noscript', 'iframe', 'embed', 'object',
            'svg', 'canvas', 'audio', 'video', 'source', 'track',
            'meta', 'link', 'base', 'head', 'title'
        ]
        
        for tag_name in unwanted_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Eliminar comentarios HTML
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Eliminar atributos innecesarios que pueden contener CSS/JS
        unwanted_attrs = [
            'style', 'class', 'id', 'onclick', 'onload', 'onmouseover', 
            'onmouseout', 'onfocus', 'onblur', 'data-*'
        ]
        
        for tag in soup.find_all():
            # Mantener solo atributos esenciales
            attrs_to_keep = {}
            if tag.name == 'a' and tag.get('href'):
                attrs_to_keep['href'] = tag['href']
            if tag.name == 'img' and tag.get('src'):
                attrs_to_keep['src'] = tag['src']
                if tag.get('alt'):
                    attrs_to_keep['alt'] = tag['alt']
            
            tag.attrs = attrs_to_keep
        
        return soup
    
    def extract_text_content(self, element):
        """Extrae texto limpio de un elemento"""
        if not element:
            return ""
        
        # Obtener texto y limpiar espacios
        text = element.get_text(separator=' ', strip=True)
        # Eliminar espacios múltiples y caracteres especiales
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-.,;:!?áéíóúüñÁÉÍÓÚÜÑ]', '', text)
        return text.strip()
    
    def is_valid_url(self, url):
        """Valida si una URL es válida"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def is_meaningful_title(self, title):
        """Verifica si el título tiene contenido significativo"""
        if not title or len(title.strip()) < 3:
            return False
        
        # Filtrar títulos que son solo espacios, números o caracteres especiales
        if re.match(r'^[\s\d\W]*$', title):
            return False
        
        # Filtrar títulos demasiado genéricos
        generic_titles = [
            'leer más', 'ver más', 'continuar', 'siguiente', 'anterior',
            'inicio', 'home', 'menú', 'menu', 'buscar', 'search'
        ]
        
        if title.lower().strip() in generic_titles:
            return False
        
        return True
    
    def get_best_title(self, entry):
        """Obtiene el mejor título de un elemento"""
        title_candidates = []
        
        # Buscar en diferentes elementos por orden de prioridad
        for selector in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            elements = entry.find_all(selector)
            for elem in elements:
                text = self.extract_text_content(elem)
                if self.is_meaningful_title(text):
                    title_candidates.append((text, len(text)))
        
        # Si no hay títulos en headers, buscar en enlaces
        if not title_candidates:
            links = entry.find_all('a', href=True)
            for link in links:
                text = self.extract_text_content(link)
                if self.is_meaningful_title(text):
                    title_candidates.append((text, len(text)))
        
        # Si aún no hay títulos, buscar en elementos con texto
        if not title_candidates:
            for tag in ['span', 'div', 'p']:
                elements = entry.find_all(tag)
                for elem in elements:
                    text = self.extract_text_content(elem)
                    if self.is_meaningful_title(text) and len(text) < 200:
                        title_candidates.append((text, len(text)))
        
        # Retornar el título más apropiado (ni muy corto ni muy largo)
        if title_candidates:
            # Ordenar por longitud y tomar uno de longitud media
            title_candidates.sort(key=lambda x: x[1])
            mid_index = len(title_candidates) // 2
            return title_candidates[mid_index][0]
        
        return None
    
    def scrape_website(self, url):
        """Método principal de scraping"""
        try:
            # Realizar petición
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # Parsear HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Limpiar el HTML
            soup = self.clean_soup(soup)
            
            scraped_data = []
            
            # Selectores candidatos más específicos y ordenados por prioridad
            candidate_selectors = [
                'article',
                'div[class*="post"]',
                'div[class*="article"]',
                'div[class*="news"]',
                'div[class*="item"]',
                'div[class*="card"]',
                'div[class*="entry"]',
                'section[class*="article"]',
                'section[class*="post"]',
                'li[class*="post"]',
                'li[class*="article"]',
                'li[class*="item"]',
                '.post', '.article', '.news-item', '.blog-post',
                '.content-item', '.story', '.entry'
            ]
            
            entries = []
            
            # Buscar entradas usando los selectores
            for selector in candidate_selectors:
                try:
                    found = soup.select(selector)
                    if found:
                        entries.extend(found)
                        if len(entries) > 50:  # Limitar para evitar demasiados elementos
                            break
                except:
                    continue
            
            # Si no se encontraron entradas específicas, buscar en contenedor principal
            if not entries:
                main_containers = soup.select('main, #main, #content, .content, .main, .container')
                for container in main_containers:
                    links = container.find_all('a', href=True)
                    for link in links[:30]:  # Limitar a 30 enlaces
                        title = self.extract_text_content(link)
                        if self.is_meaningful_title(title):
                            full_url = urljoin(url, link['href']).strip()
                            if self.is_valid_url(full_url):
                                # Limpiar URL de parámetros innecesarios
                                full_url = full_url.split('#')[0]
                                scraped_data.append({
                                    "title": title,
                                    "link": full_url
                                })
            else:
                # Procesar entradas encontradas
                for entry in entries:
                    title = self.get_best_title(entry)
                    
                    if title:
                        # Buscar enlace en la entrada
                        link_element = entry.find('a', href=True)
                        
                        if link_element:
                            link = urljoin(url, link_element['href']).strip()
                            link = link.split('#')[0]  # Eliminar anclas
                            
                            if self.is_valid_url(link):
                                scraped_data.append({
                                    "title": title,
                                    "link": link
                                })
            
            # Eliminar duplicados y filtrar
            unique_data = []
            seen = set()
            
            for item in scraped_data:
                # Crear clave única basada en título y dominio del enlace
                domain = urlparse(item['link']).netloc
                key = (item['title'].lower().strip(), domain)
                
                if key not in seen and len(item['title']) > 5:
                    unique_data.append(item)
                    seen.add(key)
            
            # Ordenar por longitud de título (títulos más descriptivos primero)
            unique_data.sort(key=lambda x: len(x['title']), reverse=True)
            
            # Limitar resultados para evitar respuestas demasiado grandes
            return unique_data[:50]
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout: La página tardó demasiado en responder")
        except requests.exceptions.ConnectionError:
            raise Exception("Error de conexión: No se pudo conectar con la página")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Error HTTP: {e.response.status_code}")
        except Exception as e:
            raise Exception(f"Error inesperado: {str(e)}")

# Instancia global del scraper
scraper = WebScraper()

@app.route('/scrape', methods=['GET'])
def scrape_website():
    """Endpoint principal para el scraping"""
    url_to_scrape = request.args.get('url')
    
    if not url_to_scrape:
        return jsonify({"error": "El parámetro 'url' es obligatorio."}), 400
    
    # Validar URL
    if not scraper.is_valid_url(url_to_scrape):
        return jsonify({"error": "La URL proporcionada no es válida."}), 400
    
    try:
        # Realizar scraping
        start_time = time.time()
        data = scraper.scrape_website(url_to_scrape)
        end_time = time.time()
        
        return jsonify({
            "success": True,
            "data": data,
            "total_items": len(data),
            "processing_time": round(end_time - start_time, 2),
            "url": url_to_scrape
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Error al procesar la página",
            "details": str(e),
            "url": url_to_scrape
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud del servicio"""
    return jsonify({"status": "healthy", "service": "web-scraper"})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
