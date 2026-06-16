import os
import re
import time
import uuid


# Sufixos por código de idioma (espelha o frontend)
LANG_SUFFIX = {
    'pt-br': '-pt-br',
    'pt-pt': '-pt-pt',
    'en':    '-en',
    'es':    '-es',
}


class FileService:
    """Responsável por salvar, ler, normalizar e limpar arquivos SRT."""

    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def save_uploaded_file(self, file, filename):
        """Salva o arquivo enviado com nome único para evitar colisões."""
        unique_id    = uuid.uuid4().hex[:8]
        safe_filename = f'{unique_id}_{filename}'
        filepath     = os.path.join(self.upload_folder, safe_filename)
        file.save(filepath)
        return filepath, safe_filename

    def read_file_content(self, filepath):
        """
        Lê o arquivo tentando os encodings mais comuns em SRTs.
        Normaliza o conteúdo logo após a leitura.
        """
        encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1', 'iso-8859-1']

        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                if content and '\ufffd' not in content and len(content.strip()) > 0:
                    return self._normalize_srt(content)
            except UnicodeDecodeError:
                continue

        raise ValueError(
            'Não foi possível ler o arquivo. '
            'Salve o .srt como UTF-8 e tente novamente.'
        )

    def _normalize_srt(self, content):
        """
        Normaliza um SRT para o formato padrão:
        - Remove BOM
        - Padroniza quebras de linha
        - Garante vírgula nos timestamps
        """
        content = content.lstrip('\ufeff')
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        content = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', content)
        return content

    def save_translated_file(self, content, original_filename, lang='pt-br'):
        """
        Salva o conteúdo traduzido com nome que reflete o idioma.

        Exemplo:
          original_filename = 'Euphoria.S03E01.XviD.srt'
          lang = 'pt-br'
          → resultado = 'Euphoria.S03E01.XviD-pt-br.srt'
        """
        suffix = LANG_SUFFIX.get(lang, f'-{lang}')
        dot_idx = original_filename.rfind('.')
        if dot_idx == -1:
            base, ext = original_filename, '.srt'
        else:
            base = original_filename[:dot_idx]
            ext  = original_filename[dot_idx:]

        translated_filename = f'{base}{suffix}{ext}'
        translated_path     = os.path.join(self.upload_folder, translated_filename)

        content = content.replace('\r\n', '\n').replace('\r', '\n')
        with open(translated_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)

        return translated_filename

    def cleanup_file(self, filepath):
        """Remove um arquivo temporário específico."""
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass

    def cleanup_old_files(self, max_age_hours=24):
        """
        Remove arquivos com mais de X horas.
        Chamado automaticamente a cada nova tradução iniciada.
        """
        now            = time.time()
        max_age_seconds = max_age_hours * 3600

        for filename in os.listdir(self.upload_folder):
            filepath = os.path.join(self.upload_folder, filename)
            try:
                age = now - os.path.getmtime(filepath)
                if age > max_age_seconds:
                    os.remove(filepath)
                    print(f'🗑️  Arquivo antigo removido: {filename}')
            except OSError:
                pass