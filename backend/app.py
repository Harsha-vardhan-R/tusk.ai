from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Flask server is running on port 5000!"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)