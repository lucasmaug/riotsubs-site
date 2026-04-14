import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import uuid
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import Config


# Mapa código → nome completo do idioma para o prompt
LANG_NAMES = {
    'pt-br': 'português brasileiro',
    'pt-pt': 'português europeu (de Portugal)',
    'en':    'inglês',
    'es':    'espanhol',
}


class TranslationService:
    def __init__(self):
        self.use_mock   = Config.USE_MOCK_API
        self.api_url    = Config.DEEPSEEK_API_URL
        self.api_key    = Config.DEEPSEEK_API_KEY
        self.active_translations = {}
        self.chunk_size = 50

        # Session HTTP compartilhada com retry automático
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retry))
        if not self.use_mock and self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type':  'application/json',
            })

    # ─── API pública ──────────────────────────────────────────────────────────

    def start_translation(self, filepath, original_filename, unique_filename,
                          lang='pt-br', media_type='', instructions=''):
        translation_id = str(uuid.uuid4())

        self.active_translations[translation_id] = {
            'status':            'processing',
            'progress':          0,
            'filepath':          filepath,
            'original_filename': original_filename,
            'unique_filename':   unique_filename,
            'lang':              lang,
            'media_type':        media_type,
            'instructions':      instructions,
            'chunks_processed':  0,
            'total_chunks':      0,
        }

        thread = threading.Thread(
            target=self._process_translation,
            args=(translation_id,),
        )
        thread.daemon = True
        thread.start()

        return translation_id

    def get_translation_status(self, translation_id):
        return self.active_translations.get(translation_id, {})

    def cancel_translation(self, translation_id):
        if translation_id in self.active_translations:
            self.active_translations[translation_id]['status'] = 'cancelled'
            return True
        return False

    # Compatibilidade com a rota /upload legada
    def translate(self, text, lang='pt-br', media_type='', instructions=''):
        if self.use_mock:
            return self._mock_translate_chunk(text)
        return self._call_api(text, lang, media_type, instructions)

    # ─── Processamento assíncrono ─────────────────────────────────────────────

    def _process_translation(self, translation_id):
        """Processa chunks em paralelo (até 3 ao mesmo tempo)."""
        td = self.active_translations[translation_id]

        try:
            self._update_progress(translation_id, 10, 'Lendo arquivo...')

            from src.file_service    import FileService
            from src.validation_service import ValidationService

            file_service       = FileService(Config.UPLOAD_FOLDER)
            validation_service = ValidationService(Config.ALLOWED_EXTENSIONS, Config.MAX_FILE_SIZE)

            srt_content = file_service.read_file_content(td['filepath'])
            validation_service.validate_srt_content(srt_content)

            self._update_progress(translation_id, 20, 'Preparando blocos...')
            chunks = self._split_srt_into_chunks(srt_content)
            total  = len(chunks)
            td['total_chunks'] = total

            lang         = td.get('lang', 'pt-br')
            media_type   = td.get('media_type', '')
            instructions = td.get('instructions', '')

            print(f'📦 {total} chunks | idioma: {lang} | mídia: {media_type or "—"}')

            self._update_progress(translation_id, 30, 'Iniciando tradução...')

            results        = {}
            failed_chunks  = 0
            done_count     = 0
            lock           = threading.Lock()

            def translate_one(index, chunk_text):
                if td['status'] == 'cancelled':
                    return index, chunk_text
                print(f'🔄 Chunk {index + 1}/{total}...')
                try:
                    if self.use_mock:
                        result = self._mock_translate_chunk(chunk_text)
                    else:
                        result = self._call_api(chunk_text, lang, media_type, instructions)
                    print(f'✅ Chunk {index + 1} concluído')
                    return index, result
                except Exception as e:
                    print(f'❌ Chunk {index + 1} falhou: {e}')
                    return index, chunk_text  # fallback: mantém original

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(translate_one, i, chunk): i
                    for i, chunk in enumerate(chunks)
                }

                for future in as_completed(futures):
                    index, translated_text = future.result()

                    with lock:
                        results[index] = translated_text
                        if translated_text == chunks[index]:
                            failed_chunks += 1
                        done_count += 1
                        td['chunks_processed'] = done_count

                    if failed_chunks > total * 0.3:
                        raise Exception(f'Muitos chunks falharam: {failed_chunks}/{total}')

                    progress = 30 + (done_count / total) * 60
                    self._update_progress(
                        translation_id,
                        int(progress),
                        f'Traduzindo... ({done_count}/{total} blocos)',
                    )

            # Reconstrói na ordem original
            self._update_progress(translation_id, 90, 'Montando arquivo final...')
            final_content = '\n\n'.join(results[i] for i in range(total))

            # Salva com nome que já reflete o idioma
            translated_filename = file_service.save_translated_file(
                final_content,
                td['unique_filename'],
                lang=lang,
            )

            self._update_progress(translation_id, 100, 'Tradução concluída!')

            if failed_chunks > 0:
                print(f'⚠️  {failed_chunks} chunks mantiveram o texto original')

            td.update({
                'status':              'completed',
                'translated_filename': translated_filename,
                'download_url':        f'/download/{translated_filename}',
                'failed_chunks':       failed_chunks,
            })

        except Exception as e:
            print(f'❌ Erro na tradução {translation_id}: {e}')
            td.update({'status': 'error', 'error': str(e)})

        finally:
            try:
                from src.file_service import FileService
                FileService(Config.UPLOAD_FOLDER).cleanup_file(td['filepath'])
            except Exception:
                pass

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _split_srt_into_chunks(self, srt_content):
        blocks = [b.strip() for b in re.split(r'\n\s*\n', srt_content.strip()) if b.strip()]
        return [
            '\n\n'.join(blocks[s: s + self.chunk_size])
            for s in range(0, len(blocks), self.chunk_size)
        ]

    def _build_prompt(self, lang, media_type, instructions):
        """Monta o user prompt contextualizado."""
        lang_name = LANG_NAMES.get(lang, lang)

        parts = [f'Traduza para {lang_name}:']

        if media_type:
            parts.append(f'Tipo de conteúdo: {media_type}.')

        if instructions:
            parts.append(f'Instruções adicionais: {instructions}')

        return ' '.join(parts)

    def _call_api(self, chunk_content, lang='pt-br', media_type='', instructions=''):
        """Chama a DeepSeek para traduzir um chunk."""
        if not self.api_key:
            raise ValueError('DEEPSEEK_API_KEY não configurada')

        lang_name = LANG_NAMES.get(lang, lang)

        system_prompt = (
            'Você é um tradutor profissional de legendas SRT. '
            'Traduza APENAS o texto dos diálogos, mantendo: '
            'números de sequência intactos, timestamps no formato '
            'HH:MM:SS,ms --> HH:MM:SS,ms, e a formatação original. '
            f'O idioma de destino é {lang_name}. '
            'Não adicione comentários ou explicações.'
        )

        user_content = self._build_prompt(lang, media_type, instructions)
        user_content += f'\n\n{chunk_content}'

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': user_content},
            ],
            'temperature': 0.1,
            'max_tokens':  2000,
        }

        print(f'📤 Enviando chunk ({len(chunk_content)} chars) → {lang_name}...')
        response = self.session.post(self.api_url, json=payload, timeout=(10, 60))
        print(f'📥 Status: {response.status_code}')

        if response.status_code != 200:
            raise Exception(f'API retornou {response.status_code}: {response.text}')

        raw = response.json()['choices'][0]['message']['content']

        from src.validation_service import ValidationService
        return ValidationService(set(), 0).validate_api_response(raw)

    def _mock_translate_chunk(self, chunk_content):
        lines = chunk_content.split('\n')
        result = []
        for line in lines:
            line = line.strip()
            if line.isdigit() or '-->' in line or not line:
                result.append(line)
            else:
                result.append(f'[TRADUZIDO] {line}')
        return '\n'.join(result)

    def _update_progress(self, translation_id, progress, message=''):
        if translation_id in self.active_translations:
            self.active_translations[translation_id]['progress'] = progress
            if message:
                self.active_translations[translation_id]['message'] = message
            print(f'📊 {progress}% — {message}')