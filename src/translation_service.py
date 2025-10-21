import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import uuid
import re
import threading
from src.config import Config

class TranslationService:
    def __init__(self):
        self.use_mock = Config.USE_MOCK_API
        self.api_url = Config.DEEPSEEK_API_URL
        self.api_key = Config.DEEPSEEK_API_KEY
        self.active_translations = {}
        self.chunk_size = 20  # CHUNKS MENORES para evitar timeout

    def start_translation(self, filepath, original_filename, unique_filename):
        translation_id = str(uuid.uuid4())
        
        self.active_translations[translation_id] = {
            'status': 'processing',
            'progress': 0,
            'filepath': filepath,
            'original_filename': original_filename,
            'unique_filename': unique_filename,
            'chunks_processed': 0,
            'total_chunks': 0
        }
        
        thread = threading.Thread(
            target=self._process_translation_sequential_chunks,
            args=(translation_id,)
        )
        thread.daemon = True
        thread.start()
        
        return translation_id
    
    def _process_translation_sequential_chunks(self, translation_id):
        """Processa chunks UM POR VEZ (sequencial)"""
        try:
            translation_data = self.active_translations[translation_id]
            filepath = translation_data['filepath']
            
            # 1. Lendo arquivo
            self._update_progress(translation_id, 10, "Lendo arquivo...")
            
            from src.file_service import FileService
            from src.validation_service import ValidationService
            
            file_service = FileService(Config.UPLOAD_FOLDER)
            validation_service = ValidationService(Config.ALLOWED_EXTENSIONS, Config.MAX_FILE_SIZE)
            
            srt_content = file_service.read_file_content(filepath)
            validation_service.validate_srt_content(srt_content)
            
            # 2. Dividindo em chunks
            self._update_progress(translation_id, 20, "Preparando blocos...")
            chunks = self._split_srt_into_chunks(srt_content)
            translation_data['total_chunks'] = len(chunks)
            
            print(f"📦 Arquivo dividido em {len(chunks)} chunks de {self.chunk_size} linhas")
            
            # 3. Processando chunks SEQUENCIALMENTE
            self._update_progress(translation_id, 30, "Iniciando tradução...")
            translated_chunks = []
            failed_chunks = 0
            
            for i, chunk in enumerate(chunks):
                if translation_data['status'] == 'cancelled':
                    break
                    
                print(f"🔄 Processando chunk {i+1}/{len(chunks)}...")
                
                try:
                    # Pequena pausa entre chunks para não sobrecarregar API
                    if i > 0 and not self.use_mock:
                        time.sleep(1)
                    
                    if self.use_mock:
                        translated_chunk = self._mock_translate_chunk(chunk)
                        time.sleep(0.5)  # Simula processamento
                    else:
                        translated_chunk = self._real_translate_chunk_robust(chunk)
                    
                    translated_chunks.append(translated_chunk)
                    translation_data['chunks_processed'] += 1
                    
                    # Atualiza progresso
                    progress = 30 + ((i + 1) / len(chunks)) * 60
                    self._update_progress(
                        translation_id, 
                        int(progress),
                        f"Traduzindo... ({i + 1}/{len(chunks)} blocos)"
                    )
                    
                    print(f"✅ Chunk {i+1} processado com sucesso")
                    
                except Exception as e:
                    print(f"❌ Chunk {i+1} falhou: {str(e)}")
                    failed_chunks += 1
                    # Fallback: usa conteúdo original
                    translated_chunks.append(chunk)
                    translation_data['chunks_processed'] += 1
                    
                    # Se muitos chunks falharem, para a tradução
                    if failed_chunks > len(chunks) * 0.3:  # 30% de falha
                        raise Exception(f"Muitos chunks falharam: {failed_chunks}/{len(chunks)}")
            
            # 4. Reconstruindo arquivo
            self._update_progress(translation_id, 90, "Montando arquivo final...")
            final_content = '\n\n'.join(translated_chunks)
            
            # 5. Salvando
            translated_filename = file_service.save_translated_file(
                final_content, 
                translation_data['unique_filename']
            )
            
            self._update_progress(translation_id, 100, "Tradução concluída!")
            
            if failed_chunks > 0:
                print(f"⚠️  Tradução concluída com {failed_chunks} chunks com falha (usando texto original)")
            
            translation_data.update({
                'status': 'completed',
                'translated_filename': translated_filename,
                'download_url': f'/download/{translated_filename}',
                'failed_chunks': failed_chunks
            })
            
        except Exception as e:
            print(f"❌ Erro na tradução {translation_id}: {str(e)}")
            self.active_translations[translation_id].update({
                'status': 'error',
                'error': str(e)
            })
        finally:
            try:
                from src.file_service import FileService
                file_service = FileService(Config.UPLOAD_FOLDER)
                file_service.cleanup_file(translation_data['filepath'])
            except:
                pass

    def _split_srt_into_chunks(self, srt_content):
        """Divide SRT em chunks mantendo blocos intactos"""
        blocks = re.split(r'\n\s*\n', srt_content.strip())
        chunks = []
        current_chunk = []
        
        for block in blocks:
            if not block.strip():
                continue
                
            current_chunk.append(block)
            
            # Chunks menores para evitar timeout
            if len(current_chunk) >= self.chunk_size:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

    def _real_translate_chunk_robust(self, chunk_content):
        """Traduz um chunk com retry e timeout robusto"""
        if not self.api_key:
            raise ValueError("Chave API não configurada")
        
        # Configura retry
        retry_strategy = Retry(
            total=2,  # APENAS 2 tentativas
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
        )
        
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """Você é um tradutor profissional de legendas SRT. 
        Sua tarefa é traduzir APENAS o texto dos diálogos, mantendo:
        - Números de sequência intactos
        - Timestamps no formato exato HH:MM:SS,ms --> HH:MM:SS,ms
        - Formatação original
        Não adicione comentários ou explicações."""
        
        # Limita tamanho para evitar timeout
        if len(chunk_content) > 4000:
            print(f"⚠️  Chunk grande ({len(chunk_content)} chars), truncando...")
            chunk_content = chunk_content[:4000] + "\n[...]"
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Traduza para português brasileiro:\n\n{chunk_content}"}
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        try:
            print(f"📤 Enviando chunk ({len(chunk_content)} caracteres)...")
            
            response = session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=(10, 30)  # Timeout menor: 30s
            )
            
            print(f"📥 Resposta recebida: {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"API retornou erro {response.status_code}: {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout: chunk demorou mais de 30 segundos")
        except Exception as e:
            raise Exception(f"Erro na API: {str(e)}")
        finally:
            session.close()

    def _mock_translate_chunk(self, chunk_content):
        """Mock para desenvolvimento"""
        lines = chunk_content.split('\n')
        translated = []
        
        for line in lines:
            line = line.strip()
            if line.isdigit() or '-->' in line or not line:
                translated.append(line)
            else:
                if len(translated) > 0 and ('-->' in translated[-1] or translated[-1].isdigit()):
                    translated.append(f"[TRADUZIDO] {line}")
                else:
                    translated.append(line)
        
        return '\n'.join(translated)

    def _update_progress(self, translation_id, progress, message=""):
        if translation_id in self.active_translations:
            self.active_translations[translation_id]['progress'] = progress
            if message:
                self.active_translations[translation_id]['message'] = message
            print(f"📊 {translation_id}: {progress}% - {message}")

    def get_translation_status(self, translation_id):
        status = self.active_translations.get(translation_id, {})
        if 'chunks_processed' in status and 'total_chunks' in status:
            status['chunks_processed'] = status['chunks_processed']
            status['total_chunks'] = status['total_chunks']
        return status

    def cancel_translation(self, translation_id):
        """Cancela uma tradução em andamento"""
        if translation_id in self.active_translations:
            self.active_translations[translation_id]['status'] = 'cancelled'
            return True
        return False

    # Método de compatibilidade
    def translate(self, text):
        if self.use_mock:
            return self._mock_translate_chunk(text)
        else:
            return self._real_translate_chunk_robust(text)