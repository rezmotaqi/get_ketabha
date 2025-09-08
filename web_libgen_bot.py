#!/usr/bin/env python3
"""
Simple web interface for LibGen search
Alternative to Telegram bot when API is not accessible
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from libgen_search import LibGenSearcher
from utils.book_formatter import BookFormatter
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json

class LibGenWebHandler(BaseHTTPRequestHandler):
    """Web request handler for LibGen search"""
    
    def __init__(self, *args, **kwargs):
        self.searcher = LibGenSearcher()
        self.formatter = BookFormatter()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_homepage()
        elif parsed_path.path == '/search':
            query_params = parse_qs(parsed_path.query)
            query = query_params.get('q', [''])[0]
            if query:
                self.perform_search(query)
            else:
                self.serve_homepage("Please enter a search query")
        else:
            self.send_error(404)
    
    def serve_homepage(self, message=""):
        """Serve the main search page"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LibGen Search Bot - Web Interface</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; text-align: center; }}
                .search-box {{ margin: 20px 0; }}
                input[type="text"] {{ width: 70%; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; }}
                button {{ padding: 12px 20px; font-size: 16px; background-color: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }}
                button:hover {{ background-color: #2980b9; }}
                .message {{ color: #e74c3c; margin: 10px 0; }}
                .status {{ color: #27ae60; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>LibGen Search Bot</h1>
                <div class="status">LibGen Search Engine: WORKING</div>
                <p>Search for books from LibGen mirrors. Enter book title, author name, or ISBN.</p>
                
                {f'<div class="message">{message}</div>' if message else ''}
                
                <form action="/search" method="get" class="search-box">
                    <input type="text" name="q" placeholder="Enter book title, author, or ISBN..." required>
                    <button type="submit">Search</button>
                </form>
                
                <h3>Example searches:</h3>
                <ul>
                    <li><a href="/search?q=Python%20programming">Python programming</a></li>
                    <li><a href="/search?q=Clean%20Code%20Robert%20Martin">Clean Code Robert Martin</a></li>
                    <li><a href="/search?q=1984%20George%20Orwell">1984 George Orwell</a></li>
                </ul>
                
                <p><strong>Note:</strong> This web interface provides the same LibGen search functionality as the Telegram bot.</p>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def perform_search(self, query):
        """Perform LibGen search and return results"""
        try:
            # Run async search in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self.searcher.search(query))
            
            # Get download links for each book
            if results:
                print(f"Found {len(results)} books, fetching download links...")
                for book in results[:5]:  # Limit to first 5 books for performance
                    md5_hash = book.get('md5')
                    if md5_hash:
                        try:
                            download_links = loop.run_until_complete(self.searcher.get_download_links(md5_hash))
                            book['download_links'] = download_links
                            print(f"Found {len(download_links)} download links for {book.get('title', 'Unknown')}")
                        except Exception as e:
                            print(f"Error getting download links for {book.get('title', 'Unknown')}: {e}")
                            book['download_links'] = []
                    else:
                        book['download_links'] = []
            
            loop.close()
            
            if not results:
                self.serve_search_results(query, [], "No results found")
                return
            
            self.serve_search_results(query, results[:10])  # Limit to 10 results
            
        except Exception as e:
            self.serve_search_results(query, [], f"Search error: {str(e)}")
    
    def serve_search_results(self, query, results, error_message=""):
        """Serve search results page"""
        results_html = ""
        
        if error_message:
            results_html = f'<div class="message">{error_message}</div>'
        elif results:
            results_html = f'<h2>Found {len(results)} results for: "{query}"</h2>'
            for i, book in enumerate(results, 1):
                # Build download links HTML
                download_links_html = ""
                download_links = book.get('download_links', [])
                
                if download_links:
                    download_links_html = '<div class="download-links"><p><strong>Download Links:</strong></p>'
                    for j, link in enumerate(download_links[:5], 1):  # Limit to 5 links
                        link_name = link.get('name') or link.get('text') or f'Download {j}'
                        link_url = link.get('url', '#')
                        download_links_html += f'<a href="{link_url}" target="_blank" class="download-link">{link_name}</a>'
                    download_links_html += '</div>'
                else:
                    download_links_html = '<p><em>No direct download links found. Use MD5 hash on LibGen mirrors.</em></p>'
                
                results_html += f"""
                <div style="border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; background: #fafafa;">
                    <h3>{i}. {book.get('title', 'N/A')}</h3>
                    <p><strong>Author:</strong> {book.get('author', 'N/A')}</p>
                    <p><strong>Format:</strong> {book.get('extension', 'N/A')} | <strong>Year:</strong> {book.get('year', 'N/A')}</p>
                    {download_links_html}
                </div>
                """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Search Results - LibGen</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; text-align: center; }}
                .message {{ color: #e74c3c; margin: 10px 0; }}
                code {{ background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }}
                .book-result {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; background: #fafafa; }}
                .download-links {{ margin: 10px 0; }}
                .download-links ul {{ list-style-type: none; padding: 0; }}
                .download-links li {{ margin: 5px 0; }}
                .download-link {{ display: inline-block; padding: 8px 15px; background-color: #3498db; color: white; text-decoration: none; border-radius: 4px; margin: 2px; }}
                .download-link:hover {{ background-color: #2980b9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>LibGen Search Results</h1>
                <p><a href="/">← Back to Search</a></p>
                
                {results_html}
                
                <p><a href="/">Search Again</a></p>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

def main():
    """Start the web server"""
    port = 8080
    server_address = ('', port)
    
    print(f"🚀 Starting LibGen Web Interface...")
    print(f"🌐 Open your browser and go to: http://localhost:{port}")
    print(f"📚 LibGen search functionality is fully working!")
    print(f"🔍 You can search for any book title, author, or ISBN")
    print(f"\\n Press Ctrl+C to stop the server\\n")
    
    try:
        httpd = HTTPServer(server_address, LibGenWebHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped")
        httpd.shutdown()

if __name__ == '__main__':
    main()
