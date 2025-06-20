import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.youtube import youtube_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Habilitar CORS
CORS(app)

# Registrar blueprints ANTES das rotas catch-all
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(youtube_bp, url_prefix='/api/youtube')

# Handler de erro global para APIs
@app.errorhandler(404)
def handle_404(e):
    # Se a requisição é para API, retorna JSON
    if '/api/' in str(e.original_exception) or '/api/' in str(e):
        return jsonify({'error': 'Endpoint não encontrado'}), 404
    # Caso contrário, serve o index.html para SPA
    return serve('')

@app.errorhandler(500)
def handle_500(e):
    # Para APIs, sempre retorna JSON
    return jsonify({'error': 'Erro interno do servidor'}), 500

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Não interceptar rotas da API
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint não encontrado'}), 404
        
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
