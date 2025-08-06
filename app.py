import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv
import uuid

# Configurações
# Carrega as variáveis de ambiente
load_dotenv()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # Verifique se esta é a URL correta
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
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
    if 'srt_file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['srt_file']
    
    if file.filename == '':
        return jsonify({'error': 'Nome de arquivo vazio'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'Apenas arquivos .srt são permitidos'}), 400
    
    try:
        # Salva o arquivo temporariamente
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Lê o conteúdo do SRT
        srt_content = read_srt_file(filepath)
        
        # Chama a API de tradução
        translated_content = translate_with_deepseek(srt_content)
        
        # Salva a tradução
        translated_filename = f"traduzido_{filename}"
        translated_path = os.path.join(app.config['UPLOAD_FOLDER'], translated_filename)
        with open(translated_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)
        
        # Remove o arquivo temporário
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'original': filename,
            'translated': translated_filename,
            'download_url': f'/download/{translated_filename}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Função para ler arquivos SRT
def read_srt_file(filepath):
    """Lê o conteúdo de um arquivo SRT e retorna o texto para tradução"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()
    
# Função para chamar a API do DeepSeek
def translate_with_deepseek(text):
    """Envia texto para a API do DeepSeek e retorna a tradução"""
    if not DEEPSEEK_API_KEY:
        raise ValueError("Chave API não configurada")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Instrução mais clara para a API
    system_prompt = """Você é um tradutor profissional de legendas SRT. 
    Sua tarefa é traduzir APENAS o texto dos diálogos, mantendo:
    - Números de sequência intactos
    - Timestamps no formato exato HH:MM:SS,ms --> HH:MM:SS,ms
    - Formatação original
    Não adicione comentários ou explicações."""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Traduza este SRT para português:\n\n{text}"}
        ],
        "temperature": 0.1  # Menor = mais preciso
    }
    
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=30  # 30 segundos de timeout
        )
        response.raise_for_status()  # Levanta erro para status 4xx/5xx
        
        return response.json()["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        print(f"Erro na API DeepSeek: {str(e)}")
        print(f"Resposta da API: {e.response.text if e.response else 'Sem resposta'}")
        raise

# Adicição de rota para download 
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Suas rotas existentes...
@app.route("/")
def home():
    return render_template("index.html")

# ... outras rotas ...

if __name__ == "__main__":
    app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)