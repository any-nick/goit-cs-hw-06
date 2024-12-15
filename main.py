import mimetypes
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket
from datetime import datetime
import threading
import json

DB_PATH = './storage/data.json'

def save_to_db(message):
    pathlib.Path('./storage').mkdir(parents=True, exist_ok=True)
    try:
        with open(DB_PATH, 'r') as db_file:
            data = json.load(db_file)
            if not isinstance(data, list):
                data = []
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(message)

    with open(DB_PATH, 'w') as db_file:
        json.dump(data, db_file, indent=4)


class HttpHandler(BaseHTTPRequestHandler):
    SOCKET_HOST = '127.0.0.1'
    SOCKET_PORT = 5000

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        data_parse = urllib.parse.unquote_plus(data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.SOCKET_HOST, self.SOCKET_PORT))
            sock.sendall(json.dumps(data_dict).encode())

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/contact':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

def socket_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(5)
        print(f"Socket server running on {host}:{port}")
        while True:
            conn, addr = server.accept()
            with conn:
                data = conn.recv(1024)
                if data:
                    message = json.loads(data.decode())
                    message['date'] = datetime.now().isoformat()
                    save_to_db(message)
                    print(f"Saved message: {message}")

if __name__ == '__main__':
    http_thread = threading.Thread(target=lambda: HTTPServer(('', 3000), HttpHandler).serve_forever())
    socket_thread = threading.Thread(target=socket_server, args=('127.0.0.1', 5000))

    http_thread.start()
    socket_thread.start()

    http_thread.join()
    socket_thread.join()
