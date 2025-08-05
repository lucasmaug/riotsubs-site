import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify
import uuid

# Configurações
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'srt'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Cria pasta se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def handle_upload():
    try:
        if 'srt_file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['srt_file']
        
        if file.filename == '':
            return jsonify({'error': 'Nome de arquivo vazio'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Apenas arquivos .srt são permitidos'}), 400
        
        # Gera nome seguro e único
        filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'Arquivo recebido com sucesso',
            'path': filepath
        })
        
    except Exception as e:
        return jsonify({'error': f"Erro no servidor: {str(e)}"}), 500

# Suas rotas existentes...
@app.route("/")
def home():
    return render_template("index.html")

# ... outras rotas ...

if __name__ == "__main__":
    app.run(debug=True)