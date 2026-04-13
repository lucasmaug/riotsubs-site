import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import uuid
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import Config


class TranslationService:
    def __init__(self):
        self.use_mock = Config.USE_MOCK_API
        self.api_url = Config.DEEPSEEK_API_URL
        self.api_key = Config.DEEPSEEK_API_KEY
        self.active_translations = {}
        self.chunk_size = 50  # Aumentado de 20 para 50 — menos roundtrips na API

        # Session HTTP compartilhada: reutiliza conexão TCP entre chunks (keep-alive)
        # Antes: uma Session nova era criada e destruída para cada chunk
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        if not self.use_mock and self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })

    def start_translation(self, filepath, original_filename, unique_filename):
        translation_id = str(uuid.uuid4())

        self.active_translations[translation_id] = {
            "status": "processing",
            "progress": 0,
            "filepath": filepath,
            "original_filename": original_filename,
            "unique_filename": unique_filename,
            "chunks_processed": 0,
            "total_chunks": 0,
        }

        thread = threading.Thread(
            target=self._process_translation,
            args=(translation_id,),
        )
        thread.daemon = True
        thread.start()

        return translation_id

    def _process_translation(self, translation_id):
        """Processa chunks em paralelo (até 3 ao mesmo tempo)."""
        translation_data = self.active_translations[translation_id]

        try:
            # 1. Lê o arquivo
            self._update_progress(translation_id, 10, "Lendo arquivo...")

            from src.file_service import FileService
            from src.validation_service import ValidationService

            file_service = FileService(Config.UPLOAD_FOLDER)
            validation_service = ValidationService(
                Config.ALLOWED_EXTENSIONS, Config.MAX_FILE_SIZE
            )

            srt_content = file_service.read_file_content(translation_data["filepath"])
            validation_service.validate_srt_content(srt_content)

            # 2. Divide em chunks
            self._update_progress(translation_id, 20, "Preparando blocos...")
            chunks = self._split_srt_into_chunks(srt_content)
            total = len(chunks)
            translation_data["total_chunks"] = total

            print(f"📦 {total} chunks de até {self.chunk_size} blocos cada")

            # 3. Traduz em paralelo — 3 workers simultâneos
            # Antes: for loop sequencial com sleep(1) entre cada chunk
            self._update_progress(translation_id, 30, "Iniciando tradução...")

            results = {}          # {índice: texto_traduzido}
            failed_chunks = 0
            done_count = 0
            lock = threading.Lock()

            def translate_one(index, chunk_text):
                """Traduz um único chunk; retorna (index, texto)."""
                if translation_data["status"] == "cancelled":
                    return index, chunk_text  # fallback: original

                print(f"🔄 Chunk {index + 1}/{total}...")
                try:
                    if self.use_mock:
                        result = self._mock_translate_chunk(chunk_text)
                    else:
                        result = self._call_api(chunk_text)
                    print(f"✅ Chunk {index + 1} concluído")
                    return index, result
                except Exception as e:
                    print(f"❌ Chunk {index + 1} falhou: {e}")
                    return index, chunk_text  # fallback: mantém original

            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_index = {
                    executor.submit(translate_one, i, chunk): i
                    for i, chunk in enumerate(chunks)
                }

                for future in as_completed(future_to_index):
                    index, translated_text = future.result()

                    with lock:
                        results[index] = translated_text
                        if translated_text == chunks[index]:
                            # texto não mudou = fallback (chunk falhou)
                            failed_chunks += 1
                        done_count += 1
                        translation_data["chunks_processed"] = done_count

                    # Verifica limite de falhas
                    if failed_chunks > total * 0.3:
                        raise Exception(
                            f"Muitos chunks falharam: {failed_chunks}/{total}"
                        )

                    progress = 30 + (done_count / total) * 60
                    self._update_progress(
                        translation_id,
                        int(progress),
                        f"Traduzindo... ({done_count}/{total} blocos)",
                    )

            # 4. Reconstrói o arquivo na ordem original
            self._update_progress(translation_id, 90, "Montando arquivo final...")
            translated_chunks = [results[i] for i in range(total)]
            final_content = "\n\n".join(translated_chunks)

            # 5. Salva
            translated_filename = file_service.save_translated_file(
                final_content, translation_data["unique_filename"]
            )

            self._update_progress(translation_id, 100, "Tradução concluída!")

            if failed_chunks > 0:
                print(f"⚠️  {failed_chunks} chunks mantiveram o texto original")

            translation_data.update({
                "status": "completed",
                "translated_filename": translated_filename,
                "download_url": f"/download/{translated_filename}",
                "failed_chunks": failed_chunks,
            })

        except Exception as e:
            print(f"❌ Erro na tradução {translation_id}: {e}")
            translation_data.update({"status": "error", "error": str(e)})

        finally:
            try:
                from src.file_service import FileService
                FileService(Config.UPLOAD_FOLDER).cleanup_file(
                    translation_data["filepath"]
                )
            except Exception:
                pass

    def _split_srt_into_chunks(self, srt_content):
        """Divide o SRT em grupos de blocos mantendo cada bloco intacto."""
        blocks = [b.strip() for b in re.split(r"\n\s*\n", srt_content.strip()) if b.strip()]
        chunks = []
        for start in range(0, len(blocks), self.chunk_size):
            chunk = blocks[start : start + self.chunk_size]
            chunks.append("\n\n".join(chunk))
        return chunks

    def _call_api(self, chunk_content):
        """Chama a DeepSeek para traduzir um chunk. Usa a session compartilhada."""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY não configurada")

        system_prompt = (
            "Você é um tradutor profissional de legendas SRT. "
            "Traduza APENAS o texto dos diálogos, mantendo: "
            "números de sequência intactos, timestamps no formato "
            "HH:MM:SS,ms --> HH:MM:SS,ms, e a formatação original. "
            "Não adicione comentários ou explicações."
        )

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Traduza para português brasileiro:\n\n{chunk_content}",
                },
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }

        print(f"📤 Enviando chunk ({len(chunk_content)} chars)...")
        response = self.session.post(self.api_url, json=payload, timeout=(10, 60))
        print(f"📥 Status: {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"API retornou {response.status_code}: {response.text}")

        data = response.json()
        raw = data["choices"][0]["message"]["content"]

        # Valida e limpa a resposta — remove markdown, texto explicativo, etc.
        from src.validation_service import ValidationService
        validator = ValidationService(set(), 0)
        return validator.validate_api_response(raw)

    def _mock_translate_chunk(self, chunk_content):
        """Mock para desenvolvimento — não chama API real."""
        lines = chunk_content.split("\n")
        translated = []
        for line in lines:
            line = line.strip()
            if line.isdigit() or "-->" in line or not line:
                translated.append(line)
            else:
                translated.append(f"[TRADUZIDO] {line}")
        return "\n".join(translated)

    def _update_progress(self, translation_id, progress, message=""):
        if translation_id in self.active_translations:
            self.active_translations[translation_id]["progress"] = progress
            if message:
                self.active_translations[translation_id]["message"] = message
            print(f"📊 {progress}% — {message}")

    def get_translation_status(self, translation_id):
        return self.active_translations.get(translation_id, {})

    def cancel_translation(self, translation_id):
        if translation_id in self.active_translations:
            self.active_translations[translation_id]["status"] = "cancelled"
            return True
        return False

    # Compatibilidade com a rota /upload legada
    def translate(self, text):
        if self.use_mock:
            return self._mock_translate_chunk(text)
        return self._call_api(text)
