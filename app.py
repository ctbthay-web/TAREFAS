from datetime import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import locale

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar locale para português brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except locale.Error:
        pass  # Fallback para locale padrão

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

STATUS_CHOICES = ['Pendente', 'Em andamento', 'Aguardando cliente', 'Concluído', 'Cancelado']
PRIORITIES = ['Baixa', 'Média', 'Alta', 'Urgente']
PAYMENT_METHODS = ['Pix', 'Cartão', 'Dinheiro', 'Boleto', 'Transferência']

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(20))
    cnpj = db.Column(db.String(20))
    address = db.Column(db.String(300))
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    email = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='client', cascade='all, delete-orphan')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    responsible = db.Column(db.String(120))
    deadline = db.Column(db.Date)
    priority = db.Column(db.String(20), default='Média')
    status = db.Column(db.String(30), default='Pendente')
    service_value = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50))
    completed_at = db.Column(db.Date)
    notes = db.Column(db.Text)
    access_info = db.Column(db.Text)

@app.template_filter('format_currency')
def format_currency(value):
    """Formata valor monetário no padrão brasileiro"""
    if value is None:
        return 'R$ 0,00'
    try:
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return 'R$ 0,00'

@app.template_filter('format_date')
def format_date(date):
    """Formata data no padrão brasileiro DD/MM/YYYY"""
    if date is None:
        return '-'
    try:
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()
        return date.strftime('%d/%m/%Y')
    except (ValueError, TypeError, AttributeError):
        return '-'

