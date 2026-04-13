import os
import re
import time
import uuid


class FileService:
    """Responsável por salvar, ler, normalizar e limpar arquivos SRT."""

    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def save_uploaded_file(self, file, filename):
        """Salva o arquivo enviado com nome único para evitar colisões."""
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f'{unique_id}_{filename}'
        filepath = os.path.join(self.upload_folder, safe_filename)
        file.save(filepath)
        return filepath, safe_filename

    def read_file_content(self, filepath):
        """
        Lê o arquivo tentando os encodings mais comuns em SRTs brasileiros.
        Normaliza o conteúdo logo após a leitura.
        """
        # Ordem: UTF-8 primeiro (mais moderno), depois encodings Windows legados
        encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1', 'iso-8859-1']

        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                # Conteúdo válido: tem texto e não tem caracteres de substituição
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
        - Garante vírgula nos timestamps (padrão SRT oficial)
        """
        # Remove BOM se sobrar após leitura
        content = content.lstrip('\ufeff')

        # Normaliza quebras de linha (Windows CRLF → LF)
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Garante vírgula nos timestamps: 00:01:23.456 → 00:01:23,456
        # Alguns exportadores usam ponto em vez de vírgula
        content = re.sub(
            r'(\d{2}:\d{2}:\d{2})\.(\d{3})',
            r'\1,\2',
            content
        )

        return content

    def save_translated_file(self, content, original_filename):
        """
        Salva o conteúdo traduzido.
        Usa UTF-8 sem BOM — compatível com VLC, MPC-HC e players modernos.
        Normaliza quebras de linha para evitar alertas de segurança no Windows.
        """
        translated_filename = f'traduzido_{original_filename}'
        translated_path = os.path.join(self.upload_folder, translated_filename)

        # Normaliza quebras antes de salvar
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # newline='\n' garante que o arquivo não saia com CRLF duplicado
        with open(translated_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)

        return translated_filename

    def cleanup_file(self, filepath):
        """Remove um arquivo temporário específico."""
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass  # ignora se o arquivo já foi removido

    def cleanup_old_files(self, max_age_hours=24):
        """
        Remove arquivos traduzidos com mais de X horas.
        Chamado automaticamente a cada nova tradução iniciada.
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        for filename in os.listdir(self.upload_folder):
            # Só limpa arquivos traduzidos, não uploads originais em processamento
            if not filename.startswith('traduzido_'):
                continue
            filepath = os.path.join(self.upload_folder, filename)
            try:
                age = now - os.path.getmtime(filepath)
                if age > max_age_seconds:
                    os.remove(filepath)
                    print(f'🗑️  Arquivo antigo removido: {filename}')
            except OSError:
                pass
