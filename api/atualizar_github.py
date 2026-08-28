import base64
import os

REPOSITORY = os.environ.get('GITHUB_REPOSITORY', 'DMOS15/ptw-matriz')
BRANCH = os.environ.get('GITHUB_BRANCH', 'main')
JSON_FILES = (
    'dados/solicitantes.json',
    'dados/responsaveis.json',
    'dados/supervisores_altura.json',
    'dados/supervisores_quente.json',
    'dados/supervisores_confinado.json'
)


def commit_jsons(data_dir, message):
    try:
        from github import Github
    except ImportError as error:
        raise RuntimeError('PyGithub não instalado. Adicione as dependências de requirements.txt.') from error
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('GITHUB_TOKEN não configurado na Vercel.')
    repository = Github(token).get_repo(REPOSITORY)
    committed = []
    for path in JSON_FILES:
        source = data_dir / path.split('/', 1)[1]
        if not source.exists():
            continue
        content = source.read_text(encoding='utf-8')
        try:
            current = repository.get_contents(path, ref=BRANCH)
            repository.update_file(path, message, content, current.sha, branch=BRANCH)
        except Exception as error:
            if error.__class__.__name__ != 'UnknownObjectException':
                raise
            repository.create_file(path, message, content, branch=BRANCH)
        committed.append(path)
    return committed
