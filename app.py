"""
SOS Usabilidade - Painel de Registro de Problemas de Interface
Disciplina: Usabilidade, desenvolvimento web, mobile e jogos (0011109)
Aula 09: Persistência com Python, Flask e SQLite

Aplicação Web em Flask integrada com banco SQLite local para registro,
listagem, atualização e exclusão de problemas de usabilidade.
"""

import os
import sqlite3
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    abort
)

DATABASE = 'problemas.db'

# Vocabulários controlados exigidos
CATEGORIAS_PERMITIDAS = {'navegacao', 'formulario', 'feedback', 'acessibilidade', 'outro'}
GRAVIDADES_PERMITIDAS = {'baixa', 'media', 'alta'}

app = Flask(__name__)
# Chave secreta necessária para suporte a sessões e mensagens flash
app.secret_key = 'sos_usabilidade_chave_secreta_dev'


def get_db():
    """
    Abre ou recupera a conexão com o banco de dados SQLite para a requisição atual.
    A conexão é armazenada no contexto 'g' do Flask.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        # Permite acessar colunas por nome como em um dicionário (ex: row['titulo'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """
    Garante o fechamento de todas as conexões abertas com o banco ao encerrar a requisição.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def inicializar_banco():
    """
    Cria a tabela 'problemas' se ela não existir.
    Pode ser executada múltiplas vezes sem apagar dados ou gerar erros.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS problemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            sistema TEXT NOT NULL,
            categoria TEXT NOT NULL,
            gravidade TEXT NOT NULL,
            descricao TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    db.commit()


@app.route('/', methods=['GET'])
def index():
    """
    Rota principal: Lista todos os problemas cadastrados, ordenados do mais recente
    ao mais antigo (id DESC).
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM problemas ORDER BY id DESC')
    problemas = cursor.fetchall()
    return render_template('index.html', problemas=problemas)


@app.route('/problemas', methods=['POST'])
def cadastrar_problema():
    """
    Recebe, valida e persiste um novo problema de usabilidade no banco.
    Aplica validações de campos obrigatórios, vocabulário e sanitização de strings.
    """
    # 1. Obtenção e sanitização de espaços (strip)
    titulo = request.form.get('titulo', '').strip()
    sistema = request.form.get('sistema', '').strip()
    categoria = request.form.get('categoria', '').strip()
    gravidade = request.form.get('gravidade', '').strip()
    descricao = request.form.get('descricao', '').strip()

    # 2. Validações de presença
    if not titulo:
        flash('O campo "Título" é obrigatório e não pode ficar em branco.', 'error')
        return redirect(url_for('index'))
    if len(titulo) > 120:
        flash('O campo "Título" deve ter no máximo 120 caracteres.', 'error')
        return redirect(url_for('index'))
    if not sistema:
        flash('O campo "Sistema" é obrigatório e não pode ficar em branco.', 'error')
        return redirect(url_for('index'))
    if not categoria:
        flash('O campo "Categoria" é obrigatório.', 'error')
        return redirect(url_for('index'))
    if not gravidade:
        flash('O campo "Gravidade" é obrigatório.', 'error')
        return redirect(url_for('index'))
    if not descricao:
        flash('O campo "Descrição" é obrigatório e não pode ficar em branco.', 'error')
        return redirect(url_for('index'))

    # 3. Validações de vocabulário controlado
    if categoria not in CATEGORIAS_PERMITIDAS:
        flash(f'Categoria inválida. Opções aceitas: {", ".join(sorted(CATEGORIAS_PERMITIDAS))}.', 'error')
        return redirect(url_for('index'))

    if gravidade not in GRAVIDADES_PERMITIDAS:
        flash(f'Gravidade inválida. Opções aceitas: {", ".join(sorted(GRAVIDADES_PERMITIDAS))}.', 'error')
        return redirect(url_for('index'))

    # 4. Inserção parametrizada (evita SQL Injection)
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO problemas (titulo, sistema, categoria, gravidade, descricao)
        VALUES (?, ?, ?, ?, ?)
    ''', (titulo, sistema, categoria, gravidade, descricao))
    db.commit()

    flash('Problema de usabilidade cadastrado com sucesso!', 'success')
    # Padrão PRG (Post/Redirect/Get)
    return redirect(url_for('index'))


@app.route('/problemas/<int:id>/editar', methods=['GET', 'POST'])
def editar_problema(id):
    """
    GET: Carrega e exibe o formulário de edição pré-preenchido.
    POST: Valida e aplica a atualização dos dados do problema selecionado.
    """
    db = get_db()
    cursor = db.cursor()

    # Busca o registro pelo ID
    cursor.execute('SELECT * FROM problemas WHERE id = ?', (id,))
    problema = cursor.fetchone()

    # Se não existir, gera HTTP 404
    if problema is None:
        abort(404, description=f'Problema #{id} não foi encontrado no sistema.')

    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        sistema = request.form.get('sistema', '').strip()
        categoria = request.form.get('categoria', '').strip()
        gravidade = request.form.get('gravidade', '').strip()
        descricao = request.form.get('descricao', '').strip()

        # Validações
        if not titulo or len(titulo) > 120 or not sistema or not descricao:
            flash('Preencha todos os campos obrigatórios corretamente.', 'error')
            return redirect(url_for('editar_problema', id=id))

        if categoria not in CATEGORIAS_PERMITIDAS:
            flash('Categoria selecionada é inválida.', 'error')
            return redirect(url_for('editar_problema', id=id))

        if gravidade not in GRAVIDADES_PERMITIDAS:
            flash('Gravidade selecionada é inválida.', 'error')
            return redirect(url_for('editar_problema', id=id))

        # Atualização parametrizada
        cursor.execute('''
            UPDATE problemas
            SET titulo = ?, sistema = ?, categoria = ?, gravidade = ?, descricao = ?
            WHERE id = ?
        ''', (titulo, sistema, categoria, gravidade, descricao, id))
        db.commit()

        flash(f'Problema #{id} atualizado com sucesso!', 'success')
        return redirect(url_for('index'))

    return render_template('editar.html', problema=problema)


@app.route('/problemas/<int:id>/excluir', methods=['POST'])
def excluir_problema(id):
    """
    Remove o problema correspondente do banco de dados SQLite.
    """
    db = get_db()
    cursor = db.cursor()

    # Verifica existência antes da exclusão
    cursor.execute('SELECT id FROM problemas WHERE id = ?', (id,))
    if cursor.fetchone() is None:
        flash(f'Tentativa de exclusão falhou: Problema #{id} não existe.', 'error')
        return redirect(url_for('index'))

    cursor.execute('DELETE FROM problemas WHERE id = ?', (id,))
    db.commit()

    flash(f'Problema #{id} excluído com sucesso.', 'success')
    return redirect(url_for('index'))


@app.errorhandler(404)
def pagina_nao_encontrada(e):
    """Handler customizado para tratar recursos inexistentes (404)."""
    return render_template('index.html', erro_404=str(e)), 404


if __name__ == '__main__':
    # Inicializa o banco de dados dentro do contexto da aplicação antes de subir o servidor
    with app.app_context():
        inicializar_banco()

    # Servidor executado exclusivamente em localhost (127.0.0.1)
    app.run(host='127.0.0.1', port=5000, debug=True)