@app.template_filter('format_datetime')
def format_datetime(dt):
    """Formata data e hora no padrão brasileiro"""
    if dt is None:
        return '-'
    try:
        return dt.strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError, AttributeError):
        return '-'

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile/', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_username = request.form.get('username') or current_user.username
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not current_user.check_password(current_password):
            flash('Senha atual incorreta.', 'danger')
            return render_template('profile.html')

        if new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash('O nome de usuário já está em uso.', 'danger')
                return render_template('profile.html')
            current_user.username = new_username

        if new_password or confirm_password:
            if new_password != confirm_password:
                flash('As senhas não coincidem.', 'danger')
                return render_template('profile.html')
            if len(new_password) < 4:
                flash('A senha precisa ter pelo menos 4 caracteres.', 'danger')
                return render_template('profile.html')
            current_user.set_password(new_password)

        db.session.commit()
        flash('Perfil atualizado com sucesso.', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html')

@app.route('/dashboard/')
@login_required
def dashboard():
    clients_count = Client.query.count()
    tasks_count = Task.query.count()
    total_value = db.session.query(db.func.sum(Task.service_value)).scalar() or 0.0
    open_clients_count = db.session.query(db.func.count(db.distinct(Task.client_id))).filter(Task.status != 'Concluído').scalar() or 0
    recent_clients = Client.query.join(Task).filter(Task.status != 'Concluído').order_by(Client.created_at.desc()).distinct().limit(5).all()
    recent_tasks = Task.query.order_by(Task.date_created.desc()).limit(5).all()
    status_summary = {
        status: Task.query.filter_by(status=status).count() for status in STATUS_CHOICES
    }
    max_status_count = max(status_summary.values()) if status_summary.values() else 1
    return render_template('dashboard.html', clients_count=clients_count, tasks_count=tasks_count,
                           total_value=total_value, open_clients_count=open_clients_count,
                           recent_clients=recent_clients, recent_tasks=recent_tasks,
                           status_summary=status_summary, max_status_count=max_status_count)

@app.route('/clients/')
@login_required
def clients():
    search = request.args.get('search', '')
    if search:
        clients = Client.query.filter(Client.full_name.ilike(f'%{search}%') | Client.email.ilike(f'%{search}%')).order_by(Client.created_at.desc()).all()
    else:
        clients = Client.query.order_by(Client.created_at.desc()).all()
    return render_template('clients.html', clients=clients, search=search)

@app.route('/clients/new/', methods=['GET', 'POST'])
@login_required
def new_client():
    if request.method == 'POST':
        client = Client(
            full_name=request.form.get('full_name'),
            cpf=request.form.get('cpf'),
            cnpj=request.form.get('cnpj'),
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            whatsapp=request.form.get('whatsapp'),
            email=request.form.get('email'),
            notes=request.form.get('notes'),
        )
        db.session.add(client)
        db.session.commit()
        flash('Cliente cadastrado com sucesso.', 'success')
        return redirect(url_for('clients'))
    return render_template('client_form.html', client=None)

@app.route('/clients/edit/<int:client_id>/', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        client.full_name = request.form.get('full_name')
        client.cpf = request.form.get('cpf')
        client.cnpj = request.form.get('cnpj')
        client.address = request.form.get('address')
        client.phone = request.form.get('phone')
        client.whatsapp = request.form.get('whatsapp')
        client.email = request.form.get('email')
        client.notes = request.form.get('notes')
        db.session.commit()
        flash('Cliente atualizado com sucesso.', 'success')
        return redirect(url_for('clients'))
    return render_template('client_form.html', client=client)

@app.route('/clients/delete/<int:client_id>/', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash('Cliente excluído com sucesso.', 'success')
    return redirect(url_for('clients'))

@app.route('/tasks/')
@login_required
def tasks():
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    responsible_filter = request.args.get('responsible', '')
    query = Task.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if responsible_filter:
        query = query.filter(Task.responsible.ilike(f'%{responsible_filter}%'))
    tasks = query.order_by(Task.date_created.desc()).all()
    clients = Client.query.order_by(Client.full_name).all()
    return render_template('tasks.html', tasks=tasks, clients=clients,
                           status_filter=status_filter,
                           priority_filter=priority_filter,
                           responsible_filter=responsible_filter,
                           STATUS_CHOICES=STATUS_CHOICES,
                           PRIORITIES=PRIORITIES)

@app.route('/tasks/new/', methods=['GET', 'POST'])
@login_required
def new_task():
    clients = Client.query.order_by(Client.full_name).all()
    if not clients:
        flash('Cadastre um cliente antes de criar uma tarefa.', 'warning')
        return redirect(url_for('clients'))
    if request.method == 'POST':
        task = Task(
            client_id=request.form.get('client_id'),
            description=request.form.get('description'),
            responsible=request.form.get('responsible'),
            deadline=request.form.get('deadline') or None,
            priority=request.form.get('priority'),
            status=request.form.get('status'),
            service_value=float(request.form.get('service_value') or 0),
            payment_method=request.form.get('payment_method'),
            completed_at=request.form.get('completed_at') or None,
            notes=request.form.get('notes'),
            access_info=request.form.get('access_info'),
        )
        if task.completed_at:
            task.completed_at = datetime.strptime(task.completed_at, '%Y-%m-%d').date()
        if task.deadline:
            task.deadline = datetime.strptime(task.deadline, '%Y-%m-%d').date()
        db.session.add(task)
        db.session.commit()
        flash('Tarefa cadastrada com sucesso.', 'success')
        return redirect(url_for('tasks'))
    return render_template('task_form.html', task=None, clients=clients,
                           STATUS_CHOICES=STATUS_CHOICES, PRIORITIES=PRIORITIES,
                           PAYMENT_METHODS=PAYMENT_METHODS)

@app.route('/tasks/edit/<int:task_id>/', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    clients = Client.query.order_by(Client.full_name).all()
    if request.method == 'POST':
        task.client_id = request.form.get('client_id')
        task.description = request.form.get('description')
        task.responsible = request.form.get('responsible')
        task.deadline = request.form.get('deadline') or None
        task.priority = request.form.get('priority')
        task.status = request.form.get('status')
        task.service_value = float(request.form.get('service_value') or 0)
        task.payment_method = request.form.get('payment_method')
        task.completed_at = request.form.get('completed_at') or None
        task.notes = request.form.get('notes')
        task.access_info = request.form.get('access_info')
        if task.completed_at:
            task.completed_at = datetime.strptime(task.completed_at, '%Y-%m-%d').date()
        if task.deadline:
            task.deadline = datetime.strptime(task.deadline, '%Y-%m-%d').date()
        db.session.commit()
        flash('Tarefa atualizada com sucesso.', 'success')
        return redirect(url_for('tasks'))
    return render_template('task_form.html', task=task, clients=clients,
                           STATUS_CHOICES=STATUS_CHOICES, PRIORITIES=PRIORITIES,
                           PAYMENT_METHODS=PAYMENT_METHODS)

@app.route('/tasks/delete/<int:task_id>/', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Tarefa excluída com sucesso.', 'success')
    return redirect(url_for('tasks'))

@app.route('/export/<string:model>/')
@login_required
def export_data(model):
    if model == 'clients':
        data = Client.query.all()
        rows = []
        for c in data:
            rows.append({
                'Nome': c.full_name,
                'CPF': c.cpf,
                'CNPJ': c.cnpj,
                'Endereço': c.address,
                'Telefone': c.phone,
                'WhatsApp': c.whatsapp,
                'E-mail': c.email,
                'Observações': c.notes,
                'Data de cadastro': c.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        df = pd.DataFrame(rows)
        filename = 'clientes_export.xlsx'
    else:
        data = Task.query.all()
        rows = []
        for t in data:
            rows.append({
                'Data de lançamento': t.date_created.strftime('%Y-%m-%d %H:%M'),
                'Cliente': t.client.full_name,
                'Descrição': t.description,
                'Responsável': t.responsible,
                'Prazo': t.deadline.strftime('%Y-%m-%d') if t.deadline else '',
                'Prioridade': t.priority,
                'Status': t.status,
                'Valor do serviço': t.service_value,
                'Forma de pagamento': t.payment_method,
                'Data de conclusão': t.completed_at.strftime('%Y-%m-%d') if t.completed_at else '',
                'Observações': t.notes,
                'Senhas e acessos': t.access_info,
            })
        df = pd.DataFrame(rows)
        filename = 'tarefas_export.xlsx'
    filepath = os.path.join('tmp', filename)
    os.makedirs('tmp', exist_ok=True)
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
