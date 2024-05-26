import http.server
import socketserver
import socket
import threading
import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

PORT = 3000
SOCKET_PORT = 5000
STATIC_FOLDER = 'static'
STORAGE_FOLDER = 'storage'
DATA_FILE = os.path.join(STORAGE_FOLDER, 'data.json')
TEMPLATES_FOLDER = 'templates'

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/message':
            self.path = '/message.html'
        
        if self.path.endswith('.html'):
            self.path = os.path.join(TEMPLATES_FOLDER, self.path[1:])
        else:
            self.path = os.path.join(STATIC_FOLDER, self.path[1:])

        if not os.path.exists(self.path):
            self.path = os.path.join(TEMPLATES_FOLDER, 'error.html')
            self.send_response(404)
        else:
            self.send_response(200)
        
        self.end_headers()
        with open(self.path, 'rb') as file:
            self.wfile.write(file.read())

    def do_POST(self):
        if self.path == '/submit_message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            parsed_data = parse_qs(post_data.decode())
            
            username = parsed_data.get('username', [''])[0]
            message = parsed_data.get('message', [''])[0]
            
            send_to_socket_server(username, message)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({"status": "success"})
            self.wfile.write(response.encode())

def run_http_server():
    handler = MyHttpRequestHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    print(f"Serving HTTP on port {PORT}")
    httpd.serve_forever()

def send_to_socket_server(username, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', SOCKET_PORT)
    message_data = json.dumps({"username": username, "message": message})
    sock.sendto(message_data.encode(), server_address)
    sock.close()

def socket_server():
    if not os.path.exists(STORAGE_FOLDER):
        os.makedirs(STORAGE_FOLDER)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', SOCKET_PORT)
    sock.bind(server_address)
    
    while True:
        data, address = sock.recvfrom(4096)
        if data:
            message = json.loads(data.decode())
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            save_message(timestamp, message)

def save_message(timestamp, message):
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as file:
            json.dump({}, file)
    
    with open(DATA_FILE, 'r+') as file:
        data = json.load(file)
        data[timestamp] = message
        file.seek(0)
        json.dump(data, file, indent=4)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_http_server)
    socket_thread = threading.Thread(target=socket_server)
    flask_thread.start()
    socket_thread.start()
    flask_thread.join()
    socket_thread.join()
