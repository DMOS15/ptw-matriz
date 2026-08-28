import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from processar_dados import DATA_DIR, _history, _json_error, _store_upload, _token_ok, process_matrix

app = Flask(__name__)
CORS(app)


def atualizar_github(data_dir, message):
	from github import Github
	token = os.environ.get('GITHUB_TOKEN')
	if not token:
		raise RuntimeError('GITHUB_TOKEN não configurado na Vercel.')
	repository = Github(token).get_repo(os.environ.get('GITHUB_REPOSITORY', 'DMOS15/ptw-matriz'))
	branch = os.environ.get('GITHUB_BRANCH', 'main')
	for path in ('dados/solicitantes.json', 'dados/responsaveis.json', 'dados/supervisores_altura.json', 'dados/supervisores_quente.json', 'dados/supervisores_confinado.json'):
		source = data_dir / path.split('/', 1)[1]
		if source.exists():
			current = repository.get_contents(path, ref=branch)
			repository.update_file(path, message, source.read_text(encoding='utf-8'), current.sha, branch=branch)


@app.route('/api/upload_supervisores', methods=['POST'])
def upload_supervisores():
	if not _token_ok():
		return _json_error('Acesso administrativo necessário.', 401)
	arquivo = request.files.get('arquivo')
	try:
		with tempfile.TemporaryDirectory() as folder:
			source = Path(folder) / (arquivo.filename if arquivo else 'upload.xlsx')
			filename = _store_upload(arquivo, source)
			count, message = process_matrix(source, False, True)
			atualizar_github(DATA_DIR, 'Atualiza dados PTW: supervisores')
		_history('supervisores', filename, True, message, count)
		return jsonify({'sucesso': True, 'mensagem': f'Concluído! {message}', 'registros': count})
	except Exception as error:
		_history('supervisores', arquivo.filename if arquivo else '', False, str(error))
		status = 400 if isinstance(error, ValueError) else 500
		return _json_error(str(error), status)

handler = app
