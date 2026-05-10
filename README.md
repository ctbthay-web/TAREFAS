# Sistema de Gestão de Tarefas e Clientes

Projeto em Python usando Flask para gerenciamento de clientes, tarefas e controle financeiro básico.

## Recursos

- Cadastro de clientes
- Cadastro de tarefas
- Dashboard com resumo de tarefas, clientes e valor total
- Sistema de status automático
- Área de observações e campo de senhas/acessos
- Login de usuário
- Pesquisa de clientes e filtro de tarefas
- Edição, exclusão e exportação para Excel
- Banco de dados SQLite gerado automaticamente
- Interface moderna com Bootstrap e tema escuro

## Estrutura

- `app.py` - aplicação Flask principal
- `templates/` - arquivos HTML do frontend
- `static/css/style.css` - estilos personalizados
- `requirements.txt` - dependências Python

## Como executar

1. Criar e ativar um ambiente virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Executar a aplicação:

```bash
python app.py
```

4. Acessar no navegador:

```text
http://127.0.0.1:5000/
```

5. Login inicial:

- usuário: `admin`
- senha: `admin123`

## Observações

O banco de dados `database.db` é criado automaticamente na primeira execução. O sistema já está preparado para futuras melhorias e novas funcionalidades.
