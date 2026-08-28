// ============================================================
// SCRIPT PRINCIPAL - MATRIZ PTW
// ============================================================

const BASE_URL = './dados/';
const API_URL = window.location.protocol === 'file:' ? 'http://localhost:5000' : window.location.origin;
const ADMIN_TOKEN_KEY = 'ptw_admin_token';

async function verificarServidor() {
    try {
        const resposta = await fetch(`${API_URL}/api/status`, { cache: 'no-store' });
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();
        console.info('[PTW] Servidor online:', dados.status, API_URL);
        return true;
    } catch (erro) {
        console.error('[PTW] Servidor indisponível em', API_URL, erro);
        return false;
    }
}

// ============================================================
// FUNÇÃO PARA CARREGAR DADOS
// ============================================================
async function carregarJSON(arquivo) {
    try {
        const resposta = await fetch(BASE_URL + arquivo);
        if (!resposta.ok) throw new Error(`Erro ao carregar ${arquivo}: ${resposta.status}`);
        return await resposta.json();
    } catch (erro) {
        console.error('Erro no carregamento:', erro);
        return [];
    }
}

// ============================================================
// ATUALIZAR DATA NO RODAPÉ
// ============================================================
function atualizarData() {
    const agora = new Date();
    const dataFormatada = agora.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    const el = document.getElementById('data-atualizacao');
    if (el) el.textContent = dataFormatada;
}

// ============================================================
// BOTÃO ATUALIZAR
// ============================================================
function atualizarDados() {
    if (confirm('Recarregar os dados dos arquivos JSON?')) {
        window.location.reload();
    }
}

// ============================================================
// FUNÇÃO DE ORDENAÇÃO ALFABÉTICA
// ============================================================
function ordenarPorNome(dados) {
    return dados.sort((a, b) => {
        const nomeA = (a.nome || '').toLowerCase();
        const nomeB = (b.nome || '').toLowerCase();
        return nomeA.localeCompare(nomeB);
    });
}

// ============================================================
// EXTRAIR ÁREAS ÚNICAS
// ============================================================
function extrairAreas(dados, campoAreas) {
    const areasSet = new Set();
    dados.forEach(item => {
        const areas = item[campoAreas] || [];
        areas.forEach(area => areasSet.add(area));
    });
    return Array.from(areasSet).sort();
}

// ============================================================
// EXTRAIR CARGOS ÚNICOS
// ============================================================
function extrairCargos(dados) {
    const cargosSet = new Set();
    dados.forEach(item => {
        if (item.cargo) {
            cargosSet.add(item.cargo);
        }
    });
    return Array.from(cargosSet).sort();
}

// ============================================================
// POPULAR SELECT
// ============================================================
function popularSelect(selectId, itens, labelTodos = 'TODAS AS ÁREAS') {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = `<option value="TODAS">${labelTodos}</option>`;
    itens.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        select.appendChild(opt);
    });
}

// ============================================================
// GERAR QR CODE
// ============================================================
function gerarQRCode(qrId) {
    const url = window.location.href;
    const qrApi = `https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=${encodeURIComponent(url)}`;
    const qrImg = document.getElementById(qrId);
    if (qrImg) {
        qrImg.src = qrApi;
        qrImg.alt = 'QR Code';
    }
}

