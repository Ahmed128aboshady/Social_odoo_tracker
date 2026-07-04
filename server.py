import http.server
import json
import os
import subprocess

PORT = 8085
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/api/config':
            try:
                config_path = os.path.join(DIRECTORY, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                else:
                    template_path = os.path.join(DIRECTORY, "config.template.json")
                    with open(template_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                
                # Sanitize response by excluding token
                sanitized_config = {
                    "facebook_groups": config_data.get("facebook", {}).get("groups", []),
                    "facebook_keywords": config_data.get("facebook", {}).get("keywords", []),
                    "linkedin_queries": config_data.get("linkedin_jobs", {}).get("queries", []),
                    "linkedin_post_queries": config_data.get("linkedin_posts", {}).get("queries", [])
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(sanitized_config).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading config: {e}".encode('utf-8'))
        else:
            # Fallback to default static file server
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                new_config = json.loads(post_data.decode('utf-8'))
                config_path = os.path.join(DIRECTORY, "config.json")
                
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        current_config = json.load(f)
                else:
                    template_path = os.path.join(DIRECTORY, "config.template.json")
                    with open(template_path, "r", encoding="utf-8") as f:
                        current_config = json.load(f)
                
                if "facebook_groups" in new_config:
                    current_config["facebook"]["groups"] = new_config["facebook_groups"]
                if "facebook_keywords" in new_config:
                    current_config["facebook"]["keywords"] = new_config["facebook_keywords"]
                if "linkedin_queries" in new_config:
                    current_config["linkedin_jobs"]["queries"] = new_config["linkedin_queries"]
                if "linkedin_post_queries" in new_config:
                    current_config["linkedin_posts"]["queries"] = new_config["linkedin_post_queries"]
                
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(current_config, f, ensure_ascii=False, indent=2)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Configuration saved successfully"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error saving config: {e}".encode('utf-8'))
                
        elif self.path == '/api/run-scraper':
            try:
                script_path = os.path.join(DIRECTORY, "tracker.py")
                print(f"Running scraper script: {script_path}")
                
                # Execute synchronously to let the user know when it completes
                result = subprocess.run(["python", script_path], capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": "Scraper executed successfully", "output": result.stdout}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Scraper script failed", "error": result.stderr}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error starting scraper: {e}".encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    print(f"Starting Odoo Leads server on http://localhost:{PORT}...")
    server = http.server.HTTPServer(('', PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
