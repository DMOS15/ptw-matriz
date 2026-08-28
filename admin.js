const API_URL = window.PTW_API_URL || (
    window.location.hostname === 'localhost' || window.location.protocol === 'file:'
        ? 'http://localhost:5000/api'
        : '/api'
);
const IS_GITHUB_PAGES = window.location.hostname.endsWith('.github.io');
const tokenStorageKey = 'ptw_admin_token';
const uploadRoutes = {
    treinamentos: '/api/upload_treinamentos',
    matriz: '/api/upload_matriz'
};

const loginPanel = document.getElementById('loginPanel');
const adminPanel = document.getElementById('adminPanel');
const loginError = document.getElementById('loginError');
const adminError = document.getElementById('adminError');
const adminFeedback = document.getElementById('adminFeedback');

function obterToken() {
    return sessionStorage.getItem(tokenStorageKey);
}

function mensagemServidorIndisponivel() {
    if (IS_GITHUB_PAGES && !window.PTW_API_URL) {
        return 'O site oficial é apenas a interface. Para atualizar dados, execute o servidor local e abra http://localhost:5000/admin.html, ou configure uma API Flask pública em window.PTW_API_URL.';
    }
    return 'Servidor indisponível. Execute iniciar_servidor.bat e abra http://localhost:5000/admin.html.';
}

function exibirPainelAdmin() {
    loginPanel.hidden = true;
    adminPanel.hidden = false;
    carregarHistorico();
}

function mostrarErro(elemento, mensagem) {
    elemento.textContent = mensagem;
    elemento.hidden = false;
}

function limparMensagens() {
    loginError.hidden = true;
    adminError.hidden = true;
    adminFeedback.hidden = true;
}

async function fazerLogin(event) {
    event.preventDefault();
    limparMensagens();
    const pin = document.getElementById('pinInput').value;

    try {
        if (IS_GITHUB_PAGES && !window.PTW_API_URL) {
            throw new Error(mensagemServidorIndisponivel());
        }
        const servidor = await fetch(`${API_URL}/status`, { cache: 'no-store' });
        if (!servidor.ok) throw new Error(`Servidor respondeu com HTTP ${servidor.status}.`);
        console.info('[PTW] Servidor online:', API_URL);
        const resposta = await fetch(`${API_URL}/admin/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin })
        });
        const dados = await resposta.json();
        if (!resposta.ok || !dados.sucesso) throw new Error(dados.mensagem || 'Não foi possível entrar.');
        sessionStorage.setItem(tokenStorageKey, dados.token);
        document.getElementById('pinInput').value = '';
        exibirPainelAdmin();
    } catch (erro) {
        console.error('[PTW] Falha na conexão/login:', erro);
        const mensagem = erro instanceof TypeError
            ? mensagemServidorIndisponivel()
            : erro.message;
        mostrarErro(loginError, `❌ ${mensagem}`);
    }
}

function configurarArquivos() {
    document.querySelectorAll('.admin-file').forEach(input => {
        input.addEventListener('change', () => {
            const tipo = input.dataset.tipo;
            const arquivo = input.files[0];
            const nome = document.querySelector(`[data-arquivo="${tipo}"]`);
            const botao = document.querySelector(`.admin-upload-button[data-tipo="${tipo}"]`);
            nome.textContent = arquivo ? `${arquivo.name} (${(arquivo.size / 1024 / 1024).toFixed(2)} MB)` : 'Nenhum arquivo selecionado';
            botao.disabled = !arquivo;
        });
    });

    document.querySelectorAll('.admin-upload-button').forEach(botao => {
        botao.addEventListener('click', () => enviarArquivo(botao.dataset.tipo));
    });
}

async function enviarArquivo(tipo) {
    const input = document.querySelector(`.admin-file[data-tipo="${tipo}"]`);
    const arquivo = input.files[0];
    if (!arquivo) return;

    limparMensagens();
    adminFeedback.textContent = '⏳ Enviando e processando arquivo...';
    adminFeedback.hidden = false;
    document.querySelectorAll('.admin-upload-button').forEach(botao => botao.disabled = true);

    const dados = new FormData();
    dados.append('arquivo', arquivo);

    try {
        if (IS_GITHUB_PAGES && !window.PTW_API_URL) {
            throw new Error(mensagemServidorIndisponivel());
        }
        const servidor = await fetch(`${API_URL}/status`, { cache: 'no-store' });
        if (!servidor.ok) throw new Error(`Servidor respondeu com HTTP ${servidor.status}.`);
        console.info('[PTW] Servidor online para upload:', API_URL);
        const rota = uploadRoutes[tipo].replace(/^\/api/, '');
        const resposta = await fetch(`${API_URL}${rota}`, {
            method: 'POST',
            headers: { 'X-Admin-Token': obterToken() },
            body: dados
        });
        const resultado = await resposta.json();
        if (resposta.status === 401) {
            sessionStorage.removeItem(tokenStorageKey);
            loginPanel.hidden = false;
            adminPanel.hidden = true;
            throw new Error('Sessão expirada. Informe o PIN novamente.');
        }
        if (!resposta.ok || !resultado.sucesso) throw new Error(resultado.mensagem || 'Falha ao processar o arquivo.');
        adminFeedback.textContent = `✅ ${resultado.mensagem}`;
        input.value = '';
        document.querySelector(`[data-arquivo="${tipo}"]`).textContent = 'Nenhum arquivo selecionado';
        carregarHistorico();
    } catch (erro) {
        adminFeedback.hidden = true;
        console.error('[PTW] Falha no upload:', erro);
        const mensagem = erro instanceof TypeError
            ? mensagemServidorIndisponivel()
            : erro.message;
        mostrarErro(adminError, `❌ ${mensagem || 'Erro ao enviar arquivo.'}`);
    } finally {
        document.querySelectorAll('.admin-upload-button').forEach(botao => {
            botao.disabled = !document.querySelector(`.admin-file[data-tipo="${botao.dataset.tipo}"]`).files[0];
        });
    }
}

async function carregarHistorico() {
    const tabela = document.getElementById('historyTable');
    try {
        const resposta = await fetch(`${API_URL}/admin/historico`, {
            headers: { 'X-Admin-Token': obterToken() }
        });
        if (!resposta.ok) throw new Error('Não foi possível carregar o histórico.');
        const historico = await resposta.json();
        tabela.innerHTML = historico.length ? historico.map(item => `
            <tr>
                <td>${new Date(item.data).toLocaleString('pt-BR')}</td>
                <td>${item.tipo}</td>
                <td>${item.arquivo || '-'}</td>
                <td><span class="${item.sucesso ? 'status-valido' : 'status-vencido'}">${item.sucesso ? 'Sucesso' : 'Erro'}</span></td>
                <td>${item.mensagem}</td>
            </tr>`).join('') : '<tr><td colspan="5" class="history-empty">Nenhuma atualização registrada.</td></tr>';
    } catch (erro) {
        tabela.innerHTML = `<tr><td colspan="5" class="history-empty">${erro.message}</td></tr>`;
    }
}

document.getElementById('loginForm').addEventListener('submit', fazerLogin);
document.getElementById('logoutButton').addEventListener('click', () => {
    sessionStorage.removeItem(tokenStorageKey);
    adminPanel.hidden = true;
    loginPanel.hidden = false;
});
document.getElementById('refreshHistory').addEventListener('click', carregarHistorico);
configurarArquivos();
if (obterToken()) exibirPainelAdmin();
