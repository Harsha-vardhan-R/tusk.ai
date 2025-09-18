from flask import Flask, jsonify, request

from rag import rag_pipeline

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Flask server is running on port 5000!"

@app.route('/health/<name>')
def health(name):
    return f"'Hello': {name}"

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

# the only endpoint used.
@app.route('/prompt', methods=['POST'])
def generateOutput():
    data = request.get_json()

    if data is None:
        return jsonify({"error" : "Missing arguments for the POST request"})

    prompt = data.get("prompt")
    context = data.get("context")

    return rag_pipeline(context, prompt)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
