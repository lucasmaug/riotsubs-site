import re
from werkzeug.utils import secure_filename


class ValidationService:
    """Responsável por validar uploads e conteúdo SRT."""

    def __init__(self, allowed_extensions, max_file_size):
        self.allowed_extensions = allowed_extensions
        self.max_file_size = max_file_size

    def is_file_allowed(self, filename):
        """Verifica se a extensão do arquivo é permitida."""
        return (
            '.' in filename
            and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
        )

    def validate_file_upload(self, uploaded_file):
        """Valida o arquivo enviado pelo usuário."""
        if not uploaded_file:
            raise ValueError('Nenhum arquivo enviado.')

        if not uploaded_file.filename:
            raise ValueError('Nome de arquivo vazio.')

        if not self.is_file_allowed(uploaded_file.filename):
            exts = ', '.join(f'.{e}' for e in self.allowed_extensions)
            raise ValueError(f'Apenas arquivos {exts} são aceitos.')

        # Verifica tamanho sem consumir o stream — lê o fim e volta ao início
        uploaded_file.stream.seek(0, 2)
        size = uploaded_file.stream.tell()
        uploaded_file.stream.seek(0)

        if size > self.max_file_size:
            mb = self.max_file_size / (1024 * 1024)
            raise ValueError(f'Arquivo muito grande. Limite: {mb:.0f}MB.')

        original_filename = uploaded_file.filename
        return secure_filename(original_filename), original_filename

    def validate_srt_content(self, content):
        """
        Valida se o conteúdo segue o formato SRT.
        Verifica: tem linhas suficientes, tem pelo menos um bloco número+timestamp.
        """
        if not content or len(content.strip()) < 10:
            raise ValueError('Arquivo SRT vazio ou muito curto.')

        lines = content.split('\n')

        if len(lines) < 3:
            raise ValueError('Arquivo SRT inválido — linhas insuficientes.')

        # Procura o padrão: número na linha N, timestamp na linha N+1
        # Verifica nas primeiras 30 linhas para não percorrer arquivos enormes
        has_srt_pattern = any(
            line.strip().isdigit()
            and i + 1 < len(lines)
            and re.search(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->', lines[i + 1])
            for i, line in enumerate(lines[:30])
        )

        if not has_srt_pattern:
            raise ValueError(
                'Arquivo não reconhecido como SRT. '
                'Verifique se o arquivo está no formato correto.'
            )

        return True

    def validate_api_response(self, response_text):
        """
        Valida se a resposta da IA é um SRT válido e não texto explicativo.
        Remove markdown que a IA às vezes insere (```srt ... ```).
        """
        if not response_text:
            raise ValueError('Resposta vazia da API.')

        # Remove blocos de código markdown se a IA os inseriu
        text = re.sub(r'```[a-z]*\n?', '', response_text).strip()

        # Remove linhas explicativas antes do primeiro número de bloco
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip().isdigit():
                text = '\n'.join(lines[i:]).strip()
                break

        # Confirma que o resultado ainda parece um SRT
        if not re.search(r'^\d+\s*\n\d{2}:\d{2}', text, re.MULTILINE):
            raise ValueError('A API não retornou um SRT válido.')

        return text
