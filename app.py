import os
import re
import json
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context, abort
from src.config import Config
from src.validation_service import ValidationService
from src.file_service import FileService
from src.translation_service import TranslationService


def create_app():
    app = Flask(__name__)

    Config.validate_config()

    validation_service  = ValidationService(Config.ALLOWED_EXTENSIONS, Config.MAX_FILE_SIZE)
    file_service        = FileService(Config.UPLOAD_FOLDER)
    translation_service = TranslationService()

    # ─── Headers de segurança ─────────────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options']  = 'nosniff'
        response.headers['X-Frame-Options']          = 'SAMEORIGIN'
        response.headers['X-XSS-Protection']         = '1; mode=block'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy']  = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:"
        )
        return response

    # ─── Páginas ──────────────────────────────────────────────────────────────
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/faq')
    def faq():
        return render_template('faq.html')

    @app.route('/termos-e-privacidade')
    def termos():
        return render_template('termos-e-privacidade.html')

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static', 'icons'),
            'favicon.png',
            mimetype='image/png',
        )

    @app.route('/ping')
    def ping():
        return 'OK', 200

    # ─── Iniciar tradução ─────────────────────────────────────────────────────
    @app.route('/start-translation', methods=['POST'])
    def start_translation():
        try:
            file_service.cleanup_old_files(max_age_hours=24)

            uploaded_file     = request.files.get('srt_file')
            safe_filename, original_filename = validation_service.validate_file_upload(uploaded_file)

            filepath, unique_filename = file_service.save_uploaded_file(
                uploaded_file, safe_filename
            )

            # Parâmetros de tradução enviados pelo frontend
            lang         = request.form.get('lang', 'pt-br').strip()
            media_type   = request.form.get('media_type', '').strip()
            instructions = request.form.get('instructions', '').strip()

            # Validação mínima do idioma
            allowed_langs = {'pt-br', 'pt-pt', 'en', 'es'}
            if lang not in allowed_langs:
                lang = 'pt-br'

            translation_id = translation_service.start_translation(
                filepath, original_filename, unique_filename,
                lang=lang, media_type=media_type, instructions=instructions,
            )

            return jsonify({
                'success':        True,
                'translation_id': translation_id,
                'message':        'Tradução iniciada',
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 400

    # ─── Status via polling ───────────────────────────────────────────────────
    @app.route('/translation-status/<translation_id>')
    def translation_status(translation_id):
        try:
            status = translation_service.get_translation_status(translation_id)
            if not status:
                return jsonify({'error': 'Tradução não encontrada'}), 404

            return jsonify({
                'status':              status.get('status', 'unknown'),
                'progress':            status.get('progress', 0),
                'message':             status.get('message', ''),
                'translated_filename': status.get('translated_filename'),
                'download_url':        status.get('download_url'),
                'error':               status.get('error'),
                'chunks_processed':    status.get('chunks_processed'),
                'total_chunks':        status.get('total_chunks'),
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ─── Status via Server-Sent Events ───────────────────────────────────────
    @app.route('/translation-stream/<translation_id>')
    def translation_stream(translation_id):
        def generate():
            while True:
                status = translation_service.get_translation_status(translation_id)
                if not status:
                    yield f"data: {json.dumps({'error': 'Tradução não encontrada'})}\n\n"
                    break
                yield f'data: {json.dumps(status)}\n\n'
                if status.get('status') in ('completed', 'error', 'cancelled'):
                    break
                time.sleep(0.8)

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
        )

    # ─── Upload legado (compatibilidade) ──────────────────────────────────────
    @app.route('/upload', methods=['POST'])
    def handle_upload():
        try:
            uploaded_file     = request.files.get('srt_file')
            safe_filename, original_filename = validation_service.validate_file_upload(uploaded_file)

            filepath, unique_filename = file_service.save_uploaded_file(
                uploaded_file, safe_filename
            )

            try:
                srt_content = file_service.read_file_content(filepath)
                validation_service.validate_srt_content(srt_content)

                lang = request.form.get('lang', 'pt-br')
                translated_content = translation_service.translate(srt_content, lang=lang)

                translated_filename = file_service.save_translated_file(
                    translated_content, unique_filename, lang=lang
                )

                return jsonify({
                    'success':    True,
                    'original':   original_filename,
                    'translated': translated_filename,
                    'download_url': f'/download/{translated_filename}',
                })
            finally:
                file_service.cleanup_file(filepath)

        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'Erro interno: {str(e)}'}), 500

    # ─── Download ─────────────────────────────────────────────────────────────
    @app.route('/download/<filename>')
    def download_file(filename):
        # Aceita nomes com colchetes, hífens, pontos, underscores e espaços — mas sem barras
        if not re.match(r'^[\w\-\.\[\] ]+\.srt$', filename):
            abort(400)
        # Monta nome de exibição: remove prefixo único e restaura espaços
        display_name = re.sub(r'^traduzido_[a-f0-9]{8}_', '', filename)
        display_name = display_name.replace('_', ' ')

        response = send_from_directory(
            Config.UPLOAD_FOLDER,
            filename,
            as_attachment=True,
            mimetype='text/plain; charset=utf-8',
        )
        response.headers['Content-Disposition'] = (
            f"attachment; filename=\"{display_name}\"; filename*=UTF-8''{display_name}"
        )
        response.headers['Cache-Control'] = 'no-store'
        return response

    # ─── Teste de API ─────────────────────────────────────────────────────────
    @app.route('/test-api')
    def test_api():
        if Config.USE_MOCK_API:
            return jsonify({'status': 'mock', 'message': 'Usando modo mock para desenvolvimento'})
        try:
            test_result = translation_service.translate('Hello')
            preview     = test_result[:50] + '...' if len(test_result) > 50 else test_result
            return jsonify({
                'status':           'success',
                'message':          'API DeepSeek conectada com sucesso',
                'test_translation': preview,
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Erro na conexão: {str(e)}'}), 500

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)