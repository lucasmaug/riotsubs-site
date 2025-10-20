import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from src.config import Config
from src.validation_service import ValidationService
from src.file_service import FileService
from src.translation_service import TranslationService

def create_app():
    """Cria e configura a aplicação Flask"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE
    
    # Valida configurações
    Config.validate_config()
    
    # Inicializa serviços
    validation_service = ValidationService(
        Config.ALLOWED_EXTENSIONS, 
        Config.MAX_FILE_SIZE
    )
    file_service = FileService(Config.UPLOAD_FOLDER)
    translation_service = TranslationService()
    
    # ===== ROTAS PRINCIPAIS =====
    @app.route("/")
    def home():
        return render_template("index.html")
    
    @app.route("/about")
    def about():
        return render_template("about.html")
    
    @app.route("/faq")
    def faq():
        return render_template("faq.html")
    
    @app.route("/termos-e-privacidade")
    def termos():
        return render_template("termos-e-privacidade.html")
    
    # ===== ROTA DE UPLOAD =====
    @app.route('/upload', methods=['POST'])
    def handle_upload():
        """Processa o upload e tradução de arquivos SRT"""
        try:
            # Validação do upload
            uploaded_file = request.files.get('srt_file')
            original_filename = validation_service.validate_file_upload(uploaded_file)
            
            # Processamento do arquivo
            filepath, unique_filename = file_service.save_uploaded_file(
                uploaded_file, 
                original_filename
            )
            
            try:
                # Leitura e validação do conteúdo
                srt_content = file_service.read_file_content(filepath)
                validation_service.validate_srt_content(srt_content)
                
                # Tradução
                translated_content = translation_service.translate(srt_content)
                
                # Salvamento do resultado
                translated_filename = file_service.save_translated_file(
                    translated_content, 
                    unique_filename
                )
                
                return jsonify({
                    'success': True,
                    'original': original_filename,
                    'translated': translated_filename,
                    'download_url': f'/download/{translated_filename}'
                })
                
            finally:
                # Limpeza do arquivo temporário
                file_service.cleanup_file(filepath)
                
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    
    # ===== ROTA DE DOWNLOAD =====
    @app.route('/download/<filename>')
    def download_file(filename):
        return send_from_directory(
            Config.UPLOAD_FOLDER, 
            filename, 
            as_attachment=True
        )
    
    # ===== ROTA DE TESTE DA API =====
    @app.route('/test-api')
    def test_api():
        """Rota para testar a conexão com a API"""
        if Config.USE_MOCK_API:
            return jsonify({
                "status": "mock", 
                "message": "Usando modo mock para desenvolvimento"
            })
        
        try:
            test_result = translation_service.translate("Hello")
            return jsonify({
                "status": "success", 
                "message": "API DeepSeek conectada com sucesso",
                "test_translation": test_result[:50] + "..." if len(test_result) > 50 else test_result
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Erro na conexão com API: {str(e)}"
            }), 500
    
    return app

# Cria a aplicação
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)