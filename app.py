import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from src.config import Config
from src.validation_service import ValidationService
from src.file_service import FileService
from src.translation_service import TranslationService

def create_app():
    """Cria e configura a aplicação Flask"""
    app = Flask(__name__)
    
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
    
    @app.route('/start-translation', methods=['POST'])
    def start_translation():
        """Inicia uma tradução com chunks paralelos"""
        try:
            uploaded_file = request.files.get('srt_file')
            original_filename = validation_service.validate_file_upload(uploaded_file)
            
            # Salva o arquivo temporariamente
            filepath, unique_filename = file_service.save_uploaded_file(
                uploaded_file, 
                original_filename
            )
            
            # Inicia a tradução assíncrona com chunks
            translation_id = translation_service.start_translation(
                filepath, original_filename, unique_filename
            )
            
            return jsonify({
                'success': True,
                'translation_id': translation_id,
                'message': 'Tradução iniciada com processamento paralelo'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/translation-status/<translation_id>')
    def translation_status(translation_id):
        """Retorna o status detalhado de uma tradução com chunks"""
        try:
            status = translation_service.get_translation_status(translation_id)
            
            if not status:
                return jsonify({'error': 'Tradução não encontrada'}), 404
            
            response_data = {
                'status': status.get('status', 'unknown'),
                'progress': status.get('progress', 0),
                'message': status.get('message', ''),
                'translated_filename': status.get('translated_filename'),
                'download_url': status.get('download_url'),
                'error': status.get('error')
            }
            
            # Adiciona informações de chunks se disponível
            if 'chunks_processed' in status and 'total_chunks' in status:
                response_data['chunks_processed'] = status['chunks_processed']
                response_data['total_chunks'] = status['total_chunks']
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # ===== ROTA DE UPLOAD LEGADO (mantida para compatibilidade) =====
    @app.route('/upload', methods=['POST'])
    def handle_upload():
        """Processa o upload e tradução de arquivos SRT (método legado)"""
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