// ============================================================
// EXECUTAR QUANDO A PÁGINA CARREGAR
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    atualizarData();
    verificarServidor();

    // Gera QR Codes
    if (document.getElementById('qrIndex')) gerarQRCode('qrIndex');
    if (document.getElementById('qrSolicitantes')) gerarQRCode('qrSolicitantes');
    if (document.getElementById('qrResponsaveis')) gerarQRCode('qrResponsaveis');
    if (document.getElementById('qrSupervisores')) gerarQRCode('qrSupervisores');

    // ============================================================
    // PÁGINA: SOLICITANTES
    // ============================================================
    if (document.getElementById('tabela-solicitantes')) {
        carregarJSON('solicitantes.json').then(dados => {
            if (!dados || dados.length === 0) {
                document.getElementById('tabela-solicitantes').innerHTML = 
                    '<tr><td colspan="7" style="text-align:center;padding:30px;color:#e74c3c;">Nenhum solicitante encontrado.</td></tr>';
                return;
            }

            dados = ordenarPorNome(dados);

            const areas = extrairAreas(dados, 'areas');
            const cargos = extrairCargos(dados);

            popularSelect('filtroAreaSolicitantes', areas);
            popularSelect('filtroCargoSolicitantes', cargos, 'TODOS OS CARGOS');

            const inputNome = document.getElementById('filtroNomeSolicitantes');
            const selectArea = document.getElementById('filtroAreaSolicitantes');
            const selectCargo = document.getElementById('filtroCargoSolicitantes');

            function renderizarSolicitantes() {
                let filtrados = [...dados];

                if (inputNome.value.trim() !== '') {
                    const termo = inputNome.value.toLowerCase().trim();
                    filtrados = filtrados.filter(item => 
                        (item.nome || '').toLowerCase().includes(termo)
                    );
                }

                if (selectArea.value !== 'TODAS') {
                    filtrados = filtrados.filter(item => {
                        const areas = item.areas || [];
                        return areas.some(area => area === selectArea.value);
                    });
                }

                if (selectCargo.value !== 'TODAS') {
                    filtrados = filtrados.filter(item => 
                        (item.cargo || '') === selectCargo.value
                    );
                }

                const tbody = document.getElementById('tabela-solicitantes');
                tbody.innerHTML = '';

                if (filtrados.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#7f8c8d;">Nenhum resultado encontrado</td></tr>';
                    return;
                }

                filtrados.forEach(item => {
                    const statusClass = ['NO PRAZO', 'APROVADO'].includes(item.status) ? 'status-valido' : 'status-vencido';
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${item.nome || '-'}</strong></td>
                        <td>${item.cargo || '-'}</td>
                        <td>${item.area || '-'}</td>
                        <td><span class="${statusClass}">${item.status || '-'}</span></td>
                        <td>${item.vence_em || '-'}</td>
                        <td><div class="areas-lista">${(item.areas || []).map(a => `<span>${a}</span>`).join(' ')}</div></td>
                    `;
                    tbody.appendChild(tr);
                });

                document.getElementById('contador-solicitantes').textContent = `${filtrados.length} registros`;
            }

            inputNome.addEventListener('input', renderizarSolicitantes);
            selectArea.addEventListener('change', renderizarSolicitantes);
            selectCargo.addEventListener('change', renderizarSolicitantes);
            renderizarSolicitantes();
        });
    }

    // ============================================================
    // PÁGINA: RESPONSÁVEIS POR ÁREA
    // ============================================================
    if (document.getElementById('tabela-responsaveis')) {
        carregarJSON('responsaveis.json').then(dados => {
            if (!dados || dados.length === 0) {
                document.getElementById('tabela-responsaveis').innerHTML = 
                    '<tr><td colspan="3" style="text-align:center;padding:30px;color:#e74c3c;">Nenhum responsável encontrado.</td></tr>';
                return;
            }

            dados = ordenarPorNome(dados);

            const areas = extrairAreas(dados, 'areas');
            popularSelect('filtroAreaResponsaveis', areas);

            const inputNome = document.getElementById('filtroNomeResponsaveis');
            const selectArea = document.getElementById('filtroAreaResponsaveis');

            function renderizarResponsaveis() {
                let filtrados = [...dados];

                if (inputNome.value.trim() !== '') {
                    const termo = inputNome.value.toLowerCase().trim();
                    filtrados = filtrados.filter(item => 
                        (item.nome || '').toLowerCase().includes(termo)
                    );
                }

                if (selectArea.value !== 'TODAS') {
                    filtrados = filtrados.filter(item => {
                        const areas = item.areas || [];
                        return areas.some(area => area === selectArea.value);
                    });
                }

                const tbody = document.getElementById('tabela-responsaveis');
                tbody.innerHTML = '';

                if (filtrados.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:30px;color:#7f8c8d;">Nenhum resultado encontrado</td></tr>';
                    return;
                }

                filtrados.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${item.nome || '-'}</strong></td>
                        <td>${item.cargo || '-'}</td>
                        <td><div class="areas-lista">${(item.areas || []).map(a => `<span>${a}</span>`).join(' ')}</div></td>
                    `;
                    tbody.appendChild(tr);
                });

                document.getElementById('contador-responsaveis').textContent = `${filtrados.length} registros`;
            }

            inputNome.addEventListener('input', renderizarResponsaveis);
            selectArea.addEventListener('change', renderizarResponsaveis);
            renderizarResponsaveis();
        });
    }

    // ============================================================
    // PÁGINA: SUPERVISORES
    // ============================================================
    if (document.getElementById('tabela-supervisores')) {
        Promise.all([
            carregarJSON('supervisores_altura.json'),
            carregarJSON('supervisores_quente.json'),
            carregarJSON('supervisores_confinado.json')
        ]).then(([altura, quente, confinado]) => {
            
            const dadosMap = {
                'altura': ordenarPorNome(altura || []),
                'quente': ordenarPorNome(quente || []),
                'confinado': ordenarPorNome(confinado || [])
            };

            let abaAtual = 'altura';

            function renderizarSupervisores(aba) {
                const dados = dadosMap[aba] || [];
                const tbody = document.getElementById('tabela-supervisores');
                const inputNome = document.getElementById('filtroNomeSupervisores');
                const selectArea = document.getElementById('filtroAreaSupervisores');

                if (!dados || dados.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:30px;color:#e74c3c;">Nenhum supervisor encontrado.</td></tr>';
                    return;
                }

                const areas = extrairAreas(dados, 'areas');
                popularSelect('filtroAreaSupervisores', areas);

                function renderizar() {
                    let filtrados = [...dados];

                    if (inputNome.value.trim() !== '') {
                        const termo = inputNome.value.toLowerCase().trim();
                        filtrados = filtrados.filter(item => 
                            (item.nome || '').toLowerCase().includes(termo)
                        );
                    }

                    if (selectArea.value !== 'TODAS') {
                        filtrados = filtrados.filter(item => {
                            const areas = item.areas || [];
                            return areas.some(area => area === selectArea.value);
                        });
                    }

                    tbody.innerHTML = '';

                    if (filtrados.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:30px;color:#7f8c8d;">Nenhum resultado encontrado</td></tr>';
                        return;
                    }

                    filtrados.forEach(item => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td><strong>${item.nome || '-'}</strong></td>
                            <td>${item.cargo || '-'}</td>
                            <td><div class="areas-lista">${(item.areas || []).map(a => `<span>${a}</span>`).join(' ')}</div></td>
                        `;
                        tbody.appendChild(tr);
                    });

                    document.getElementById('contador-supervisores').textContent = `${filtrados.length} registros`;
                }

                const novoInput = inputNome.cloneNode(true);
                const novoSelect = selectArea.cloneNode(true);
                inputNome.parentNode.replaceChild(novoInput, inputNome);
                selectArea.parentNode.replaceChild(novoSelect, selectArea);

                document.getElementById('filtroNomeSupervisores').addEventListener('input', renderizar);
                document.getElementById('filtroAreaSupervisores').addEventListener('change', renderizar);
                renderizar();
            }

            document.querySelectorAll('.aba').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.aba').forEach(b => b.classList.remove('ativa'));
                    this.classList.add('ativa');
                    abaAtual = this.dataset.aba;
                    renderizarSupervisores(abaAtual);
                });
            });

            renderizarSupervisores('altura');
        });
    }
});

// ============================================================
// FUNÇÕES DO MODAL DE UPLOAD
// ============================================================

let arquivoSelecionado = null;
let tipoUpload = '';

const nomesArquivos = {
    'treinamentos': 'Treinamentos obrigatórios (SHE-QUALID).xlsx',
    'responsaveis': 'SHE 10 - B Work Permit Systems-Responsibility.xlsx',
    'supervisores': 'SHE 10 - B Work Permit Systems-Responsibility.xlsx',
    'matriz': 'SHE 10 - B Work Permit Systems-Responsibility.xlsx'
};

const descricoes = {
    'treinamentos': 'Selecione o arquivo Excel de treinamentos para atualizar a lista de Solicitantes:',
    'responsaveis': 'Selecione o arquivo Excel com a aba "RESPONSAVEIS DE AREA" para atualizar os responsáveis:',
    'supervisores': 'Selecione o arquivo Excel com as abas de supervisores para atualizar a lista:',
    'matriz': 'Selecione o arquivo Excel completo com todas as abas de responsáveis e supervisores:'
};

const titulos = {
    'treinamentos': '📤 Upload Treinamentos (Solicitantes)',
    'responsaveis': '📤 Upload Responsáveis por Área',
    'supervisores': '📤 Upload Supervisores',
    'matriz': '📤 Upload Matriz Completa'
};

function abrirModalUpload(tipo) {
    tipoUpload = tipo;
    
    document.getElementById('modalTitulo').textContent = titulos[tipo] || '📤 Upload Excel';
    document.getElementById('modalDescricao').textContent = descricoes[tipo] || 'Selecione o arquivo Excel para atualizar os dados:';
    document.getElementById('nomeArquivoEsperado').textContent = nomesArquivos[tipo] || 'Arquivo Excel';
    
    document.getElementById('modalUpload').style.display = 'flex';
    document.getElementById('uploadLoading').style.display = 'none';
    document.getElementById('uploadError').style.display = 'none';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('btnEnviar').disabled = true;
    arquivoSelecionado = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadArea').classList.remove('has-file');
}

function fecharModalUpload() {
    document.getElementById('modalUpload').style.display = 'none';
}

document.addEventListener('click', function(event) {
    const modal = document.getElementById('modalUpload');
    if (event.target === modal) {
        fecharModalUpload();
    }
});

// ============================================================
// CONFIGURAÇÃO DO UPLOAD
// ============================================================

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');

if (uploadArea) {
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
}

if (fileInput) {
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            processarArquivoSelecionado(e.target.files[0]);
        }
    });
}

if (uploadArea) {
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            processarArquivoSelecionado(e.dataTransfer.files[0]);
        }
    });
}

function processarArquivoSelecionado(file) {
    const extensao = file.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls'].includes(extensao)) {
        document.getElementById('uploadError').textContent = '⚠️ Selecione um arquivo Excel (.xlsx ou .xls)';
        document.getElementById('uploadError').style.display = 'block';
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
        document.getElementById('uploadError').textContent = '⚠️ Arquivo muito grande (máximo 50MB)';
        document.getElementById('uploadError').style.display = 'block';
        return;
    }
    
    arquivoSelecionado = file;
    
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const tamanho = (file.size / 1024 / 1024).toFixed(2);
    fileName.textContent = `📄 ${file.name} (${tamanho} MB)`;
    fileInfo.style.display = 'block';
    uploadArea.classList.add('has-file');
    
    document.getElementById('btnEnviar').disabled = false;
    document.getElementById('uploadError').style.display = 'none';
}

// ============================================================
// ENVIAR ARQUIVO PARA O SERVIDOR
// ============================================================

function enviarArquivo() {
    if (!arquivoSelecionado) {
        document.getElementById('uploadError').textContent = '⚠️ Selecione um arquivo primeiro!';
        document.getElementById('uploadError').style.display = 'block';
        return;
    }
    
    const loading = document.getElementById('uploadLoading');
    const error = document.getElementById('uploadError');
    const btnEnviar = document.getElementById('btnEnviar');
    
    loading.style.display = 'block';
    loading.textContent = '⏳ Enviando e processando arquivo... Aguarde!';
    error.style.display = 'none';
    btnEnviar.disabled = true;
    
    const formData = new FormData();
    formData.append('arquivo', arquivoSelecionado);
    
    const rotas = {
        'treinamentos': '/api/upload_treinamentos',
        'responsaveis': '/api/upload_responsaveis',
        'supervisores': '/api/upload_supervisores',
        'matriz': '/api/upload_matriz'
    };
    const rota = rotas[tipoUpload] || '/api/upload_treinamentos';
    
    verificarServidor().then(servidorOnline => {
        if (!servidorOnline) {
            throw new Error('Servidor indisponível. Execute iniciar_servidor.bat e abra o sistema por http://localhost:5000.');
        }
        return fetch(`${API_URL}${rota}`, {
            method: 'POST',
            headers: { 'X-Admin-Token': sessionStorage.getItem(ADMIN_TOKEN_KEY) || '' },
            body: formData
        });
    }).then(async response => {
        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error(`Resposta inválida do servidor (HTTP ${response.status}).`);
        }
        if (!response.ok) {
            throw new Error(data.mensagem || `Servidor respondeu com HTTP ${response.status}.`);
        }
        return data;
    }).then(data => {
        if (!data.sucesso) throw new Error(data.mensagem || 'O servidor não conseguiu processar o arquivo.');
        loading.style.display = 'none';
        btnEnviar.disabled = false;
        alert('✅ ' + data.mensagem);
        fecharModalUpload();
        window.location.reload();
    }).catch(err => {
        loading.style.display = 'none';
        btnEnviar.disabled = false;
        error.textContent = `❌ ${err.message || 'Erro ao enviar arquivo.'}`;
        error.style.display = 'block';
        console.error('[PTW] Falha no upload:', err);
    });
}