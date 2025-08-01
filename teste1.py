# coding: utf-8
import kivy


import hashlib
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta

from kivy.app import App
from kivy.core.window import Window
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle

# Global Definitions
DATABASE_NAME = "infinity_park_215.db"
APP_NAME = "Infinity Park 215"
ASSETS_PATH = "assets"  # Relative path for assets
LOGO_FILE = os.path.join(ASSETS_PATH, "logo_infinity_park_215.png")

# Color Palette
COLOR_PRIMARY = get_color_from_hex("#1E88E5")  # Vibrant Blue
COLOR_SECONDARY = get_color_from_hex("#FFC107")  # Amber Yellow
COLOR_ACCENT = get_color_from_hex("#4CAF50")  # Green
COLOR_BACKGROUND = get_color_from_hex("#F5F5F5")  # Light Gray
COLOR_TEXT_DARK = get_color_from_hex("#D3D3D3")  # Grey
COLOR_TEXT_LIGHT = get_color_from_hex("#FFFFFF")  # White
COLOR_DISABLED = get_color_from_hex("#BDBDBD")  # Gray for disabled

# --- Database Functions ---

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # To access columns by name
    return conn

def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ticket Types Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipos_ingressos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        descricao TEXT,
        preco_base REAL NOT NULL,
        idade_minima INTEGER DEFAULT 0,
        idade_maxima INTEGER DEFAULT 120,
        ativo INTEGER DEFAULT 1 -- 1 for TRUE, 0 for FALSE
    );
    """)

    # Visitors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visitantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cpf TEXT UNIQUE NOT NULL,
        nome_completo TEXT NOT NULL,
        data_nascimento TEXT NOT NULL, -- Format YYYY-MM-DD
        altura_cm INTEGER,
        email TEXT UNIQUE NOT NULL,
        telefone TEXT,
        restricoes_medicas TEXT,
        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Attractions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS atracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        descricao_curta TEXT,
        descricao_detalhada TEXT,
        capacidade_por_ciclo INTEGER NOT NULL,
        duracao_ciclo_minutos INTEGER,
        altura_minima_cm INTEGER,
        altura_maxima_cm INTEGER,
        idade_minima_anos INTEGER,
        acompanhante_obrigatorio_ate_idade INTEGER,
        tipo_atracao TEXT, -- Ex: Radical, Familiar, Infantil, Aquatica, Show
        localizacao_mapa TEXT,
        local_image_path TEXT, -- Path to local image
        status TEXT DEFAULT "Operacional", -- Operacional, Manutencao Programada, etc.
        data_ultima_manutencao TEXT, -- Format YYYY-MM-DD
        proxima_manutencao_programada TEXT, -- Format YYYY-MM-DD
        nivel_emocao TEXT, -- Baixo, Medio, Alto
        acessibilidade TEXT
    );
    """)

    # Employees Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cpf TEXT UNIQUE NOT NULL,
        nome_completo TEXT NOT NULL,
        data_nascimento TEXT, -- Format YYYY-MM-DD
        cargo TEXT NOT NULL,
        departamento TEXT,
        turno TEXT, -- Manha, Tarde, Noite, Integral
        data_admissao TEXT NOT NULL, -- Format YYYY-MM-DD
        data_desligamento TEXT, -- Format YYYY-MM-DD
        salario REAL,
        email_corporativo TEXT UNIQUE,
        telefone_contato TEXT,
        status TEXT DEFAULT "Ativo" -- Ativo, Inativo, Ferias, Licenca
    );
    """)

    # System Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios_sistema (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_visitante INTEGER NULL UNIQUE,
        id_funcionario INTEGER NULL UNIQUE,
        username TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        tipo_perfil TEXT NOT NULL DEFAULT "Comum", -- Comum, Administrador, Operador
        email_recuperacao TEXT NOT NULL UNIQUE,
        ativo INTEGER DEFAULT 1, -- 1 for TRUE, 0 for FALSE
        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
        ultimo_login TEXT,
        FOREIGN KEY (id_visitante) REFERENCES visitantes(id) ON DELETE SET NULL,
        FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id) ON DELETE SET NULL
    );
    """)

    # Ticket Purchases Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras_ingressos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario_sistema INTEGER NOT NULL,
        id_visitante_responsavel INTEGER NULL, -- Can be null if the user is not a registered visitor
        data_compra TEXT DEFAULT CURRENT_TIMESTAMP,
        valor_total_compra REAL NOT NULL,
        metodo_pagamento TEXT,
        status_pagamento TEXT DEFAULT "Pendente", -- Pendente, Aprovado, Recusado
        codigo_transacao TEXT UNIQUE,
        FOREIGN KEY (id_usuario_sistema) REFERENCES usuarios_sistema(id),
        FOREIGN KEY (id_visitante_responsavel) REFERENCES visitantes(id)
    );
    """)

    # Ticket Purchase Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_compra_ingressos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_compra_ingresso INTEGER NOT NULL,
        id_tipo_ingresso INTEGER NOT NULL,
        quantidade INTEGER NOT NULL DEFAULT 1,
        preco_unitario_cobrado REAL NOT NULL,
        data_utilizacao_prevista TEXT NOT NULL, -- Format YYYY-MM-DD
        codigo_ingresso_unico TEXT UNIQUE NOT NULL,
        status_ingresso TEXT DEFAULT "Nao Utilizado", -- Nao Utilizado, Utilizado, Cancelado
        id_visitante_portador INTEGER NULL,
        FOREIGN KEY (id_compra_ingresso) REFERENCES compras_ingressos(id) ON DELETE CASCADE,
        FOREIGN KEY (id_tipo_ingresso) REFERENCES tipos_ingressos(id),
        FOREIGN KEY (id_visitante_portador) REFERENCES visitantes(id) ON DELETE SET NULL
    );
    """)

    # Park Operating Hours Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS horarios_funcionamento_parque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_especifica TEXT UNIQUE, -- Format YYYY-MM-DD
        dia_semana TEXT, -- Segunda, Terca, etc. or NULL if data_especifica is filled
        horario_abertura TEXT, -- Format HH:MM
        horario_fechamento TEXT, -- Format HH:MM
        observacao TEXT
    );
    """)

    # Attraction Maintenance Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS manutencoes_atracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_atracao INTEGER NOT NULL,
        data_inicio_manutencao TEXT NOT NULL, -- Format YYYY-MM-DD HH:MM
        data_fim_prevista_manutencao TEXT,
        data_fim_real_manutencao TEXT,
        tipo_manutencao TEXT NOT NULL, -- Preventiva, Corretiva
        descricao_servico TEXT NOT NULL,
        id_funcionario_responsavel INTEGER,
        custo_estimado REAL,
        custo_real REAL,
        status_manutencao TEXT DEFAULT "Agendada", -- Agendada, Em Andamento, Concluida
        FOREIGN KEY (id_atracao) REFERENCES atracoes(id) ON DELETE CASCADE,
        FOREIGN KEY (id_funcionario_responsavel) REFERENCES funcionarios(id) ON DELETE SET NULL
    );
    """)

    # Shows Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        descricao TEXT,
        tipo_show TEXT, -- Ex: Musical, Teatro, Personagens
        localizacao TEXT,
        horarios TEXT, -- Can be JSON or formatted text
        duracao_minutos INTEGER,
        url_imagem_divulgacao TEXT, -- Path to local image or URL
        ativo INTEGER DEFAULT 1
    );
    """)

    # Park Information Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS informacoes_parque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chave TEXT NOT NULL UNIQUE, -- Ex: "sobre_nos", "regras_gerais", "historia"
        titulo TEXT NOT NULL,
        conteudo TEXT NOT NULL,
        data_atualizacao TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Food Courts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lanchonetes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        descricao TEXT,
        tipo_culinaria TEXT, -- Ex: "Fast Food", "Doces", "Bebidas"
        localizacao_mapa TEXT,
        horario_funcionamento TEXT,
        url_imagem_logo TEXT, -- Path to local image or URL
        ativo INTEGER DEFAULT 1
    );
    """)

    # Menu Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cardapio_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_lanchonete INTEGER NOT NULL,
        nome_item TEXT NOT NULL,
        descricao_item TEXT,
        preco REAL NOT NULL,
        categoria TEXT, -- Ex: "Sanduiches", "Sobremesas", "Bebidas"
        disponivel INTEGER DEFAULT 1,
        url_imagem_item TEXT, -- Path to local image or URL
        FOREIGN KEY (id_lanchonete) REFERENCES lanchonetes(id) ON DELETE CASCADE
    );
    """)

    # Special Attraction Tickets Table (Fast Pass / Scheduling)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bilhetes_atracao_especial (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_item_compra_ingresso INTEGER NULL, -- If purchased
        id_usuario_sistema INTEGER NOT NULL,
        id_atracao INTEGER NOT NULL,
        data_agendamento TEXT NOT NULL, -- Format YYYY-MM-DD
        horario_agendado TEXT NOT NULL, -- Format HH:MM
        status TEXT DEFAULT "Agendado", -- Agendado, Utilizado, Cancelado, Expirado
        codigo_bilhete TEXT UNIQUE NOT NULL,
        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_item_compra_ingresso) REFERENCES itens_compra_ingressos(id) ON DELETE SET NULL,
        FOREIGN KEY (id_usuario_sistema) REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
        FOREIGN KEY (id_atracao) REFERENCES atracoes(id) ON DELETE CASCADE
    );
    """)

    # Park Notices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avisos_parque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        mensagem TEXT NOT NULL,
        tipo_aviso TEXT DEFAULT "Informativo", -- Informativo, Alerta, Urgente
        data_publicacao TEXT DEFAULT CURRENT_TIMESTAMP,
        data_expiracao TEXT,
        ativo INTEGER DEFAULT 1
    );
    """)

    # Ratings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario_sistema INTEGER NOT NULL,
        id_referencia INTEGER NOT NULL, -- ID of attraction, food court, show, etc.
        tipo_referencia TEXT NOT NULL, -- "atracao", "lanchonete", "show"
        nota INTEGER NOT NULL, -- Ex: 1 to 5
        comentario TEXT,
        data_avaliacao TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_usuario_sistema) REFERENCES usuarios_sistema(id) ON DELETE CASCADE
    );
    """)

    # Attraction Check-ins Table (Gamification)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checkins_atracao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario_sistema INTEGER NOT NULL,
        id_atracao INTEGER NOT NULL,
        data_checkin TEXT DEFAULT CURRENT_TIMESTAMP,
        pontos_ganhos INTEGER DEFAULT 0,
        FOREIGN KEY (id_usuario_sistema) REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
        FOREIGN KEY (id_atracao) REFERENCES atracoes(id) ON DELETE CASCADE,
        UNIQUE (id_usuario_sistema, id_atracao, data_checkin) -- Uniqueness per day should be handled in application logic if needed
    );
    """)

    # Itinerary Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itinerarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario_sistema INTEGER NOT NULL,
        nome TEXT NOT NULL,
        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
        data_visita TEXT NOT NULL, -- Format YYYY-MM-DD
        FOREIGN KEY (id_usuario_sistema) REFERENCES usuarios_sistema(id) ON DELETE CASCADE
    );
    """)

    # Itinerary Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_itinerario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_itinerario INTEGER NOT NULL,
        tipo_item TEXT NOT NULL, -- "atracao", "show", "lanchonete"
        id_referencia INTEGER NOT NULL, -- ID of attraction, show, food court
        horario_previsto TEXT, -- Format HH:MM
        ordem INTEGER NOT NULL,
        observacao TEXT,
        FOREIGN KEY (id_itinerario) REFERENCES itinerarios(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("SELECT COUNT(*) FROM atracoes")
    if cursor.fetchone()["COUNT(*)"] == 0:  # Adjusted to access by column name
        populate_example_data(cursor)

    conn.commit()
    conn.close()

def populate_example_data(cursor):
    """Populate the database with example data, including new tables."""
    # Add default admin user
    admin_username = "admin"
    admin_password = "admin123"  # Default password
    admin_email = "admin@infinitypark.com"
    hashed_password = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()

    try:
        cursor.execute(
            "INSERT INTO usuarios_sistema (username, senha_hash, email_recuperacao, tipo_perfil) "
            "VALUES (?, ?, ?, ?)",
            (admin_username, hashed_password, admin_email, "Administrador")
        )
    except sqlite3.IntegrityError:
        pass 
    
    # Ticket Types
    tipos_ingressos_data = [
        ("Adulto", "Ingresso para maiores de 12 anos.", 150.00, 13, 59, 1),
        ("Crianca", "Ingresso para criancas de 3 a 12 anos.", 75.00, 3, 12, 1),
        ("Idoso", "Ingresso para maiores de 60 anos.", 70.00, 60, 120, 1),
        ("PCD", "Ingresso para Pessoa com Deficiencia (acompanhante verificar regras).", 0.00, 0, 120, 1),
        ("VIP Pass", "Acesso rapido a atracoes selecionadas e areas exclusivas.", 300.00, 0, 120, 1)
    ]
    for tipo_ingresso in tipos_ingressos_data:
        try:
            cursor.execute("INSERT INTO tipos_ingressos (nome, descricao, preco_base, idade_minima, idade_maxima, ativo) VALUES (?, ?, ?, ?, ?, ?)", tipo_ingresso)
        except sqlite3.IntegrityError:  # Avoid error if they already exist
            pass

    # Attractions
    atracoes_data = [
        ("Montanha Russa Alpha", "Loopings e adrenalina!", "Sinta a adrenalina pura na Montanha Russa Alpha, uma jornada de alta velocidade com loopings verticais e quedas de tirar o folego. Prepare-se para gritar!", 32, 3, 140, None, 12, None, "Radical", "Area Radical Leste, Setor Vermelho", os.path.join(ASSETS_PATH, "atracao_montanha_russa_alpha.png"), "Operacional", "2025-04-10", "2025-07-10", "Muito Alto", "Nao acessivel para cadeirantes. Restricoes para gestantes e problemas cardiacos."),
        ("Roda Gigante Vista Bela", "Vista panoramica do parque.", "Desfrute de uma vista espetacular de todo o parque e da paisagem ao redor na Roda Gigante Vista Bela. Perfeita para fotos e momentos relaxantes em familia.", 40, 15, 100, None, 0, None, "Familiar", "Praca Central, Proximo a Entrada Principal", os.path.join(ASSETS_PATH, "atracao_roda_gigante_vista_bela.png"), "Operacional", "2025-03-15", "2025-09-15", "Baixo", "Acessivel para cadeirantes (gondola especial)."),
        ("Carrinho Bate-Bate Diversao", "Classica diversao para todos.", "Acelere e divirta-se com os amigos e familia no classico Carrinho Bate-Bate. Risadas garantidas para todas as idades!", 20, 4, 90, None, 6, None, "Familiar", "Area Infantil Oeste, Setor Amarelo", os.path.join(ASSETS_PATH, "atracao_carrinho_bate_bate_diversao.png"), "Manutencao Programada", "2025-05-12", "2025-05-17", "Medio", "Acessivel com auxilio para embarque."),
        ("Rio Bravo Kids", "Aventura aquatica para os pequenos.", "Navegue por corredeiras suaves e divirta-se com esguichos dagua no Rio Bravo Kids. Perfeito para refrescar e para os pequenos aventureiros explorarem.", 20, 10, 80, 120, 4, 8, "Infantil", "Aqua Parque, Setor Azul", os.path.join(ASSETS_PATH, "atracao_rio_bravo_kids.png"), "Operacional", "2025-04-20", "2025-08-20", "Medio", "Acessivel. Criancas pequenas devem estar acompanhadas.")
    ]
    for atracao_tuple in atracoes_data:
        try:
            cursor.execute("""
                INSERT INTO atracoes (
                    nome, descricao_curta, descricao_detalhada, capacidade_por_ciclo, duracao_ciclo_minutos,
                    altura_minima_cm, altura_maxima_cm, idade_minima_anos, acompanhante_obrigatorio_ate_idade,
                    tipo_atracao, localizacao_mapa, local_image_path, status, data_ultima_manutencao,
                    proxima_manutencao_programada, nivel_emocao, acessibilidade
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, atracao_tuple)
        except sqlite3.IntegrityError:
            pass

    # Shows
    shows_data = [
        ("O Reino Encantado", "Um musical magico com princesas e herois.", "Musical", "Teatro Principal", "14:00, 17:00", 60, os.path.join(ASSETS_PATH, "show_reino_encantado.png"), 1),
        ("Acrobatas do Fogo", "Performances radicais com fogo e luzes.", "Performance", "Arena Radical", "20:00", 45, os.path.join(ASSETS_PATH, "show_acrobatas_fogo.png"), 1),
        ("Parada dos Personagens", "Desfile com todos os personagens do parque.", "Desfile", "Rua Principal", "16:00", 30, os.path.join(ASSETS_PATH, "show_parada_personagens.png"), 1)
    ]
    for show_tuple in shows_data:
        try:
            cursor.execute("INSERT INTO shows (nome, descricao, tipo_show, localizacao, horarios, duracao_minutos, url_imagem_divulgacao, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", show_tuple)
        except sqlite3.IntegrityError:
            pass

    # Park Information
    info_parque_data = [
        ("sobre_nos", "Sobre o Infinity Park 215", "O Infinity Park 215 e o seu destino de diversao sem limites! Inaugurado em 2020, nosso parque oferece atracoes emocionantes, shows espetaculares e experiencias inesqueciveis para toda a familia. Venha criar memorias magicas conosco!"),
        ("regras_gerais", "Regras Gerais do Parque", "Para a seguranca e conforto de todos, siga nossas regras: Nao e permitido entrar com alimentos e bebidas (exceto agua e alimentos para bebes). Respeite as filas e as indicacoes dos funcionarios. Proibido fumar fora das areas designadas. Divirta-se com responsabilidade!"),
        ("horarios_funcionamento", "Horarios de Funcionamento", "Consulte a secao especifica de horarios para detalhes atualizados, incluindo dias especiais e feriados.")
    ]
    for info_tuple in info_parque_data:
        try:
            cursor.execute("INSERT INTO informacoes_parque (chave, titulo, conteudo) VALUES (?, ?, ?)", info_tuple)
        except sqlite3.IntegrityError:
            pass    
    
    # Operating Hours
    horarios_data = [
        (None, "Segunda-feira", "10:00", "18:00", "Atracoes aquaticas podem fechar mais cedo dependendo do clima."),
        (None, "Terca-feira", "10:00", "18:00", None),
        (None, "Quarta-feira", "10:00", "18:00", None),
        (None, "Quinta-feira", "10:00", "20:00", "Show noturno as 19:00"),
        (None, "Sexta-feira", "10:00", "22:00", "Parada especial as 21:00"),
        (None, "Sabado", "09:00", "22:00", None),
        (None, "Domingo", "09:00", "20:00", None),
        ("2025-12-25", None, "12:00", "18:00", "Horario especial de Natal"),
        ("2026-01-01", None, "12:00", "20:00", "Horario especial de Ano Novo")
    ]
    for horario_tuple in horarios_data:
        try:
            cursor.execute("INSERT INTO horarios_funcionamento_parque (data_especifica, dia_semana, horario_abertura, horario_fechamento, observacao) VALUES (?, ?, ?, ?, ?)", horario_tuple)
        except sqlite3.IntegrityError:
            pass

    # Food Courts
    lanchonetes_data = [
        ("Burger Mania", "Os melhores hamburgueres do parque!", "Fast Food", "Praca de Alimentacao Central", "10:00 - 21:30", os.path.join(ASSETS_PATH, "lanchonete_burger_mania.png"), 1),
        ("Doce Sonho", "Sobremesas, bolos e cafes deliciosos.", "Doceria", "Rua Principal, proximo a Roda Gigante", "11:00 - 19:00", os.path.join(ASSETS_PATH, "lanchonete_doce_sonho.png"), 1),
        ("Refrescos Tropicais", "Sucos naturais, smoothies e agua de coco.", "Bebidas", "Aqua Parque, entrada", "10:00 - 17:00", os.path.join(ASSETS_PATH, "lanchonete_refrescos_tropicais.png"), 1)
    ]
    for lanchonete_tuple in lanchonetes_data:
        try:
            cursor.execute("INSERT INTO lanchonetes (nome, descricao, tipo_culinaria, localizacao_mapa, horario_funcionamento, url_imagem_logo, ativo) VALUES (?, ?, ?, ?, ?, ?, ?)", lanchonete_tuple)
        except sqlite3.IntegrityError:
            pass

    # Menu Items (Example for Burger Mania, ID 1)
    cardapio_burger_mania = [
        (1, "X-Burger Classico", "Pao, carne, queijo, alface, tomate e molho especial.", 25.50, "Sanduiches", 1, os.path.join(ASSETS_PATH, "item_xburger.png")),
        (1, "Batata Frita Media", "Porcao generosa de batatas fritas crocantes.", 12.00, "Acompanhamentos", 1, os.path.join(ASSETS_PATH, "item_batata_frita.png")),
        (1, "Refrigerante Lata", "Coca-Cola, Guarana, Fanta.", 8.00, "Bebidas", 1, None)
    ]
    for item_tuple in cardapio_burger_mania:
        try:
            cursor.execute("INSERT INTO cardapio_itens (id_lanchonete, nome_item, descricao_item, preco, categoria, disponivel, url_imagem_item) VALUES (?, ?, ?, ?, ?, ?, ?)", item_tuple)
        except sqlite3.IntegrityError:
            pass    
    
    # Menu Items (Example for Doce Sonho, ID 2)
    cardapio_doce_sonho = [
        (2, "Bolo de Chocolate Fatiado", "Fatia generosa de bolo de chocolate com cobertura.", 15.00, "Bolos", 1, os.path.join(ASSETS_PATH, "item_bolo_chocolate.png")),
        (2, "Cafe Expresso", "Cafe forte e aromatico.", 7.00, "Cafes", 1, None)
    ]
    for item_tuple in cardapio_doce_sonho:
        try:
            cursor.execute("INSERT INTO cardapio_itens (id_lanchonete, nome_item, descricao_item, preco, categoria, disponivel, url_imagem_item) VALUES (?, ?, ?, ?, ?, ?, ?)", item_tuple)
        except sqlite3.IntegrityError:
            pass

    # Park Notices
    avisos_data = [
        ("Manutencao Montanha Russa", "A Montanha Russa Alpha estara em manutencao programada de 12/05/2025 a 17/05/2025. Agradecemos a compreensao.", "Informativo", "2025-05-10 10:00:00", "2025-05-18 00:00:00", 1),
        ("Show de Encerramento Especial", "Neste sabado, teremos um show de fogos especial as 21:30 na Praca Central! Nao perca!", "Alerta", "2025-05-13 09:00:00", "2025-05-18 00:00:00", 1)
    ]
    for aviso_tuple in avisos_data:
        try:
            cursor.execute("INSERT INTO avisos_parque (titulo, mensagem, tipo_aviso, data_publicacao, data_expiracao, ativo) VALUES (?, ?, ?, ?, ?, ?)", aviso_tuple)
        except sqlite3.IntegrityError:
            pass

# --- Custom Widget Classes ---
class HeaderLabel(Label):
    def __init__(self, **kwargs):
        super(HeaderLabel, self).__init__(**kwargs)
        self.font_size = "24sp"
        self.bold = True
        self.color = COLOR_PRIMARY
        self.size_hint_y = None
        self.height = 60
        self.halign = "center"
        self.valign = "middle"

class StyledButton(Button):
    def __init__(self, **kwargs):
        super(StyledButton, self).__init__(**kwargs)
        self.background_color = COLOR_PRIMARY
        self.color = COLOR_TEXT_LIGHT
        self.font_size = "16sp"
        self.size_hint_y = None
        self.height = 50

class ClickableLabel(Label):
    id_ref = NumericProperty(0)
    screen_to_go = StringProperty("")

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            if self.screen_to_go == "attraction_detail":
                app.selected_attraction_id = self.id_ref
            elif self.screen_to_go == "show_detail":
                app.selected_show_id = self.id_ref
            # Add more types if needed
            app.previous_screen = app.sm.current
            app.sm.current = self.screen_to_go
            return True
        return super(ClickableLabel, self).on_touch_down(touch)

# --- Application Screens ---
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.name = "login"
        layout = BoxLayout(orientation="vertical", padding=30, spacing=15)
        
        # Logo
        logo_path = os.path.join(ASSETS_PATH, "logo_infinity_park_215.png")
        if os.path.exists(logo_path):
            logo_img = KivyImage(source=logo_path, size_hint_y=None, height=150)
            layout.add_widget(logo_img)
        else:
            layout.add_widget(Label(text=APP_NAME, font_size="32sp", color=COLOR_PRIMARY, size_hint_y=None, height=60))

        layout.add_widget(Label(text="Login de Usuario", font_size="20sp", color=COLOR_TEXT_DARK))
        self.username_input = TextInput(hint_text="Usuario", multiline=False, size_hint_y=None, height=45, font_size="16sp")
        self.password_input = TextInput(hint_text="Senha", password=True, multiline=False, size_hint_y=None, height=45, font_size="16sp")
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        login_button = StyledButton(text="Entrar")
        login_button.bind(on_press=self.login_user)
        register_button = Button(text="Registrar", background_color=COLOR_SECONDARY, color=COLOR_TEXT_DARK, font_size="16sp")
        register_button.bind(on_press=lambda x: setattr(self.manager, "current", "register"))
        buttons_layout.add_widget(login_button)
        buttons_layout.add_widget(register_button)

        self.status_label = Label(text="", size_hint_y=None, height=30, color=COLOR_ACCENT)

        layout.add_widget(self.username_input)
        layout.add_widget(self.password_input)
        layout.add_widget(buttons_layout)
        layout.add_widget(self.status_label)
        
        # Add admin login info for testing
        admin_info = Label(
            text="Admin: usuario=admin, senha=admin123", 
            font_size="14sp", 
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30
        )
        layout.add_widget(admin_info)
        
        self.add_widget(layout)

    def login_user(self, instance):
        username = self.username_input.text
        password = self.password_input.text

        if not username or not password:
            self.status_label.text = "Preencha usuario e senha."
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se o usuário admin existe e criar se não existir
        cursor.execute("SELECT COUNT(*) FROM usuarios_sistema WHERE username = 'admin'")
        admin_exists = cursor.fetchone()[0] > 0
        
        if not admin_exists:
            # Criar usuário admin se não existir
            admin_password = "admin123"
            hashed_password = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()
            cursor.execute(
                "INSERT INTO usuarios_sistema (username, senha_hash, email_recuperacao, tipo_perfil, ativo) "
                "VALUES (?, ?, ?, ?, ?)",
                ("admin", hashed_password, "admin@infinitypark.com", "Administrador", 1)
            )
            conn.commit()
            
        # Continuar com o login normal
        cursor.execute("SELECT id, senha_hash, tipo_perfil FROM usuarios_sistema WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        
        if user_data:
            hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if hashed_password == user_data["senha_hash"]:
                self.status_label.text = "Login bem-sucedido!"
                app = App.get_running_app()
                app.user_id = user_data["id"]
                app.user_profile = user_data["tipo_perfil"]
                self.username_input.text = ""
                self.password_input.text = ""
                self.status_label.text = ""
                if app.user_profile == "Administrador":
                    self.manager.current = "admin_home"
                else:
                    self.manager.current = "user_home"
            else:
                self.status_label.text = "Senha incorreta."
        else:
            self.status_label.text = "Usuario nao encontrado ou inativo."
        
        conn.close()


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(RegisterScreen, self).__init__(**kwargs)
        self.name = "register"
        layout = BoxLayout(orientation="vertical", padding=30, spacing=15)
        layout.add_widget(HeaderLabel(text="Cadastro de Novo Usuario"))

        self.username_input = TextInput(hint_text="Nome de Usuario", multiline=False, size_hint_y=None, height=45)
        self.email_input = TextInput(hint_text="Email para Recuperacao", multiline=False, size_hint_y=None, height=45)
        self.password_input = TextInput(hint_text="Senha", password=True, multiline=False, size_hint_y=None, height=45)
        self.confirm_password_input = TextInput(hint_text="Confirmar Senha", password=True, multiline=False, size_hint_y=None, height=45)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        register_button = StyledButton(text="Registrar")
        register_button.bind(on_press=self.register_user)
        back_button = Button(text="Voltar para Login", background_color=COLOR_SECONDARY, color=COLOR_TEXT_DARK)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "login"))
        buttons_layout.add_widget(register_button)
        buttons_layout.add_widget(back_button)

        self.status_label = Label(text="", size_hint_y=None, height=30, color=COLOR_ACCENT)

        layout.add_widget(self.username_input)
        layout.add_widget(self.email_input)
        layout.add_widget(self.password_input)
        layout.add_widget(self.confirm_password_input)
        layout.add_widget(buttons_layout)
        layout.add_widget(self.status_label)
        self.add_widget(layout)

    def register_user(self, instance):
        username = self.username_input.text
        email = self.email_input.text
        password = self.password_input.text
        confirm_password = self.confirm_password_input.text

        if not all([username, email, password, confirm_password]):
            self.status_label.text = "Todos os campos sao obrigatorios."
            return
        if password != confirm_password:
            self.status_label.text = "As senhas nao coincidem."
            return
        if len(password) < 6:
            self.status_label.text = "A senha deve ter pelo menos 6 caracteres."
            return
        # TODO: Validate email format

        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO usuarios_sistema (username, senha_hash, email_recuperacao, tipo_perfil) VALUES (?, ?, ?, ?)",
                           (username, hashed_password, email, "Comum"))
            conn.commit()
            self.status_label.text = "Usuario cadastrado com sucesso! Faca o login."
            self.username_input.text = ""
            self.email_input.text = ""
            self.password_input.text = ""
            self.confirm_password_input.text = ""
        except sqlite3.IntegrityError as e:
            if "username" in str(e).lower():
                self.status_label.text = "Nome de usuario ja existe."
            elif "email_recuperacao" in str(e).lower():
                self.status_label.text = "Email ja cadastrado."
            else:
                self.status_label.text = f"Erro de integridade: {e}"
        except Exception as e:
            self.status_label.text = f"Erro ao cadastrar: {e}"
        finally:
            conn.close()

class UserHomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "user_home"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=8)
        
        layout.add_widget(HeaderLabel(text=f"Bem-vindo ao {APP_NAME}!"))
        
        scroll = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        button_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, padding=10)
        button_grid.bind(minimum_height=button_grid.setter("height"))

        buttons_data = [
            ("Ver Atracoes", "attractions_list", "atracao_icon.png"),
            ("Ver Shows", "shows_list", "show_icon.png"),
            ("Ingressos", "tickets_list", "ticket_icon.png"),
            ("Lanchonetes", "food_courts_list", "food_icon.png"),
            ("Mapa do Parque", "park_map", "map_icon.png"),
            ("Sobre o Parque", "about_park", "info_icon.png"),
            ("Avisos Importantes", "warnings_list", "warning_icon.png"),
            ("Meu Perfil", "my_profile", "profile_icon.png"),
            ("Criar Itinerario", "create_itinerary", "itinerary_icon.png"),
            ("Ver Meu Itinerario", "my_itinerary", "my_itinerary_icon.png")
        ]

        for text, screen_name, icon_name in buttons_data:
            btn_item = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=5)
            
            icon_path = os.path.join(ASSETS_PATH, icon_name)
            if os.path.exists(icon_path):
                img = KivyImage(source=icon_path, size_hint_y=None, height=60)
            else:
                img = Label(text="Ícone", size_hint_y=None, height=60)
            
            btn = StyledButton(text=text, size_hint_y=None, height=50)
            btn.bind(on_press=lambda _, sn=screen_name: self.go_to_screen(sn))
            
            btn_item.add_widget(img)
            btn_item.add_widget(btn)
            button_grid.add_widget(btn_item)

        scroll.add_widget(button_grid)
        layout.add_widget(scroll)

        logout_btn = Button(text="Logout", size_hint_y=None, height=50,
                          background_color=COLOR_SECONDARY, color=COLOR_TEXT_DARK)
        logout_btn.bind(on_press=self.logout)
        layout.add_widget(logout_btn)
        
        self.add_widget(layout)

    def go_to_screen(self, screen_name):
        App.get_running_app().previous_screen = self.name
        self.manager.current = screen_name

    def logout(self, instance):
        app = App.get_running_app()
        app.user_id = None
        app.user_profile = None
        self.manager.current = "login"

class AdminHomeScreen(Screen):
    def __init__(self, **kwargs):
        super(AdminHomeScreen, self).__init__(**kwargs)
        self.name = "admin_home"
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)
        layout.add_widget(HeaderLabel(text="Painel do Administrador"))
        
        button_grid = GridLayout(cols=2, spacing=10, size_hint_y=None, padding=10)
        button_grid.bind(minimum_height=button_grid.setter("height"))

        admin_buttons_data = [
            ("Gerenciar Usuarios", "admin_manage_users", "users_icon.png"),
            ("Gerenciar Atracoes", "admin_manage_attractions", "attraction_icon.png"),
            ("Gerenciar Shows", "admin_manage_shows", "show_icon.png"),
            ("Gerenciar Lanchonetes", "admin_manage_food_courts", "food_icon.png"),
            ("Gerenciar Avisos", "admin_manage_warnings", "warning_icon.png"),
            ("Ver Logs do Sistema", "admin_system_logs", "log_icon.png")
        ]

        for text, screen_name, icon_name in admin_buttons_data:
            button_item_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=5)
            icon_path = os.path.join(ASSETS_PATH, icon_name)
            if os.path.exists(icon_path):
                img = KivyImage(source=icon_path, size_hint_y=None, height=60)
            else:
                img = Label(text="Icone", size_hint_y=None, height=60)
            
            btn = StyledButton(text=text, height=50, size_hint_y=None)
            btn.bind(on_press=lambda x, sn=screen_name: setattr(self.manager, "current", sn) if self.manager.has_screen(sn) else self.show_dev_popup(sn))
            
            button_item_layout.add_widget(img)
            button_item_layout.add_widget(btn)
            button_grid.add_widget(button_item_layout)

        layout.add_widget(button_grid)
        
        logout_button = Button(text="Logout", size_hint_y=None, height=50, background_color=COLOR_SECONDARY, color=COLOR_TEXT_DARK)
        logout_button.bind(on_press=self.logout)
        layout.add_widget(logout_button)
        self.add_widget(layout)

    def logout(self, instance):
        app = App.get_running_app()
        app.user_id = None
        app.user_profile = None
        self.manager.current = "login"
    
    def show_dev_popup(self, screen_name):
        popup_content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        popup_content.add_widget(Label(text=f"A tela '{screen_name}' ainda está em desenvolvimento."))
        close_button = StyledButton(text="Fechar")        
        popup_content.add_widget(close_button)
        popup = Popup(title="Em Desenvolvimento", content=popup_content, size_hint=(0.8, 0.4))
        close_button.bind(on_press=popup.dismiss)
        popup.open()

# --- Attractions Screens ---
class AttractionsListScreen(Screen):
    def __init__(self, **kwargs):
        super(AttractionsListScreen, self).__init__(**kwargs)
        self.name = "attractions_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Atrações do Parque"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.attractions_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.attractions_grid.bind(minimum_height=self.attractions_grid.setter("height"))
        scroll_view.add_widget(self.attractions_grid)
        layout.add_widget(scroll_view)
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_attractions()

    def load_attractions(self):
        self.attractions_grid.clear_widgets()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, descricao_curta, local_image_path, tipo_atracao, status FROM atracoes ORDER BY nome")
        attractions = cursor.fetchall()
        conn.close()

        if not attractions:
            self.attractions_grid.add_widget(Label(text="Nenhuma atração disponível no momento.", color=COLOR_TEXT_DARK))
            return

        for attraction in attractions:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=150, spacing=10, padding=5)
            
            # Image
            img_path = attraction["local_image_path"] if attraction["local_image_path"] and os.path.exists(attraction["local_image_path"]) else os.path.join(ASSETS_PATH, "attraction_placeholder.png")
            if os.path.exists(img_path):
                img = KivyImage(source=img_path, size_hint_x=0.4)
            else:
                img = Label(text="Imagem\nNão Disponível", size_hint_x=0.4, color=COLOR_TEXT_DARK)
            item.add_widget(img)
            
            # Info
            info_layout = BoxLayout(orientation="vertical", size_hint_x=0.6, spacing=5)
            info_layout.add_widget(Label(
                text=attraction["nome"],
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            info_layout.add_widget(Label(
                text=attraction["descricao_curta"] if attraction["descricao_curta"] else "Sem descrição",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            info_layout.add_widget(Label(
                text=f"Tipo: {attraction['tipo_atracao']} | Status: {attraction['status']}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            
            # Details button
            details_button = StyledButton(text="Ver Detalhes", size_hint_y=None, height=40)
            details_button.bind(on_press=lambda _, id=attraction["id"]: self.show_details(id))
            info_layout.add_widget(details_button)
            
            item.add_widget(info_layout)
            self.attractions_grid.add_widget(item)

    def show_details(self, attraction_id):
        app = App.get_running_app()
        app.selected_attraction_id = attraction_id
        app.previous_screen = self.name
        self.manager.current = "attraction_detail"

class AttractionDetailScreen(Screen):
    def __init__(self, **kwargs):
        super(AttractionDetailScreen, self).__init__(**kwargs)
        self.name = "attraction_detail"
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # Header with title and back button
        self.header_label = HeaderLabel(text="Detalhes da Atração")
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(self.header_label)
        
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "attractions_list"))
        header_layout.add_widget(back_button)
        
        self.layout.add_widget(header_layout)

        # Scrollable content area
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.details_content = BoxLayout(
            orientation="vertical", 
            size_hint_y=None, 
            spacing=10,
            padding=10
        )
        self.details_content.bind(minimum_height=self.details_content.setter('height'))
        self.scroll_view.add_widget(self.details_content)
        self.layout.add_widget(self.scroll_view)

        self.add_widget(self.layout)
        
        # Average rating component
        self.avg_rating_label = Label(
            text="Avaliação Média: N/A",
            font_size="15sp",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        
        # Status label for actions
        self.status_label = Label(
            text="",
            font_size="14sp",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )

    def on_enter(self, *args):
        self.load_attraction_details()

    def load_attraction_details(self):
        self.details_content.clear_widgets()
        attraction_id = App.get_running_app().selected_attraction_id
        if not attraction_id:
            self.details_content.add_widget(Label(text="Nenhuma atração selecionada.", color=COLOR_TEXT_DARK))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM atracoes WHERE id = ?", (attraction_id,))
        attraction = cursor.fetchone()
        
        cursor.execute(
            "SELECT AVG(nota) as media, COUNT(id) as total_avaliacoes "
            "FROM avaliacoes WHERE id_referencia = ? AND tipo_referencia = ?",
            (attraction_id, "atracao")
        )
        rating_data = cursor.fetchone()
        conn.close()

        if not attraction:
            self.details_content.add_widget(Label(text="Detalhes da atração não encontrados.", color=COLOR_TEXT_DARK))
            return

        self.header_label.text = attraction["nome"]

        # Attraction image
        if attraction["local_image_path"] and os.path.exists(attraction["local_image_path"]):
            self.details_content.add_widget(KivyImage(
                source=attraction["local_image_path"],
                size_hint_y=None,
                height=250
            ))
        else:
            placeholder_img = os.path.join(ASSETS_PATH, "attraction_placeholder.png")
            if os.path.exists(placeholder_img):
                self.details_content.add_widget(KivyImage(
                    source=placeholder_img,
                    size_hint_y=None,
                    height=250
                ))
            else:
                self.details_content.add_widget(Label(
                    text="Sem Imagem Disponível",
                    size_hint_y=None,
                    height=200,
                    color=COLOR_TEXT_DARK
                ))

        # Attraction details
        self.details_content.add_widget(Label(
            text=attraction["nome"],
            font_size='20sp',
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40,
            halign='left',
            text_size=(Window.width * 0.85, None)
        ))

        desc_label = Label(
            text=attraction["descricao_detalhada"] if attraction["descricao_detalhada"] else "Descrição não disponível.",
            font_size='15sp',
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            halign='left',
            text_size=(Window.width * 0.85, None)
        )

        desc_label.bind(texture_size=desc_label.setter('size'))
        self.details_content.add_widget(desc_label)

        # Technical details
        tech_details = [
            f"Tipo: {attraction['tipo_atracao']}",
            f"Status: {attraction['status']}",
            f"Localização: {attraction['localizacao_mapa']}",
            f"Altura mínima: {attraction['altura_minima_cm']} cm" if attraction['altura_minima_cm'] else "Sem restrição de altura mínima",
            f"Idade mínima: {attraction['idade_minima_anos']} anos" if attraction['idade_minima_anos'] else "Sem restrição de idade mínima",
            f"Nível de emoção: {attraction['nivel_emocao']}",
            f"Acessibilidade: {attraction['acessibilidade']}"
        ]

        for detail in tech_details:
            self.details_content.add_widget(Label(
                text=detail,
                font_size='15sp',
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=30,
                halign='left',
                text_size=(Window.width * 0.85, None)
            ))

        # Average rating
        if rating_data and rating_data["media"] is not None:
            self.avg_rating_label.text = f"Avaliação Média: {rating_data['media']:.1f}/5 ({rating_data['total_avaliacoes']} avaliações)"
        else:
            self.avg_rating_label.text = "Avaliação Média: Nenhuma avaliação ainda."
        self.details_content.add_widget(self.avg_rating_label)

        # Action buttons
        action_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        # FastPass button
        fastpass_button = StyledButton(
            text="Agendar FastPass",
            size_hint_x=0.5
        )
        fastpass_button.bind(on_press=self.request_fastpass)
        
        # Check-in button
        checkin_button = StyledButton(
            text="Fazer Check-in",
            size_hint_x=0.5
        )
        checkin_button.bind(on_press=self.do_checkin)
        
        action_layout.add_widget(fastpass_button)
        action_layout.add_widget(checkin_button)
        self.details_content.add_widget(action_layout)

        # Rating button
        rate_button = StyledButton(
            text="Avaliar Atração",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        rate_button.bind(on_press=self.open_rating_popup)
        self.details_content.add_widget(rate_button)
        
        # Status label for actions
        self.details_content.add_widget(self.status_label)

    def request_fastpass(self, instance):
        self.status_label.text = "Funcionalidade FastPass em desenvolvimento."

    def do_checkin(self, instance):
        app = App.get_running_app()
        user_id = app.user_id
        attraction_id = app.selected_attraction_id
        
        if not user_id:
            self.status_label.text = "Você precisa estar logado para fazer check-in."
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user already checked in today
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT id FROM checkins_atracao WHERE id_usuario_sistema = ? AND id_atracao = ? AND date(data_checkin) = ?",
                (user_id, attraction_id, today)
            )
            
            if cursor.fetchone():
                self.status_label.text = "Você já fez check-in nesta atração hoje!"
                conn.close()
                return
                
            # Add check-in with points
            points = 10  # Default points per check-in
            cursor.execute(
                "INSERT INTO checkins_atracao (id_usuario_sistema, id_atracao, pontos_ganhos) VALUES (?, ?, ?)",
                (user_id, attraction_id, points)
            )
            
            conn.commit()
            self.status_label.text = f"Check-in realizado com sucesso! +{points} pontos"
            
        except Exception as e:
            self.status_label.text = f"Erro ao fazer check-in: {e}"
        finally:
            conn.close()

    def open_rating_popup(self, instance):
        attraction_id = App.get_running_app().selected_attraction_id
        if attraction_id:
            popup = RatingPopup(id_referencia=attraction_id, tipo_referencia="atracao")
            popup.open()

class AdminManageAttractionsScreen(Screen):
    def __init__(self, **kwargs):
        super(AdminManageAttractionsScreen, self).__init__(**kwargs)
        self.name = "admin_manage_attractions"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Gerenciar Atrações"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "admin_home"))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Add Attraction button
        add_button = StyledButton(text="Adicionar Nova Atração", size_hint_y=None, height=50)
        add_button.bind(on_press=self.open_add_attraction_popup)
        layout.add_widget(add_button)

        # Attractions list
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.attractions_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.attractions_grid.bind(minimum_height=self.attractions_grid.setter("height"))
        scroll_view.add_widget(self.attractions_grid)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_attractions()

    def load_attractions(self):
        self.attractions_grid.clear_widgets()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, tipo_atracao, status FROM atracoes ORDER BY nome")
        attractions = cursor.fetchall()
        conn.close()

        if not attractions:
            self.attractions_grid.add_widget(Label(text="Nenhuma atração cadastrada.", color=COLOR_TEXT_DARK))
            return

        for attraction in attractions:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=80, spacing=10, padding=5)
            
            # Attraction info
            info_layout = BoxLayout(orientation="vertical", size_hint_x=0.7)
            info_layout.add_widget(Label(
                text=attraction["nome"],
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY if attraction["status"] == "Operacional" else COLOR_SECONDARY,
                halign="left",
                text_size=(Window.width * 0.6, None)
            ))
            info_layout.add_widget(Label(
                text=f"Tipo: {attraction['tipo_atracao']} | Status: {attraction['status']}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                text_size=(Window.width * 0.6, None)
            ))
            item.add_widget(info_layout)
            
            # Action buttons
            buttons_layout = BoxLayout(orientation="vertical", size_hint_x=0.3, spacing=5)
            edit_button = Button(text="Editar", size_hint_y=None, height=35, background_color=COLOR_ACCENT)
            edit_button.bind(on_press=lambda _, id=attraction["id"]: self.open_edit_attraction_popup(id))
            
            toggle_button = Button(
                text="Manutenção" if attraction["status"] == "Operacional" else "Operacional", 
                size_hint_y=None, 
                height=35, 
                background_color=COLOR_SECONDARY if attraction["status"] == "Operacional" else COLOR_PRIMARY
            )
            toggle_button.bind(on_press=lambda _, id=attraction["id"], status=attraction["status"]: self.toggle_attraction_status(id, status))
            
            buttons_layout.add_widget(edit_button)
            buttons_layout.add_widget(toggle_button)
            item.add_widget(buttons_layout)
            
            self.attractions_grid.add_widget(item)

    def open_add_attraction_popup(self, instance):
        popup = AttractionFormPopup(mode="add", callback=self.load_attractions)
        popup.open()

    def open_edit_attraction_popup(self, attraction_id):
        popup = AttractionFormPopup(mode="edit", attraction_id=attraction_id, callback=self.load_attractions)
        popup.open()

    def toggle_attraction_status(self, attraction_id, current_status):
        new_status = "Manutencao Programada" if current_status == "Operacional" else "Operacional"
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE atracoes SET status = ? WHERE id = ?", (new_status, attraction_id))
            conn.commit()
            self.load_attractions()  # Refresh the list
        except Exception as e:
            print(f"Error toggling attraction status: {e}")
        finally:
            conn.close()

class AttractionFormPopup(Popup):
    def __init__(self, mode="add", attraction_id=None, callback=None, **kwargs):
        self.mode = mode
        self.attraction_id = attraction_id
        self.callback = callback
        
        title = "Adicionar Nova Atração" if mode == "add" else "Editar Atração"
        super(AttractionFormPopup, self).__init__(title=title, size_hint=(0.9, 0.9), **kwargs)
        
        layout = BoxLayout(orientation="vertical", padding=15, spacing=10)
        
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))
        
        # Form fields
        form_layout.add_widget(Label(text="Nome da Atração:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.nome_input = TextInput(hint_text="Nome da atração", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.nome_input)
        
        form_layout.add_widget(Label(text="Descrição Curta:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.descricao_curta_input = TextInput(hint_text="Descrição curta", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.descricao_curta_input)
        
        form_layout.add_widget(Label(text="Descrição Detalhada:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.descricao_detalhada_input = TextInput(hint_text="Descrição detalhada", multiline=True, size_hint_y=None, height=80)
        form_layout.add_widget(self.descricao_detalhada_input)
        
        form_layout.add_widget(Label(text="Tipo de Atração:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.tipo_atracao_input = TextInput(hint_text="Ex: Radical, Familiar, Infantil", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.tipo_atracao_input)
        
        form_layout.add_widget(Label(text="Localização:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.localizacao_input = TextInput(hint_text="Local onde a atração está", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.localizacao_input)
        
        form_layout.add_widget(Label(text="Capacidade por Ciclo:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.capacidade_input = TextInput(hint_text="Ex: 30", input_filter="int", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.capacidade_input)
        
        form_layout.add_widget(Label(text="Duração do Ciclo (minutos):", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.duracao_input = TextInput(hint_text="Ex: 5", input_filter="int", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.duracao_input)
        
        form_layout.add_widget(Label(text="Altura Mínima (cm):", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.altura_minima_input = TextInput(hint_text="Ex: 120", input_filter="int", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.altura_minima_input)
        
        form_layout.add_widget(Label(text="Idade Mínima (anos):", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.idade_minima_input = TextInput(hint_text="Ex: 10", input_filter="int", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.idade_minima_input)
        
        form_layout.add_widget(Label(text="Nível de Emoção:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.nivel_emocao_input = TextInput(hint_text="Ex: Baixo, Médio, Alto", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.nivel_emocao_input)
        
        form_layout.add_widget(Label(text="Acessibilidade:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.acessibilidade_input = TextInput(hint_text="Informações sobre acessibilidade", multiline=True, size_hint_y=None, height=60)
        form_layout.add_widget(self.acessibilidade_input)
        
        form_layout.add_widget(Label(text="Caminho da Imagem:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.imagem_input = TextInput(hint_text="Caminho para a imagem", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.imagem_input)
        
        self.status_spinner = Spinner(
            text="Operacional",
            values=["Operacional", "Manutencao Programada", "Fechada Temporariamente"],
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(Label(text="Status:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        form_layout.add_widget(self.status_spinner)
        
        scroll.add_widget(form_layout)
        layout.add_widget(scroll)
        
        # Buttons
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        save_button = StyledButton(text="Salvar")
        save_button.bind(on_press=self.save_attraction)
        cancel_button = Button(text="Cancelar", background_color=COLOR_SECONDARY, color=COLOR_TEXT_DARK)
        cancel_button.bind(on_press=self.dismiss)
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(cancel_button)
        layout.add_widget(buttons_layout)
        
        self.status_label = Label(text="", size_hint_y=None, height=30, color=COLOR_ACCENT)
        layout.add_widget(self.status_label)
        
        self.content = layout
        
        # If editing, load attraction data
        if mode == "edit" and attraction_id:
            self.load_attraction_data()
    
    def load_attraction_data(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM atracoes WHERE id = ?", (self.attraction_id,))
        attraction = cursor.fetchone()
        conn.close()
        
        if attraction:
            self.nome_input.text = attraction["nome"]
            self.descricao_curta_input.text = attraction["descricao_curta"] if attraction["descricao_curta"] else ""
            self.descricao_detalhada_input.text = attraction["descricao_detalhada"] if attraction["descricao_detalhada"] else ""
            self.tipo_atracao_input.text = attraction["tipo_atracao"] if attraction["tipo_atracao"] else ""
            self.localizacao_input.text = attraction["localizacao_mapa"] if attraction["localizacao_mapa"] else ""
            self.capacidade_input.text = str(attraction["capacidade_por_ciclo"]) if attraction["capacidade_por_ciclo"] else ""
            self.duracao_input.text = str(attraction["duracao_ciclo_minutos"]) if attraction["duracao_ciclo_minutos"] else ""
            self.altura_minima_input.text = str(attraction["altura_minima_cm"]) if attraction["altura_minima_cm"] else ""
            self.idade_minima_input.text = str(attraction["idade_minima_anos"]) if attraction["idade_minima_anos"] else ""
            self.nivel_emocao_input.text = attraction["nivel_emocao"] if attraction["nivel_emocao"] else ""
            self.acessibilidade_input.text = attraction["acessibilidade"] if attraction["acessibilidade"] else ""
            self.imagem_input.text = attraction["local_image_path"] if attraction["local_image_path"] else ""
            self.status_spinner.text = attraction["status"] if attraction["status"] else "Operacional"
    
    def save_attraction(self, instance):
        # Validate required fields
        if not self.nome_input.text:
            self.status_label.text = "Nome da atração é obrigatório."
            return
        
        if not self.capacidade_input.text:
            self.status_label.text = "Capacidade por ciclo é obrigatória."
            return
        
        # Prepare data
        nome = self.nome_input.text
        descricao_curta = self.descricao_curta_input.text
        descricao_detalhada = self.descricao_detalhada_input.text
        tipo_atracao = self.tipo_atracao_input.text
        localizacao_mapa = self.localizacao_input.text
        
        try:
            capacidade = int(self.capacidade_input.text)
            duracao = int(self.duracao_input.text) if self.duracao_input.text else None
            altura_minima = int(self.altura_minima_input.text) if self.altura_minima_input.text else None
            idade_minima = int(self.idade_minima_input.text) if self.idade_minima_input.text else None
        except ValueError:
            self.status_label.text = "Valores numéricos inválidos."
            return
        
        nivel_emocao = self.nivel_emocao_input.text
        acessibilidade = self.acessibilidade_input.text
        local_image_path = self.imagem_input.text
        status = self.status_spinner.text
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if self.mode == "add":
                cursor.execute(
                    "INSERT INTO atracoes (nome, descricao_curta, descricao_detalhada, capacidade_por_ciclo, "
                    "duracao_ciclo_minutos, altura_minima_cm, idade_minima_anos, tipo_atracao, "
                    "localizacao_mapa, local_image_path, status, nivel_emocao, acessibilidade) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (nome, descricao_curta, descricao_detalhada, capacidade, duracao, altura_minima, 
                     idade_minima, tipo_atracao, localizacao_mapa, local_image_path, status, nivel_emocao, acessibilidade)
                )
                self.status_label.text = "Atração adicionada com sucesso!"
            else:
                cursor.execute(
                    "UPDATE atracoes SET nome = ?, descricao_curta = ?, descricao_detalhada = ?, "
                    "capacidade_por_ciclo = ?, duracao_ciclo_minutos = ?, altura_minima_cm = ?, "
                    "idade_minima_anos = ?, tipo_atracao = ?, localizacao_mapa = ?, local_image_path = ?, "
                    "status = ?, nivel_emocao = ?, acessibilidade = ? WHERE id = ?",
                    (nome, descricao_curta, descricao_detalhada, capacidade, duracao, altura_minima, 
                     idade_minima, tipo_atracao, localizacao_mapa, local_image_path, status, nivel_emocao, 
                     acessibilidade, self.attraction_id)
                )
                self.status_label.text = "Atração atualizada com sucesso!"
            
            conn.commit()
            
            # Call callback to refresh the list
            if self.callback:
                self.callback()
                
            # Close popup after a short delay
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.dismiss(), 1.5)
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                self.status_label.text = "Erro: Já existe uma atração com este nome."
            else:
                self.status_label.text = f"Erro de integridade: {e}"
        except Exception as e:
            self.status_label.text = f"Erro ao salvar: {e}"
        finally:
            conn.close()

# --- Shows Management Screens ---
class ShowsListScreen(Screen):
    def __init__(self, **kwargs):
        super(ShowsListScreen, self).__init__(**kwargs)
        self.name = "shows_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Shows do Parque"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.shows_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.shows_grid.bind(minimum_height=self.shows_grid.setter("height"))
        scroll_view.add_widget(self.shows_grid)
        layout.add_widget(scroll_view)
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_shows()

    def load_shows(self):
        self.shows_grid.clear_widgets()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, tipo_show, url_imagem_divulgacao, horarios FROM shows WHERE ativo = 1 ORDER BY nome")
        shows = cursor.fetchall()
        conn.close()

        if not shows:
            self.shows_grid.add_widget(Label(text="Nenhum show disponível no momento.", color=COLOR_TEXT_DARK))
            return

        for show in shows:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=150, spacing=10, padding=5)
            
            # Image
            img_path = show["url_imagem_divulgacao"] if show["url_imagem_divulgacao"] and os.path.exists(show["url_imagem_divulgacao"]) else os.path.join(ASSETS_PATH, "show_placeholder.png")
            if os.path.exists(img_path):
                img = KivyImage(source=img_path, size_hint_x=0.4)
            else:
                img = Label(text="Imagem\nNão Disponível", size_hint_x=0.4, color=COLOR_TEXT_DARK)
            item.add_widget(img)
            
            # Info
            info_layout = BoxLayout(orientation="vertical", size_hint_x=0.6, spacing=5)
            info_layout.add_widget(Label(
                text=show["nome"],
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            info_layout.add_widget(Label(
                text=f"Tipo: {show['tipo_show']}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            info_layout.add_widget(Label(
                text=f"Horários: {show['horarios']}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            
            # Details button
            details_button = StyledButton(text="Ver Detalhes", size_hint_y=None, height=40)
            details_button.bind(on_press=lambda _, id=show["id"]: self.show_details(id))
            info_layout.add_widget(details_button)
            
            item.add_widget(info_layout)
            self.shows_grid.add_widget(item)

    def show_details(self, show_id):
        app = App.get_running_app()
        app.selected_show_id = show_id
        app.previous_screen = self.name
        self.manager.current = "show_detail"

class ShowDetailScreen(Screen):
    def __init__(self, **kwargs):
        super(ShowDetailScreen, self).__init__(**kwargs)
        self.name = "show_detail"
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # Header with title and back button
        self.header_label = HeaderLabel(text="Detalhes do Show")
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(self.header_label)
        
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "shows_list"))
        header_layout.add_widget(back_button)
        
        self.layout.add_widget(header_layout)

        # Scrollable content area
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.details_content = BoxLayout(
            orientation="vertical", 
            size_hint_y=None, 
            spacing=10,
            padding=10
        )
        self.details_content.bind(minimum_height=self.details_content.setter('height'))
        self.scroll_view.add_widget(self.details_content)
        self.layout.add_widget(self.scroll_view)

        self.add_widget(self.layout)
        
        # Average rating component
        self.avg_rating_label_show = Label(
            text="Avaliação Média: N/A",
            font_size="15sp",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )

    def on_enter(self, *args):
        self.load_show_details()

    def load_show_details(self):
        self.details_content.clear_widgets()
        show_id = App.get_running_app().selected_show_id
        if not show_id:
            self.details_content.add_widget(Label(text="Nenhum show selecionado.", color=COLOR_TEXT_DARK))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shows WHERE id = ?", (show_id,))
        show = cursor.fetchone()
        
        cursor.execute(
            "SELECT AVG(nota) as media, COUNT(id) as total_avaliacoes "
            "FROM avaliacoes WHERE id_referencia = ? AND tipo_referencia = ?",
            (show_id, "show")
        )
        rating_data = cursor.fetchone()
        conn.close()

        if not show:
            self.details_content.add_widget(Label(text="Detalhes do show não encontrados.", color=COLOR_TEXT_DARK))
            return

        self.header_label.text = show["nome"]

        # Show image
        if show["url_imagem_divulgacao"] and os.path.exists(show["url_imagem_divulgacao"]):
            self.details_content.add_widget(KivyImage(
                source=show["url_imagem_divulgacao"],
                size_hint_y=None,
                height=250
            ))
        else:
            placeholder_img = os.path.join(ASSETS_PATH, "show_placeholder.png")
            if os.path.exists(placeholder_img):
                self.details_content.add_widget(KivyImage(
                    source=placeholder_img,
                    size_hint_y=None,
                    height=250
                ))
            else:
                self.details_content.add_widget(Label(
                    text="Sem Imagem Disponível",
                    size_hint_y=None,
                    height=200,
                    color=COLOR_TEXT_DARK
                ))

        # Show details
        self.details_content.add_widget(Label(
            text=f"Nome: {show['nome']}",
            font_size='20sp',
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40,
            halign='left',
            text_size=(Window.width * 0.85, None)
        ))

        desc_label = Label(
            text=f"Descrição: {show['descricao'] if show['descricao'] else 'Não disponível.'}",
            font_size='15sp',
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            halign='left',
            text_size=(Window.width * 0.85, None)
        )

        desc_label.bind(texture_size=desc_label.setter('size'))
        self.details_content.add_widget(desc_label)

        self.details_content.add_widget(Label(
            text=f"Tipo: {show['tipo_show'] if show['tipo_show'] else 'Não especificado'}",
            font_size='15sp',
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30
        ))

        self.details_content.add_widget(Label(
            text=f"Localização: {show['localizacao'] if show['localizacao'] else 'Não especificado'}",
            font_size='15sp',
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30
        ))

        self.details_content.add_widget(Label(
            text=f"Horários: {show['horarios'] if show['horarios'] else 'Consultar programação'}",
            font_size='15sp',
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30
        ))

        self.details_content.add_widget(Label(
            text=f"Duração: {show['duracao_minutos']} minutos" if show['duracao_minutos'] else "Duração não informada",
            font_size='15sp',
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30
        ))

        # Average rating
        if rating_data and rating_data["media"] is not None:
            self.avg_rating_label_show.text = f"Avaliação Média: {rating_data['media']:.1f}/5 ({rating_data['total_avaliacoes']} avaliações)"
        else:
            self.avg_rating_label_show.text = "Avaliação Média: Nenhuma avaliação ainda."
        self.details_content.add_widget(self.avg_rating_label_show)

        # Rating button
        rate_button = StyledButton(
            text="Avaliar Show",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        rate_button.bind(on_press=self.open_rating_popup)
        self.details_content.add_widget(rate_button)

    def open_rating_popup(self, instance):
        show_id = App.get_running_app().selected_show_id
        if show_id:
            popup = RatingPopup(id_referencia=show_id, tipo_referencia="show")
            popup.open()

class AdminManageShowsScreen(Screen):
    def __init__(self, **kwargs):
        super(AdminManageShowsScreen, self).__init__(**kwargs)
        self.name = "admin_manage_shows"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Gerenciar Shows"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "admin_home"))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Add Show button
        add_button = StyledButton(text="Adicionar Novo Show", size_hint_y=None, height=50)
        add_button.bind(on_press=self.open_add_show_popup)
        layout.add_widget(add_button)

        # Shows list
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.shows_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.shows_grid.bind(minimum_height=self.shows_grid.setter("height"))
        scroll_view.add_widget(self.shows_grid)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_shows()

    def load_shows(self):
        self.shows_grid.clear_widgets()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, tipo_show, ativo FROM shows ORDER BY nome")
        shows = cursor.fetchall()
        conn.close()

        if not shows:
            self.shows_grid.add_widget(Label(text="Nenhum show cadastrado.", color=COLOR_TEXT_DARK))
            return

        for show in shows:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=80, spacing=10, padding=5)
            
            # Show info
            info_layout = BoxLayout(orientation="vertical", size_hint_x=0.7)
            info_layout.add_widget(Label(
                text=show["nome"],
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY if show["ativo"] == 1 else COLOR_DISABLED,
                halign="left",
                text_size=(Window.width * 0.6, None)
            ))
            info_layout.add_widget(Label(
                text=f"Tipo: {show['tipo_show']} | Status: {'Ativo' if show['ativo'] == 1 else 'Inativo'}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                text_size=(Window.width * 0.6, None)
            ))
            item.add_widget(info_layout)
            
            # Action buttons
            buttons_layout = BoxLayout(orientation="vertical", size_hint_x=0.3, spacing=5)
            edit_button = Button(text="Editar", size_hint_y=None, height=35, background_color=COLOR_ACCENT)
            edit_button.bind(on_press=lambda _, id=show["id"]: self.open_edit_show_popup(id))
            
            toggle_button = Button(
                text="Desativar" if show["ativo"] == 1 else "Ativar", 
                size_hint_y=None, 
                height=35, 
                background_color=COLOR_SECONDARY if show["ativo"] == 1 else COLOR_PRIMARY
            )
            toggle_button.bind(on_press=lambda _, id=show["id"], active=show["ativo"]: self.toggle_show_status(id, active))
            
            buttons_layout.add_widget(edit_button)
            buttons_layout.add_widget(toggle_button)
            item.add_widget(buttons_layout)
            
            self.shows_grid.add_widget(item)

    def open_add_show_popup(self, instance):
        popup = ShowFormPopup(mode="add", callback=self.load_shows)
        popup.open()

    def open_edit_show_popup(self, show_id):
        popup = ShowFormPopup(mode="edit", show_id=show_id, callback=self.load_shows)
        popup.open()

    def toggle_show_status(self, show_id, current_status):
        new_status = 0 if current_status == 1 else 1
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE shows SET ativo = ? WHERE id = ?", (new_status, show_id))
            conn.commit()
            self.load_shows()  # Refresh the list
        except Exception as e:
            print(f"Error toggling show status: {e}")
        finally:
            conn.close()

class ShowFormPopup(Popup):
    def __init__(self, mode="add", show_id=None, callback=None, **kwargs):
        self.mode = mode
        self.show_id = show_id
        self.callback = callback
        
        title = "Adicionar Novo Show" if mode == "add" else "Editar Show"
        super(ShowFormPopup, self).__init__(title=title, size_hint=(0.9, 0.9), **kwargs)
        
        layout = BoxLayout(orientation="vertical", padding=15, spacing=10)
        
        scroll = ScrollView(size_hint=(1, 1))
        form_layout = BoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter("height"))
        
        # Form fields
        form_layout.add_widget(Label(text="Nome do Show:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.nome_input = TextInput(hint_text="Nome do show", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.nome_input)
        
        form_layout.add_widget(Label(text="Descrição:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.descricao_input = TextInput(hint_text="Descrição do show", multiline=True, size_hint_y=None, height=80)
        form_layout.add_widget(self.descricao_input)
        
        form_layout.add_widget(Label(text="Tipo de Show:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.tipo_show_input = TextInput(hint_text="Ex: Musical, Teatro, Desfile", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.tipo_show_input)
        
        form_layout.add_widget(Label(text="Localização:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.localizacao_input = TextInput(hint_text="Local onde o show é realizado", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.localizacao_input)
        
        form_layout.add_widget(Label(text="Horários (separados por vírgula):", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.horarios_input = TextInput(hint_text="Ex: 14:00, 17:00, 20:00", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.horarios_input)
        
        form_layout.add_widget(Label(text="Duração (minutos):", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.duracao_input = TextInput(hint_text="Ex: 60", input_filter="int", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.duracao_input)
        
        form_layout.add_widget(Label(text="URL da Imagem:", size_hint_y=None, height=30, halign="left", text_size=(Window.width * 0.8, None)))
        self.url_imagem_input = TextInput(hint_text="Caminho para a imagem", multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.url_imagem_input)
        
        self.ativo_checkbox = BoxLayout(orientation="horizontal", size_hint_y=None, height=40)
        self.ativo_checkbox.add_widget(Label(text="Ativo:", size_hint_x=0.3))
        self.ativo_value = True
        self.ativo_button = Button(text="Sim", background_color=COLOR_ACCENT)
        self.ativo_button.bind(on_press=self.toggle_ativo)
        self.ativo_checkbox.add_widget(self.ativo_button)
        form_layout.add_widget(self.ativo_checkbox)
        
        scroll.add_widget(form_layout)
        layout.add_widget(scroll)
        
        # Buttons
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        save_button = StyledButton(text="Salvar")
        save_button.bind(on_press=self.save_show)
        cancel_button = Button(text="Cancelar", background_color=COLOR_SECONDARY, color=COLOR_TEXT_DARK)
        cancel_button.bind(on_press=self.dismiss)
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(cancel_button)
        layout.add_widget(buttons_layout)
        
        self.status_label = Label(text="", size_hint_y=None, height=30, color=COLOR_ACCENT)
        layout.add_widget(self.status_label)
        
        self.content = layout
        
        # If editing, load show data
        if mode == "edit" and show_id:
            self.load_show_data()
    
    def toggle_ativo(self, instance):
        self.ativo_value = not self.ativo_value
        instance.text = "Sim" if self.ativo_value else "Não"
        instance.background_color = COLOR_ACCENT if self.ativo_value else COLOR_SECONDARY
    
    def load_show_data(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shows WHERE id = ?", (self.show_id,))
        show = cursor.fetchone()
        conn.close()
        
        if show:
            self.nome_input.text = show["nome"]
            self.descricao_input.text = show["descricao"] if show["descricao"] else ""
            self.tipo_show_input.text = show["tipo_show"] if show["tipo_show"] else ""
            self.localizacao_input.text = show["localizacao"] if show["localizacao"] else ""
            self.horarios_input.text = show["horarios"] if show["horarios"] else ""
            self.duracao_input.text = str(show["duracao_minutos"]) if show["duracao_minutos"] else ""
            self.url_imagem_input.text = show["url_imagem_divulgacao"] if show["url_imagem_divulgacao"] else ""
            self.ativo_value = show["ativo"] == 1
            self.ativo_button.text = "Sim" if self.ativo_value else "Não"
            self.ativo_button.background_color = COLOR_ACCENT if self.ativo_value else COLOR_SECONDARY
    
    def save_show(self, instance):
        # Validate required fields
        if not self.nome_input.text:
            self.status_label.text = "Nome do show é obrigatório."
            return
        
        # Prepare data
        nome = self.nome_input.text
        descricao = self.descricao_input.text
        tipo_show = self.tipo_show_input.text
        localizacao = self.localizacao_input.text
        horarios = self.horarios_input.text
        
        try:
            duracao = int(self.duracao_input.text) if self.duracao_input.text else None
        except ValueError:
            self.status_label.text = "Duração deve ser um número inteiro."
            return
        
        url_imagem = self.url_imagem_input.text
        ativo = 1 if self.ativo_value else 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if self.mode == "add":
                cursor.execute(
                    "INSERT INTO shows (nome, descricao, tipo_show, localizacao, horarios, duracao_minutos, url_imagem_divulgacao, ativo) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (nome, descricao, tipo_show, localizacao, horarios, duracao, url_imagem, ativo)
                )
                self.status_label.text = "Show adicionado com sucesso!"
            else:
                cursor.execute(
                    "UPDATE shows SET nome = ?, descricao = ?, tipo_show = ?, localizacao = ?, "
                    "horarios = ?, duracao_minutos = ?, url_imagem_divulgacao = ?, ativo = ? "
                    "WHERE id = ?",
                    (nome, descricao, tipo_show, localizacao, horarios, duracao, url_imagem, ativo, self.show_id)
                )
                self.status_label.text = "Show atualizado com sucesso!"
            
            conn.commit()
            
            # Call callback to refresh the list
            if self.callback:
                self.callback()
                
            # Close popup after a short delay
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.dismiss(), 1.5)
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                self.status_label.text = "Erro: Já existe um show com este nome."
            else:
                self.status_label.text = f"Erro de integridade: {e}"
        except Exception as e:
            self.status_label.text = f"Erro ao salvar: {e}"
        finally:
            conn.close()

# --- Food Courts Screens ---
class FoodCourtsListScreen(Screen):
    def __init__(self, **kwargs):
        super(FoodCourtsListScreen, self).__init__(**kwargs)
        self.name = "food_courts_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Lanchonetes do Parque"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.food_courts_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.food_courts_grid.bind(minimum_height=self.food_courts_grid.setter("height"))
        scroll_view.add_widget(self.food_courts_grid)
        layout.add_widget(scroll_view)
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_food_courts()

    def load_food_courts(self):
        self.food_courts_grid.clear_widgets()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, descricao, tipo_culinaria, url_imagem_logo, horario_funcionamento FROM lanchonetes WHERE ativo = 1 ORDER BY nome")
        food_courts = cursor.fetchall()
        conn.close()

        if not food_courts:
            self.food_courts_grid.add_widget(Label(text="Nenhuma lanchonete disponível no momento.", color=COLOR_TEXT_DARK))
            return

        for food_court in food_courts:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=150, spacing=10, padding=5)
            
            # Image
            img_path = food_court["url_imagem_logo"] if food_court["url_imagem_logo"] and os.path.exists(food_court["url_imagem_logo"]) else os.path.join(ASSETS_PATH, "food_court_placeholder.png")
            if os.path.exists(img_path):
                img = KivyImage(source=img_path, size_hint_x=0.4)
            else:
                img = Label(text="Imagem\nNão Disponível", size_hint_x=0.4, color=COLOR_TEXT_DARK)
            item.add_widget(img)
            
            # Info
            info_layout = BoxLayout(orientation="vertical", size_hint_x=0.6, spacing=5)
            info_layout.add_widget(Label(
                text=food_court["nome"],
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            info_layout.add_widget(Label(
                text=food_court["descricao"] if food_court["descricao"] else "Sem descrição",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            info_layout.add_widget(Label(
                text=f"Tipo: {food_court['tipo_culinaria']} | Horário: {food_court['horario_funcionamento']}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                halign="left",
                valign="top",
                text_size=(Window.width * 0.5, None)
            ))
            
            # Details button
            details_button = StyledButton(text="Ver Cardápio", size_hint_y=None, height=40)
            details_button.bind(on_press=lambda _, id=food_court["id"]: self.show_menu(id))
            info_layout.add_widget(details_button)
            
            item.add_widget(info_layout)
            self.food_courts_grid.add_widget(item)

    def show_menu(self, food_court_id):
        app = App.get_running_app()
        app.selected_lanchonete_id = food_court_id
        app.previous_screen = self.name
        self.manager.current = "food_court_detail"

class FoodCourtDetailScreen(Screen):
    def __init__(self, **kwargs):
        super(FoodCourtDetailScreen, self).__init__(**kwargs)
        self.name = "food_court_detail"
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # Header with title and back button
        self.header_label = HeaderLabel(text="Cardápio")
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(self.header_label)
        
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "food_courts_list"))
        header_layout.add_widget(back_button)
        
        self.layout.add_widget(header_layout)

        # Scrollable content area
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.menu_content = BoxLayout(
            orientation="vertical", 
            size_hint_y=None, 
            spacing=10,
            padding=10
        )
        self.menu_content.bind(minimum_height=self.menu_content.setter('height'))
        self.scroll_view.add_widget(self.menu_content)
        self.layout.add_widget(self.scroll_view)

        self.add_widget(self.layout)
        
        # Average rating component
        self.avg_rating_label = Label(
            text="Avaliação Média: N/A",
            font_size="15sp",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )

    def on_enter(self, *args):
        self.load_menu()

    def load_menu(self):
        self.menu_content.clear_widgets()
        food_court_id = App.get_running_app().selected_lanchonete_id
        if not food_court_id:
            self.menu_content.add_widget(Label(text="Nenhuma lanchonete selecionada.", color=COLOR_TEXT_DARK))
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lanchonetes WHERE id = ?", (food_court_id,))
        food_court = cursor.fetchone()
        
        if not food_court:
            self.menu_content.add_widget(Label(text="Lanchonete não encontrada.", color=COLOR_TEXT_DARK))
            conn.close()
            return
            
        self.header_label.text = f"Cardápio - {food_court['nome']}"
        
        # Food court info
        if food_court["url_imagem_logo"] and os.path.exists(food_court["url_imagem_logo"]):
            self.menu_content.add_widget(KivyImage(
                source=food_court["url_imagem_logo"],
                size_hint_y=None,
                height=150
            ))
        
        self.menu_content.add_widget(Label(
            text=food_court["nome"],
            font_size="20sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        ))
        
        self.menu_content.add_widget(Label(
            text=food_court["descricao"] if food_court["descricao"] else "Sem descrição",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.menu_content.add_widget(Label(
            text=f"Tipo: {food_court['tipo_culinaria']} | Horário: {food_court['horario_funcionamento']}",
            font_size="14sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30
        ))
        
        # Get menu items grouped by category
        cursor.execute(
            "SELECT categoria, COUNT(*) as item_count FROM cardapio_itens "
            "WHERE id_lanchonete = ? AND disponivel = 1 "
            "GROUP BY categoria ORDER BY categoria",
            (food_court_id,)
        )
        categories = cursor.fetchall()
        
        # Get ratings
        cursor.execute(
            "SELECT AVG(nota) as media, COUNT(id) as total_avaliacoes "
            "FROM avaliacoes WHERE id_referencia = ? AND tipo_referencia = ?",
            (food_court_id, "lanchonete")
        )
        rating_data = cursor.fetchone()
        
        # Menu items
        if categories:
            self.menu_content.add_widget(Label(
                text="Cardápio",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=40,
                halign="left"
            ))
            
            for category in categories:
                # Category header
                self.menu_content.add_widget(Label(
                    text=category["categoria"],
                    font_size="16sp",
                    bold=True,
                    color=COLOR_ACCENT,
                    size_hint_y=None,
                    height=30,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                # Get items in this category
                cursor.execute(
                    "SELECT id, nome_item, descricao_item, preco, url_imagem_item "
                    "FROM cardapio_itens "
                    "WHERE id_lanchonete = ? AND categoria = ? AND disponivel = 1 "
                    "ORDER BY nome_item",
                    (food_court_id, category["categoria"])
                )
                items = cursor.fetchall()
                
                for item in items:
                    item_layout = BoxLayout(
                        orientation="horizontal", 
                        size_hint_y=None, 
                        height=80, 
                        spacing=10,
                        padding=5
                    )
                    
                    # Item image if available
                    if item["url_imagem_item"] and os.path.exists(item["url_imagem_item"]):
                        img = KivyImage(
                            source=item["url_imagem_item"],
                            size_hint_x=0.2
                        )
                        item_layout.add_widget(img)
                    
                    # Item details
                    item_info = BoxLayout(
                        orientation="vertical",
                        size_hint_x=0.6 if item["url_imagem_item"] else 0.8
                    )
                    
                    item_info.add_widget(Label(
                        text=item["nome_item"],
                        font_size="16sp",
                        bold=True,
                        color=COLOR_TEXT_DARK,
                        halign="left",
                        size_hint_y=None,
                        height=25,
                        text_size=(Window.width * 0.5, None)
                    ))
                    
                    if item["descricao_item"]:
                        desc_label = Label(
                            text=item["descricao_item"],
                            font_size="14sp",
                            color=COLOR_TEXT_DARK,
                            halign="left",
                            size_hint_y=None,
                            text_size=(Window.width * 0.5, None)
                        )
                        desc_label.bind(texture_size=desc_label.setter('size'))
                        item_info.add_widget(desc_label)
                    
                    item_layout.add_widget(item_info)
                    
                    # Price
                    price_label = Label(
                        text=f"R$ {item['preco']:.2f}".replace(".", ","),
                        font_size="16sp",
                        bold=True,
                        color=COLOR_ACCENT,
                        size_hint_x=0.2,
                        halign="right",
                        text_size=(Window.width * 0.2, None)
                    )
                    item_layout.add_widget(price_label)
                    
                    self.menu_content.add_widget(item_layout)
                    
                    # Separator
                    separator = BoxLayout(size_hint_y=None, height=1)
                    with separator.canvas:
                        Color(0.9, 0.9, 0.9, 1)
                        Rectangle(pos=separator.pos, size=separator.size)
                    self.menu_content.add_widget(separator)
        else:
            self.menu_content.add_widget(Label(
                text="Cardápio não disponível no momento.",
                font_size="16sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=40
            ))
        
        # Average rating
        if rating_data and rating_data["media"] is not None:
            self.avg_rating_label.text = f"Avaliação Média: {rating_data['media']:.1f}/5 ({rating_data['total_avaliacoes']} avaliações)"
        else:
            self.avg_rating_label.text = "Avaliação Média: Nenhuma avaliação ainda."
        self.menu_content.add_widget(self.avg_rating_label)
        
        # Rating button
        rate_button = StyledButton(
            text="Avaliar Lanchonete",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        rate_button.bind(on_press=self.open_rating_popup)
        self.menu_content.add_widget(rate_button)
        
        conn.close()

    def open_rating_popup(self, instance):
        food_court_id = App.get_running_app().selected_lanchonete_id
        if food_court_id:
            popup = RatingPopup(id_referencia=food_court_id, tipo_referencia="lanchonete")
            popup.open()

# --- Tickets Screens ---
# --- Tickets Screens ---
class TicketsListScreen(Screen):
    def __init__(self, **kwargs):
        super(TicketsListScreen, self).__init__(**kwargs)
        self.name = "tickets_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Ingressos"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Tabs for different ticket functions
        tabs_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        
        buy_button = StyledButton(text="Comprar Ingressos")
        buy_button.bind(on_press=lambda x: self.show_tab("buy"))
        
        my_tickets_button = Button(
            text="Meus Ingressos", 
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        my_tickets_button.bind(on_press=lambda x: self.show_tab("my_tickets"))
        
        tabs_layout.add_widget(buy_button)
        tabs_layout.add_widget(my_tickets_button)
        layout.add_widget(tabs_layout)

        # Content area that will change based on selected tab
        self.content_area = BoxLayout(orientation="vertical", padding=10)
        layout.add_widget(self.content_area)
        
        self.add_widget(layout)
        
        # Default to buy tab
        self.current_tab = "buy"

    def on_enter(self, *args):
        self.show_tab(self.current_tab)

    def show_tab(self, tab_name):
        self.current_tab = tab_name
        self.content_area.clear_widgets()
        
        if tab_name == "buy":
            self.show_buy_tickets()
        elif tab_name == "my_tickets":
            self.show_my_tickets()

    def show_buy_tickets(self):
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        tickets_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        tickets_grid.bind(minimum_height=tickets_grid.setter("height"))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, descricao, preco_base, idade_minima, idade_maxima FROM tipos_ingressos WHERE ativo = 1 ORDER BY preco_base")
        ticket_types = cursor.fetchall()
        conn.close()
        
        if not ticket_types:
            tickets_grid.add_widget(Label(text="Nenhum tipo de ingresso disponível no momento.", color=COLOR_TEXT_DARK))
        else:
            tickets_grid.add_widget(Label(
                text="Selecione o tipo de ingresso para comprar:",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=40
            ))
            
            for ticket in ticket_types:
                item = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5, padding=10)
                item.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
                item.canvas.before.add(Rectangle(pos=item.pos, size=item.size))
                
                item.add_widget(Label(
                    text=ticket["nome"],
                    font_size="18sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=30
                ))
                
                item.add_widget(Label(
                    text=ticket["descricao"] if ticket["descricao"] else "Sem descrição adicional.",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=40,
                    text_size=(Window.width * 0.9, None)
                ))
                
                details_layout = BoxLayout(size_hint_y=None, height=30)
                
                age_text = ""
                if ticket["idade_minima"] > 0 and ticket["idade_maxima"] < 120:
                    age_text = f"Idade: {ticket['idade_minima']} a {ticket['idade_maxima']} anos"
                elif ticket["idade_minima"] > 0:
                    age_text = f"Idade mínima: {ticket['idade_minima']} anos"
                elif ticket["idade_maxima"] < 120:
                    age_text = f"Idade máxima: {ticket['idade_maxima']} anos"
                
                if age_text:
                    details_layout.add_widget(Label(
                        text=age_text,
                        font_size="14sp",
                        color=COLOR_TEXT_DARK,
                        halign="left",
                        text_size=(Window.width * 0.5, None)
                    ))
                
                price_text = "Gratuito" if ticket["preco_base"] == 0 else f"R$ {ticket['preco_base']:.2f}".replace(".", ",")
                details_layout.add_widget(Label(
                    text=price_text,
                    font_size="16sp",
                    bold=True,
                    color=COLOR_ACCENT,
                    halign="right",
                    text_size=(Window.width * 0.4, None)
                ))
                
                item.add_widget(details_layout)
                
                select_button = StyledButton(
                    text="Selecionar",
                    size_hint_y=None,
                    height=40
                )
                select_button.bind(on_press=lambda _, id=ticket["id"], name=ticket["nome"], price=ticket["preco_base"]: self.select_ticket(id, name, price))
                item.add_widget(select_button)
                
                tickets_grid.add_widget(item)
        
        scroll_view.add_widget(tickets_grid)
        self.content_area.add_widget(scroll_view)

    def show_my_tickets(self):
        user_id = App.get_running_app().user_id
        if not user_id:
            self.content_area.add_widget(Label(text="Você precisa estar logado para ver seus ingressos.", color=COLOR_TEXT_DARK))
            return
            
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        tickets_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        tickets_grid.bind(minimum_height=tickets_grid.setter("height"))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ci.id, ci.data_compra, ci.valor_total_compra, ci.status_pagamento,
                   COUNT(ici.id) as total_ingressos
            FROM compras_ingressos ci
            LEFT JOIN itens_compra_ingressos ici ON ci.id = ici.id_compra_ingresso
            WHERE ci.id_usuario_sistema = ?
            GROUP BY ci.id
            ORDER BY ci.data_compra DESC
        """, (user_id,))
        purchases = cursor.fetchall()
        
        if not purchases:
            tickets_grid.add_widget(Label(text="Você ainda não possui ingressos comprados.", color=COLOR_TEXT_DARK))
        else:
            for purchase in purchases:
                item = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=5, padding=10)
                item.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
                item.canvas.before.add(Rectangle(pos=item.pos, size=item.size))
                
                # Format date
                purchase_date = datetime.strptime(purchase["data_compra"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                
                item.add_widget(Label(
                    text=f"Compra #{purchase['id']} - {purchase_date}",
                    font_size="16sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=30
                ))
                
                item.add_widget(Label(
                    text=f"Total: R$ {purchase['valor_total_compra']:.2f}".replace(".", ","),
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25
                ))
                
                status_color = COLOR_ACCENT if purchase["status_pagamento"] == "Aprovado" else COLOR_SECONDARY
                item.add_widget(Label(
                    text=f"Status: {purchase['status_pagamento']} | Ingressos: {purchase['total_ingressos']}",
                    font_size="14sp",
                    color=status_color,
                    size_hint_y=None,
                    height=25
                ))
                
                details_button = StyledButton(
                    text="Ver Detalhes",
                    size_hint_y=None,
                    height=30
                )
                details_button.bind(on_press=lambda _, id=purchase["id"]: self.show_purchase_details(id))
                item.add_widget(details_button)
                
                tickets_grid.add_widget(item)
        
        conn.close()
        scroll_view.add_widget(tickets_grid)
        self.content_area.add_widget(scroll_view)

    def select_ticket(self, ticket_id, ticket_name, ticket_price):
        app = App.get_running_app()
        app.selected_ticket_type_id = ticket_id
        app.selected_ticket_type_name = ticket_name
        app.selected_ticket_type_price = ticket_price
        app.previous_screen = self.name
        self.manager.current = "ticket_purchase"

    def show_purchase_details(self, purchase_id):
        app = App.get_running_app()
        app.selected_purchase_id = purchase_id
        app.previous_screen = self.name
        self.manager.current = "purchase_details"

class TicketPurchaseScreen(Screen):
    def __init__(self, **kwargs):
        super(TicketPurchaseScreen, self).__init__(**kwargs)
        self.name = "ticket_purchase"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.header_label = HeaderLabel(text="Comprar Ingressos")
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "tickets_list"))
        header_layout.add_widget(self.header_label)
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Form content
        form_layout = BoxLayout(orientation="vertical", spacing=15, padding=10)
        
        # Ticket info
        self.ticket_info = Label(
            text="Selecione a quantidade e data de visita:",
            font_size="18sp",
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.ticket_info)
        
        # Quantity selector
        qty_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        qty_layout.add_widget(Label(text="Quantidade:", size_hint_x=0.4))
        
        qty_selector = BoxLayout(size_hint_x=0.6)
        self.decrease_btn = Button(text="-", size_hint_x=0.3)
        self.decrease_btn.bind(on_press=self.decrease_quantity)
        
        self.quantity_label = Label(text="1", size_hint_x=0.4)
        
        self.increase_btn = Button(text="+", size_hint_x=0.3)
        self.increase_btn.bind(on_press=self.increase_quantity)
        
        qty_selector.add_widget(self.decrease_btn)
        qty_selector.add_widget(self.quantity_label)
        qty_selector.add_widget(self.increase_btn)
        
        qty_layout.add_widget(qty_selector)
        form_layout.add_widget(qty_layout)
        
        # Date selector
        date_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        date_layout.add_widget(Label(text="Data de Visita:", size_hint_x=0.4))
        
        # Create a date spinner with next 30 days
        import datetime as dt
        self.date_spinner = Spinner(
            text=date.today().strftime("%d/%m/%Y"),
            values=[
                (date.today() + dt.timedelta(days=i)).strftime("%d/%m/%Y")
                for i in range(30)
            ],
            size_hint_x=0.6
        )
        date_layout.add_widget(self.date_spinner)
        form_layout.add_widget(date_layout)
        
        # Total price
        self.total_price_label = Label(
            text="Total: R$ 0,00",
            font_size="18sp",
            bold=True,
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.total_price_label)
        
        # Payment method
        payment_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        payment_layout.add_widget(Label(text="Forma de Pagamento:", size_hint_x=0.4))
        
        self.payment_spinner = Spinner(
            text="Cartão de Crédito",
            values=["Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"],
            size_hint_x=0.6
        )
        payment_layout.add_widget(self.payment_spinner)
        form_layout.add_widget(payment_layout)
        
        # Purchase button
        self.purchase_button = StyledButton(
            text="Finalizar Compra",
            size_hint_y=None,
            height=50
        )
        self.purchase_button.bind(on_press=self.process_purchase)
        form_layout.add_widget(self.purchase_button)
        
        # Status message
        self.status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        form_layout.add_widget(self.status_label)
        
        layout.add_widget(form_layout)
        self.add_widget(layout)
        
        # Initialize
        self.quantity = 1
        self.update_total()

    def on_enter(self, *args):
        app = App.get_running_app()
        self.ticket_id = app.selected_ticket_type_id
        self.ticket_name = app.selected_ticket_type_name
        self.ticket_price = app.selected_ticket_type_price
        
        self.header_label.text = f"Comprar - {self.ticket_name}"
        self.ticket_info.text = f"Ingresso: {self.ticket_name} - R$ {self.ticket_price:.2f}".replace(".", ",")
        self.update_total()

    def decrease_quantity(self, instance):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.text = str(self.quantity)
            self.update_total()

    def increase_quantity(self, instance):
        self.quantity += 1
        self.quantity_label.text = str(self.quantity)
        self.update_total()

    def update_total(self):
        total = self.quantity * self.ticket_price
        self.total_price_label.text = f"Total: R$ {total:.2f}".replace(".", ",")

    def process_purchase(self, instance):
        app = App.get_running_app()
        user_id = app.user_id
        
        if not user_id:
            self.status_label.text = "Você precisa estar logado para comprar ingressos."
            return
            
        # Get selected date in YYYY-MM-DD format
        selected_date = datetime.strptime(self.date_spinner.text, "%d/%m/%Y").strftime("%Y-%m-%d")
        payment_method = self.payment_spinner.text
        total_price = self.quantity * self.ticket_price
        
        # Generate a unique transaction code
        import uuid
        transaction_code = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Create purchase record
            cursor.execute(
                "INSERT INTO compras_ingressos (id_usuario_sistema, data_compra, valor_total_compra, metodo_pagamento, status_pagamento, codigo_transacao) "
                "VALUES (?, CURRENT_TIMESTAMP, ?, ?, 'Aprovado', ?)",
                (user_id, total_price, payment_method, transaction_code)
            )
            purchase_id = cursor.lastrowid
            
            # Create ticket items
            for i in range(self.quantity):
                ticket_code = f"{transaction_code}-{i+1}"
                cursor.execute(
                    "INSERT INTO itens_compra_ingressos (id_compra_ingresso, id_tipo_ingresso, quantidade, preco_unitario_cobrado, data_utilizacao_prevista, codigo_ingresso_unico) "
                    "VALUES (?, ?, 1, ?, ?, ?)",
                    (purchase_id, self.ticket_id, self.ticket_price, selected_date, ticket_code)
                )
            
            conn.commit()
            self.status_label.text = "Compra realizada com sucesso!"
            
            # Show success popup
            self.show_success_popup(purchase_id)
            
        except Exception as e:
            conn.rollback()
            self.status_label.text = f"Erro ao processar compra: {e}"
        finally:
            conn.close()

    def show_success_popup(self, purchase_id):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        content.add_widget(Label(
            text="Compra Realizada com Sucesso!",
            font_size="18sp",
            bold=True,
            color=COLOR_ACCENT
        ))
        content.add_widget(Label(
            text=f"Número da compra: #{purchase_id}",
            font_size="16sp"
        ))
        content.add_widget(Label(
            text="Seus ingressos estão disponíveis na seção 'Meus Ingressos'.",
            font_size="14sp"
        ))
        
        view_button = StyledButton(text="Ver Meus Ingressos")
        view_button.bind(on_press=lambda x: self.go_to_my_tickets())
        
        close_button = Button(
            text="Fechar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        buttons_layout.add_widget(view_button)
        buttons_layout.add_widget(close_button)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Compra Confirmada",
            content=content,
            size_hint=(0.9, 0.5),
            auto_dismiss=False
        )
        
        close_button.bind(on_press=popup.dismiss)
        popup.open()

    def go_to_my_tickets(self):
        screen = self.manager.get_screen("tickets_list")
        screen.current_tab = "my_tickets"
        self.manager.current = "tickets_list"

# --- User Profile Screen ---
class MyProfileScreen(Screen):
    def __init__(self, **kwargs):
        super(MyProfileScreen, self).__init__(**kwargs)
        self.name = "my_profile"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Meu Perfil"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)
        
        # Profile content
        scroll_view = ScrollView(size_hint=(1, 1))
        self.profile_content = BoxLayout(orientation="vertical", spacing=15, padding=10, size_hint_y=None)
        self.profile_content.bind(minimum_height=self.profile_content.setter("height"))
        scroll_view.add_widget(self.profile_content)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_profile_data()

    def load_profile_data(self):
        self.profile_content.clear_widgets()
        user_id = App.get_running_app().user_id
        
        if not user_id:
            self.profile_content.add_widget(Label(
                text="Você precisa estar logado para ver seu perfil.",
                color=COLOR_TEXT_DARK
            ))
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute(
            "SELECT username, email_recuperacao, tipo_perfil, data_criacao "
            "FROM usuarios_sistema WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            self.profile_content.add_widget(Label(
                text="Erro ao carregar dados do perfil.",
                color=COLOR_TEXT_DARK
            ))
            conn.close()
            return
        
        # User avatar placeholder
        avatar_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, padding=10)
        avatar_path = os.path.join(ASSETS_PATH, "user_avatar.png")
        
        if os.path.exists(avatar_path):
            avatar_layout.add_widget(KivyImage(
                source=avatar_path,
                size_hint=(None, None),
                size=(100, 100),
                pos_hint={'center_x': 0.5}
            ))
        else:
            avatar_layout.add_widget(Label(
                text="👤",
                font_size="60sp",
                size_hint_y=None,
                height=100
            ))
        
        avatar_layout.add_widget(Label(
            text=user["username"],
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30
        ))
        
        self.profile_content.add_widget(avatar_layout)
        
        # User info section
        info_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=10)
        info_layout.add_widget(Label(
            text="Informações da Conta",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        # Format date
        if user["data_criacao"]:
            try:
                creation_date = datetime.strptime(user["data_criacao"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            except:
                creation_date = user["data_criacao"]
        else:
            creation_date = "N/A"
        
        info_items = [
            f"Email: {user['email_recuperacao']}",
            f"Tipo de Perfil: {user['tipo_perfil']}",
            f"Data de Criação: {creation_date}"
        ]
        
        for item in info_items:
            info_layout.add_widget(Label(
                text=item,
                font_size="16sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
        
        self.profile_content.add_widget(info_layout)
        
        # Get user points from check-ins
        cursor.execute(
            "SELECT SUM(pontos_ganhos) as total_pontos, COUNT(*) as total_checkins "
            "FROM checkins_atracao WHERE id_usuario_sistema = ?",
            (user_id,)
        )
        points_data = cursor.fetchone()
        
        # Points section
        points_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=10)
        points_layout.add_widget(Label(
            text="Pontos e Atividades",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        total_points = points_data["total_pontos"] if points_data and points_data["total_pontos"] else 0
        total_checkins = points_data["total_checkins"] if points_data and points_data["total_checkins"] else 0
        
        points_layout.add_widget(Label(
            text=f"Total de Pontos: {total_points}",
            font_size="16sp",
            color=COLOR_ACCENT,
            bold=True,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        points_layout.add_widget(Label(
            text=f"Check-ins em Atrações: {total_checkins}",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.profile_content.add_widget(points_layout)
        
        # Get recent tickets
        cursor.execute("""
            SELECT ci.data_compra, COUNT(ici.id) as num_tickets, ci.valor_total_compra
            FROM compras_ingressos ci
            LEFT JOIN itens_compra_ingressos ici ON ci.id = ici.id_compra_ingresso
            WHERE ci.id_usuario_sistema = ?
            GROUP BY ci.id
            ORDER BY ci.data_compra DESC
            LIMIT 3
        """, (user_id,))
        recent_tickets = cursor.fetchall()
        
        # Recent tickets section
        if recent_tickets:
            tickets_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=10)
            tickets_layout.bind(minimum_height=tickets_layout.setter("height"))
            
            tickets_layout.add_widget(Label(
                text="Ingressos Recentes",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            for ticket in recent_tickets:
                purchase_date = datetime.strptime(ticket["data_compra"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                
                ticket_item = BoxLayout(
                    orientation="horizontal", 
                    size_hint_y=None, 
                    height=40,
                    spacing=10
                )
                
                ticket_item.add_widget(Label(
                    text=purchase_date,
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_x=0.3,
                    halign="left",
                    text_size=(Window.width * 0.3, None)
                ))
                
                ticket_item.add_widget(Label(
                    text=f"{ticket['num_tickets']} ingresso(s)",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_x=0.4,
                    halign="center",
                    text_size=(Window.width * 0.4, None)
                ))
                
                ticket_item.add_widget(Label(
                    text=f"R$ {ticket['valor_total_compra']:.2f}".replace(".", ","),
                    font_size="14sp",
                    color=COLOR_ACCENT,
                    size_hint_x=0.3,
                    halign="right",
                    text_size=(Window.width * 0.3, None)
                ))
                
                tickets_layout.add_widget(ticket_item)
                tickets_layout.height += 40
            
            view_all_button = StyledButton(
                text="Ver Todos os Ingressos",
                size_hint_y=None,
                height=40
            )
            view_all_button.bind(on_press=self.go_to_tickets)
            tickets_layout.add_widget(view_all_button)
            tickets_layout.height += 50
            
            self.profile_content.add_widget(tickets_layout)
        
        # Account actions
        actions_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=10)
        actions_layout.add_widget(Label(
            text="Ações da Conta",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        change_password_button = StyledButton(
            text="Alterar Senha",
            size_hint_y=None,
            height=40
        )
        change_password_button.bind(on_press=self.show_change_password_popup)
        
        logout_button = Button(
            text="Sair da Conta",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=40
        )
        logout_button.bind(on_press=self.logout)
        
        actions_layout.add_widget(change_password_button)
        actions_layout.add_widget(logout_button)
        
        self.profile_content.add_widget(actions_layout)
        
        conn.close()

    def go_to_tickets(self, instance):
        screen = self.manager.get_screen("tickets_list")
        screen.current_tab = "my_tickets"
        self.manager.current = "tickets_list"

    def show_change_password_popup(self, instance):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        
        content.add_widget(Label(
            text="Alterar Senha",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30
        ))
        
        current_password = TextInput(
            hint_text="Senha Atual",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40
        )
        content.add_widget(current_password)
        
        new_password = TextInput(
            hint_text="Nova Senha",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40
        )
        content.add_widget(new_password)
        
        confirm_password = TextInput(
            hint_text="Confirmar Nova Senha",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40
        )
        content.add_widget(confirm_password)
        
        status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        content.add_widget(status_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        save_button = StyledButton(text="Salvar")
        cancel_button = Button(
            text="Cancelar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(cancel_button)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Alterar Senha",
            content=content,
            size_hint=(0.9, 0.6),
            auto_dismiss=False
        )
        
        def change_password(instance):
            if not current_password.text:
                status_label.text = "Digite sua senha atual."
                return
                
            if not new_password.text:
                status_label.text = "Digite a nova senha."
                return
                
            if new_password.text != confirm_password.text:
                status_label.text = "As senhas não coincidem."
                return
                
            if len(new_password.text) < 6:
                status_label.text = "A senha deve ter pelo menos 6 caracteres."
                return
            
            user_id = App.get_running_app().user_id
            
            # Verify current password
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT senha_hash FROM usuarios_sistema WHERE id = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                status_label.text = "Erro ao verificar usuário."
                conn.close()
                return
            
            current_hash = hashlib.sha256(current_password.text.encode("utf-8")).hexdigest()
            
            if current_hash != user["senha_hash"]:
                status_label.text = "Senha atual incorreta."
                conn.close()
                return
            
            # Update password
            new_hash = hashlib.sha256(new_password.text.encode("utf-8")).hexdigest()
            
            try:
                cursor.execute(
                    "UPDATE usuarios_sistema SET senha_hash = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                conn.commit()
                status_label.text = "Senha alterada com sucesso!"
                
                # Close popup after a short delay
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: popup.dismiss(), 1.5)
                
            except Exception as e:
                status_label.text = f"Erro ao alterar senha: {e}"
            finally:
                conn.close()
        
        save_button.bind(on_press=change_password)
        cancel_button.bind(on_press=popup.dismiss)
        
        popup.open()

    def logout(self, instance):
        app = App.get_running_app()
        app.user_id = None
        app.user_profile = None
        self.manager.current = "login"

# --- Rating Popup ---
class AboutParkScreen(Screen):
    def __init__(self, **kwargs):
        super(AboutParkScreen, self).__init__(**kwargs)
        self.name = "about_park"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Sobre o Parque"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Conteúdo sobre o parque
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        content_layout = BoxLayout(orientation="vertical", spacing=15, padding=10, size_hint_y=None)
        content_layout.bind(minimum_height=content_layout.setter("height"))
        
        # Logo do parque
        logo_path = os.path.join(ASSETS_PATH, "logo_infinity_park_215.png")
        if os.path.exists(logo_path):
            content_layout.add_widget(KivyImage(
                source=logo_path,
                size_hint_y=None,
                height=150
            ))
        
        # Carregar informações do banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chave, titulo, conteudo FROM informacoes_parque ORDER BY id")
        info_items = cursor.fetchall()
        conn.close()
        
        if info_items:
            for item in info_items:
                content_layout.add_widget(Label(
                    text=item["titulo"],
                    font_size="18sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=40,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                content_label = Label(
                    text=item["conteudo"],
                    font_size="15sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                )
                content_label.bind(texture_size=content_label.setter('size'))
                content_layout.add_widget(content_label)
        else:
            # Informações padrão caso não haja dados no banco
            sections = [
                {
                    "title": "Sobre o Infinity Park 215",
                    "content": """O Infinity Park 215 é o seu destino de diversão sem limites! Inaugurado em 2020, nosso parque oferece atrações emocionantes, shows espetaculares e experiências inesquecíveis para toda a família. Venha criar memórias mágicas conosco!

Com mais de 30 atrações distribuídas em 5 áreas temáticas, o Infinity Park 215 foi projetado para proporcionar diversão para todas as idades. Nossa equipe de mais de 500 colaboradores trabalha diariamente para garantir sua segurança e conforto."""
                },
                {
                    "title": "Regras Gerais do Parque",
                    "content": """Para a segurança e conforto de todos, siga nossas regras:

• Não é permitido entrar com alimentos e bebidas (exceto água e alimentos para bebês).
• Respeite as filas e as indicações dos funcionários.
• Proibido fumar fora das áreas designadas.
• Crianças menores de 12 anos devem estar acompanhadas por um adulto responsável.
• Siga todas as instruções de segurança nas atrações.
• Não é permitido pular filas ou guardar lugar para outras pessoas.
• Divirta-se com responsabilidade!"""
                },
                {
                    "title": "Horários de Funcionamento",
                    "content": """• Segunda a Quinta: 10h às 18h
• Sexta: 10h às 22h
• Sábado: 9h às 22h
• Domingo: 9h às 20h

Horários especiais em feriados e datas comemorativas. Consulte o calendário no site oficial ou na bilheteria do parque."""
                },
                {
                    "title": "Contato",
                    "content": """• Telefone: (11) 5555-1234
• E-mail: contato@infinitypark215.com
• Site: www.infinitypark215.com
• Endereço: Av. das Diversões, 215 - Cidade Feliz - SP"""
                }
            ]
            
            for section in sections:
                content_layout.add_widget(Label(
                    text=section["title"],
                    font_size="18sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=40,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                content_label = Label(
                    text=section["content"],
                    font_size="15sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                )
                content_label.bind(texture_size=content_label.setter('size'))
                content_layout.add_widget(content_label)
        
        scroll_view.add_widget(content_layout)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)
class MyItineraryScreen(Screen):
    def __init__(self, **kwargs):
        super(MyItineraryScreen, self).__init__(**kwargs)
        self.name = "my_itinerary"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Meus Itinerários"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Lista de itinerários
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.itineraries_layout = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.itineraries_layout.bind(minimum_height=self.itineraries_layout.setter("height"))
        scroll_view.add_widget(self.itineraries_layout)
        layout.add_widget(scroll_view)
        
        # Botão para criar novo itinerário
        create_button = StyledButton(
            text="Criar Novo Itinerário",
            size_hint_y=None,
            height=50
        )
        create_button.bind(on_press=lambda x: setattr(self.manager, "current", "create_itinerary"))
        layout.add_widget(create_button)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_itineraries()

    def load_itineraries(self):
        self.itineraries_layout.clear_widgets()
        
        user_id = App.get_running_app().user_id
        if not user_id:
            self.itineraries_layout.add_widget(Label(
                text="Você precisa estar logado para ver seus itinerários.",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=50
            ))
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nome, data_criacao, data_visita
            FROM itinerarios
            WHERE id_usuario_sistema = ?
            ORDER BY data_visita DESC
        """, (user_id,))
        itineraries = cursor.fetchall()
        
        if not itineraries:
            self.itineraries_layout.add_widget(Label(
                text="Você ainda não criou nenhum itinerário.",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=50
            ))
            return
        
        for itinerary in itineraries:
            # Formatar datas
            creation_date = datetime.strptime(itinerary["data_criacao"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            visit_date = datetime.strptime(itinerary["data_visita"], "%Y-%m-%d").strftime("%d/%m/%Y")
            
            # Obter itens do itinerário
            cursor.execute("""
                SELECT ii.horario_previsto, ii.ordem, 
                       CASE 
                           WHEN ii.tipo_item = 'atracao' THEN a.nome
                           WHEN ii.tipo_item = 'show' THEN s.nome
                           WHEN ii.tipo_item = 'lanchonete' THEN l.nome
                           ELSE 'Item desconhecido'
                       END as nome_item
                FROM itens_itinerario ii
                LEFT JOIN atracoes a ON ii.tipo_item = 'atracao' AND ii.id_referencia = a.id
                LEFT JOIN shows s ON ii.tipo_item = 'show' AND ii.id_referencia = s.id
                LEFT JOIN lanchonetes l ON ii.tipo_item = 'lanchonete' AND ii.id_referencia = l.id
                WHERE ii.id_itinerario = ?
                ORDER BY ii.ordem
            """, (itinerary["id"],))
            items = cursor.fetchall()
            
            # Criar card do itinerário
            itinerary_card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                padding=10,
                spacing=5
            )
            itinerary_card.bind(minimum_height=itinerary_card.setter("height"))
            
            # Adicionar fundo
            with itinerary_card.canvas.before:
                Color(0.95, 0.95, 0.95, 1)
                self.rect = Rectangle(pos=itinerary_card.pos, size=itinerary_card.size)
            itinerary_card.bind(pos=self.update_rect, size=self.update_rect)
            
            # Cabeçalho do itinerário
            header = BoxLayout(orientation="vertical", size_hint_y=None, height=80)
            
            header.add_widget(Label(
                text=itinerary["nome"],
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            header.add_widget(Label(
                text=f"Data da visita: {visit_date}",
                font_size="15sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=25,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            header.add_widget(Label(
                text=f"Criado em: {creation_date}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=25,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            itinerary_card.add_widget(header)
            
            # Lista de itens
            if items:
                items_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
                items_layout.bind(minimum_height=items_layout.setter("height"))
                
                for item in items:
                    item_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=30, spacing=10)
                    
                    item_row.add_widget(Label(
                        text=item["horario_previsto"],
                        font_size="14sp",
                        color=COLOR_ACCENT,
                        size_hint_x=0.2,
                        halign="left",
                        text_size=(Window.width * 0.15, None)
                    ))
                    
                    item_row.add_widget(Label(
                        text=item["nome_item"],
                        font_size="14sp",
                        color=COLOR_TEXT_DARK,
                        size_hint_x=0.8,
                        halign="left",
                        text_size=(Window.width * 0.7, None)
                    ))
                    
                    items_layout.add_widget(item_row)
                    items_layout.height += 30
                
                itinerary_card.add_widget(items_layout)
                itinerary_card.height = 80 + items_layout.height + 20  # header + items + padding
            else:
                itinerary_card.add_widget(Label(
                    text="Nenhum item adicionado a este itinerário.",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=30
                ))
                itinerary_card.height = 80 + 30 + 20  # header + message + padding
            
            # Botões de ação
            buttons_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=10)
            
            edit_button = Button(
                text="Editar",
                background_color=COLOR_PRIMARY,
                size_hint_x=0.5
            )
            edit_button.bind(on_press=lambda _, id=itinerary["id"]: self.edit_itinerary(id))
            
            delete_button = Button(
                text="Excluir",
                background_color=(0.9, 0.2, 0.2, 1),
                size_hint_x=0.5
            )
            delete_button.bind(on_press=lambda _, id=itinerary["id"]: self.delete_itinerary(id))
            
            buttons_layout.add_widget(edit_button)
            buttons_layout.add_widget(delete_button)
            
            itinerary_card.add_widget(buttons_layout)
            itinerary_card.height += 40 + 10  # buttons + padding
            
            self.itineraries_layout.add_widget(itinerary_card)
        
        conn.close()
    
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def edit_itinerary(self, itinerary_id):
        # Implementação futura - por enquanto apenas mostra mensagem
        popup = Popup(
            title="Funcionalidade em Desenvolvimento",
            content=Label(text="A edição de itinerários será implementada em breve."),
            size_hint=(0.8, 0.4)
        )
        popup.open()
    
    def delete_itinerary(self, itinerary_id):
        # Confirmar exclusão
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        content.add_widget(Label(
            text="Tem certeza que deseja excluir este itinerário?",
            font_size="16sp"
        ))
        
        buttons = BoxLayout(size_hint_y=None, height=40, spacing=10)
        
        confirm_button = Button(
            text="Sim, excluir",
            background_color=(0.9, 0.2, 0.2, 1)
        )
        
        cancel_button = Button(
            text="Cancelar",
            background_color=COLOR_PRIMARY
        )
        
        buttons.add_widget(confirm_button)
        buttons.add_widget(cancel_button)
        content.add_widget(buttons)
        
        popup = Popup(
            title="Confirmar Exclusão",
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        def confirm_delete(instance):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Excluir itens do itinerário
                cursor.execute("DELETE FROM itens_itinerario WHERE id_itinerario = ?", (itinerary_id,))
                
                # Excluir itinerário
                cursor.execute("DELETE FROM itinerarios WHERE id = ?", (itinerary_id,))
                
                conn.commit()
                popup.dismiss()
                self.load_itineraries()  # Recarregar lista
                
            except Exception as e:
                conn.rollback()
                print(f"Erro ao excluir itinerário: {e}")
            finally:
                conn.close()
        
        confirm_button.bind(on_press=confirm_delete)
        cancel_button.bind(on_press=popup.dismiss)
        
        popup.open()


class RatingPopup(Popup):
    def __init__(self, id_referencia, tipo_referencia, **kwargs):
        self.id_referencia = id_referencia
        self.tipo_referencia = tipo_referencia
        
        title_map = {
            "atracao": "Avaliar Atração",
            "show": "Avaliar Show",
            "lanchonete": "Avaliar Lanchonete"
        }
        
        title = title_map.get(tipo_referencia, "Avaliar")
        super(RatingPopup, self).__init__(title=title, size_hint=(0.9, 0.7), **kwargs)
        
        layout = BoxLayout(orientation="vertical", padding=15, spacing=10)
        
        # Rating stars
        layout.add_widget(Label(
            text="Sua Avaliação:",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        ))
        
        stars_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.star_buttons = []
        
        for i in range(1, 6):
            star = Button(
                text="★",
                font_size="24sp",
                background_color=(0, 0, 0, 0),
                color=COLOR_DISABLED
            )
            star.rating_value = i
            star.bind(on_press=self.set_rating)
            stars_layout.add_widget(star)
            self.star_buttons.append(star)
        
        layout.add_widget(stars_layout)
        
        # Comment
        layout.add_widget(Label(
            text="Comentário (opcional):",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.8, None)
        ))
        
        self.comment_input = TextInput(
            hint_text="Escreva seu comentário aqui...",
            multiline=True,
            size_hint_y=None,
            height=100
        )
        layout.add_widget(self.comment_input)
        
        # Status message
        self.status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        layout.add_widget(self.status_label)
        
        # Buttons
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        submit_button = StyledButton(text="Enviar Avaliação")
        submit_button.bind(on_press=self.submit_rating)
        
        cancel_button = Button(
            text="Cancelar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        cancel_button.bind(on_press=self.dismiss)
        
        buttons_layout.add_widget(submit_button)
        buttons_layout.add_widget(cancel_button)
        layout.add_widget(buttons_layout)
        
        self.content = layout
        self.rating = 0

    def set_rating(self, instance):
        self.rating = instance.rating_value
        
        for i, star in enumerate(self.star_buttons):
            if i < self.rating:
                star.color = COLOR_SECONDARY  # Filled star
            else:
                star.color = COLOR_DISABLED  # Empty star

    def submit_rating(self, instance):
        if self.rating == 0:
            self.status_label.text = "Por favor, selecione uma avaliação de 1 a 5 estrelas."
            return
        
        user_id = App.get_running_app().user_id
        if not user_id:
            self.status_label.text = "Você precisa estar logado para avaliar."
            return
        
        comment = self.comment_input.text
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user already rated this item
            cursor.execute(
                "SELECT id FROM avaliacoes WHERE id_usuario_sistema = ? AND id_referencia = ? AND tipo_referencia = ?",
                (user_id, self.id_referencia, self.tipo_referencia)
            )
            existing_rating = cursor.fetchone()
            
            if existing_rating:
                # Update existing rating
                cursor.execute(
                    "UPDATE avaliacoes SET nota = ?, comentario = ?, data_avaliacao = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (self.rating, comment, existing_rating["id"])
                )
                self.status_label.text = "Sua avaliação foi atualizada!"
            else:
                # Create new rating
                cursor.execute(
                    "INSERT INTO avaliacoes (id_usuario_sistema, id_referencia, tipo_referencia, nota, comentario) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, self.id_referencia, self.tipo_referencia, self.rating, comment)
                )
                self.status_label.text = "Avaliação enviada com sucesso!"
            
            conn.commit()
            
            # Close popup after a short delay
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.dismiss(), 1.5)
            
        except Exception as e:
            self.status_label.text = f"Erro ao enviar avaliação: {e}"
        finally:
            conn.close()


# --- Main App ---
# --- Tickets Screens ---
class PurchaseDetailsScreen(Screen):
    def __init__(self, **kwargs):
        super(PurchaseDetailsScreen, self).__init__(**kwargs)
        self.name = "purchase_details"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.header_label = HeaderLabel(text="Detalhes da Compra")
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "tickets_list"))
        header_layout.add_widget(self.header_label)
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Content area
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.content_layout = BoxLayout(orientation="vertical", spacing=15, padding=10, size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter("height"))
        scroll_view.add_widget(self.content_layout)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_purchase_details()

    def load_purchase_details(self):
        self.content_layout.clear_widgets()
        purchase_id = App.get_running_app().selected_purchase_id
        
        if not purchase_id:
            self.content_layout.add_widget(Label(text="Nenhuma compra selecionada.", color=COLOR_TEXT_DARK))
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get purchase info
        cursor.execute("""
            SELECT ci.id, ci.data_compra, ci.valor_total_compra, ci.metodo_pagamento, 
                   ci.status_pagamento, ci.codigo_transacao
            FROM compras_ingressos ci
            WHERE ci.id = ?
        """, (purchase_id,))
        purchase = cursor.fetchone()
        
        if not purchase:
            self.content_layout.add_widget(Label(text="Detalhes da compra não encontrados.", color=COLOR_TEXT_DARK))
            conn.close()
            return
            
        # Format date
        purchase_date = datetime.strptime(purchase["data_compra"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        
        # Purchase header
        self.header_label.text = f"Compra #{purchase_id}"
        
        # Purchase summary
        summary_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5, padding=10)
        summary_layout.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
        summary_layout.canvas.before.add(Rectangle(pos=summary_layout.pos, size=summary_layout.size))
        
        summary_layout.add_widget(Label(
            text=f"Data: {purchase_date}",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        summary_layout.add_widget(Label(
            text=f"Valor Total: R$ {purchase['valor_total_compra']:.2f}".replace(".", ","),
            font_size="16sp",
            bold=True,
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        summary_layout.add_widget(Label(
            text=f"Forma de Pagamento: {purchase['metodo_pagamento']}",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        status_color = COLOR_ACCENT if purchase["status_pagamento"] == "Aprovado" else COLOR_SECONDARY
        summary_layout.add_widget(Label(
            text=f"Status: {purchase['status_pagamento']}",
            font_size="16sp",
            color=status_color,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.content_layout.add_widget(summary_layout)
        
        # Get ticket items
        cursor.execute("""
            SELECT ici.id, ici.quantidade, ici.preco_unitario_cobrado, ici.data_utilizacao_prevista,
                   ici.codigo_ingresso_unico, ici.status_ingresso, ti.nome as tipo_ingresso
            FROM itens_compra_ingressos ici
            JOIN tipos_ingressos ti ON ici.id_tipo_ingresso = ti.id
            WHERE ici.id_compra_ingresso = ?
            ORDER BY ici.id
        """, (purchase_id,))
        tickets = cursor.fetchall()
        
        # Tickets list
        if tickets:
            self.content_layout.add_widget(Label(
                text="Ingressos",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=40,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            for ticket in tickets:
                # Format date
                usage_date = datetime.strptime(ticket["data_utilizacao_prevista"], "%Y-%m-%d").strftime("%d/%m/%Y")
                
                ticket_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5, padding=10)
                ticket_layout.canvas.before.add(Color(0.98, 0.98, 0.98, 1))
                ticket_layout.canvas.before.add(Rectangle(pos=ticket_layout.pos, size=ticket_layout.size))
                
                ticket_layout.add_widget(Label(
                    text=f"Ingresso: {ticket['tipo_ingresso']}",
                    font_size="16sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=30,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                ticket_layout.add_widget(Label(
                    text=f"Valor: R$ {ticket['preco_unitario_cobrado']:.2f}".replace(".", ","),
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                ticket_layout.add_widget(Label(
                    text=f"Data de Utilização: {usage_date}",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                status_color = COLOR_ACCENT if ticket["status_ingresso"] == "Nao Utilizado" else COLOR_SECONDARY
                ticket_layout.add_widget(Label(
                    text=f"Status: {ticket['status_ingresso']}",
                    font_size="14sp",
                    color=status_color,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                ticket_layout.add_widget(Label(
                    text=f"Código: {ticket['codigo_ingresso_unico']}",
                    font_size="12sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                self.content_layout.add_widget(ticket_layout)
        
        conn.close()

class TicketsListScreen(Screen):
    def __init__(self, **kwargs):
        super(TicketsListScreen, self).__init__(**kwargs)
        self.name = "tickets_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Ingressos"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Tabs for different ticket functions
        tabs_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        
        buy_button = StyledButton(text="Comprar Ingressos")
        buy_button.bind(on_press=lambda x: self.show_tab("buy"))
        
        my_tickets_button = Button(
            text="Meus Ingressos", 
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        my_tickets_button.bind(on_press=lambda x: self.show_tab("my_tickets"))
        
        tabs_layout.add_widget(buy_button)
        tabs_layout.add_widget(my_tickets_button)
        layout.add_widget(tabs_layout)

        # Content area that will change based on selected tab
        self.content_area = BoxLayout(orientation="vertical", padding=10)
        layout.add_widget(self.content_area)
        
        self.add_widget(layout)
        
        # Default to buy tab
        self.current_tab = "buy"

    def on_enter(self, *args):
        self.show_tab(self.current_tab)

    def show_tab(self, tab_name):
        self.current_tab = tab_name
        self.content_area.clear_widgets()
        
        if tab_name == "buy":
            self.show_buy_tickets()
        elif tab_name == "my_tickets":
            self.show_my_tickets()

    def show_buy_tickets(self):
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        tickets_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        tickets_grid.bind(minimum_height=tickets_grid.setter("height"))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, descricao, preco_base, idade_minima, idade_maxima FROM tipos_ingressos WHERE ativo = 1 ORDER BY preco_base")
        ticket_types = cursor.fetchall()
        conn.close()
        
        if not ticket_types:
            tickets_grid.add_widget(Label(text="Nenhum tipo de ingresso disponível no momento.", color=COLOR_TEXT_DARK))
        else:
            tickets_grid.add_widget(Label(
                text="Selecione o tipo de ingresso para comprar:",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=40
            ))
            
            for ticket in ticket_types:
                item = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5, padding=10)
                item.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
                item.canvas.before.add(Rectangle(pos=item.pos, size=item.size))
                
                item.add_widget(Label(
                    text=ticket["nome"],
                    font_size="18sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=30
                ))
                
                item.add_widget(Label(
                    text=ticket["descricao"] if ticket["descricao"] else "Sem descrição adicional.",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=40,
                    text_size=(Window.width * 0.9, None)
                ))
                
                details_layout = BoxLayout(size_hint_y=None, height=30)
                
                age_text = ""
                if ticket["idade_minima"] > 0 and ticket["idade_maxima"] < 120:
                    age_text = f"Idade: {ticket['idade_minima']} a {ticket['idade_maxima']} anos"
                elif ticket["idade_minima"] > 0:
                    age_text = f"Idade mínima: {ticket['idade_minima']} anos"
                elif ticket["idade_maxima"] < 120:
                    age_text = f"Idade máxima: {ticket['idade_maxima']} anos"
                
                if age_text:
                    details_layout.add_widget(Label(
                        text=age_text,
                        font_size="14sp",
                        color=COLOR_TEXT_DARK,
                        halign="left",
                        text_size=(Window.width * 0.5, None)
                    ))
                
                price_text = "Gratuito" if ticket["preco_base"] == 0 else f"R$ {ticket['preco_base']:.2f}".replace(".", ",")
                details_layout.add_widget(Label(
                    text=price_text,
                    font_size="16sp",
                    bold=True,
                    color=COLOR_ACCENT,
                    halign="right",
                    text_size=(Window.width * 0.4, None)
                ))
                
                item.add_widget(details_layout)
                
                select_button = StyledButton(
                    text="Selecionar",
                    size_hint_y=None,
                    height=40
                )
                select_button.bind(on_press=lambda _, id=ticket["id"], name=ticket["nome"], price=ticket["preco_base"]: self.select_ticket(id, name, price))
                item.add_widget(select_button)
                
                tickets_grid.add_widget(item)
        
        scroll_view.add_widget(tickets_grid)
        self.content_area.add_widget(scroll_view)

    def show_my_tickets(self):
        user_id = App.get_running_app().user_id
        if not user_id:
            self.content_area.add_widget(Label(text="Você precisa estar logado para ver seus ingressos.", color=COLOR_TEXT_DARK))
            return
            
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        tickets_grid = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        tickets_grid.bind(minimum_height=tickets_grid.setter("height"))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ci.id, ci.data_compra, ci.valor_total_compra, ci.status_pagamento,
                   COUNT(ici.id) as total_ingressos
            FROM compras_ingressos ci
            LEFT JOIN itens_compra_ingressos ici ON ci.id = ici.id_compra_ingresso
            WHERE ci.id_usuario_sistema = ?
            GROUP BY ci.id
            ORDER BY ci.data_compra DESC
        """, (user_id,))
        purchases = cursor.fetchall()
        
        if not purchases:
            tickets_grid.add_widget(Label(text="Você ainda não possui ingressos comprados.", color=COLOR_TEXT_DARK))
        else:
            for purchase in purchases:
                item = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=5, padding=10)
                item.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
                item.canvas.before.add(Rectangle(pos=item.pos, size=item.size))
                
                # Format date
                purchase_date = datetime.strptime(purchase["data_compra"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                
                item.add_widget(Label(
                    text=f"Compra #{purchase['id']} - {purchase_date}",
                    font_size="16sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=30
                ))
                
                item.add_widget(Label(
                    text=f"Total: R$ {purchase['valor_total_compra']:.2f}".replace(".", ","),
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25
                ))
                
                status_color = COLOR_ACCENT if purchase["status_pagamento"] == "Aprovado" else COLOR_SECONDARY
                item.add_widget(Label(
                    text=f"Status: {purchase['status_pagamento']} | Ingressos: {purchase['total_ingressos']}",
                    font_size="14sp",
                    color=status_color,
                    size_hint_y=None,
                    height=25
                ))
                
                details_button = StyledButton(
                    text="Ver Detalhes",
                    size_hint_y=None,
                    height=30
                )
                details_button.bind(on_press=lambda _, id=purchase["id"]: self.show_purchase_details(id))
                item.add_widget(details_button)
                
                tickets_grid.add_widget(item)
        
        conn.close()
        scroll_view.add_widget(tickets_grid)
        self.content_area.add_widget(scroll_view)

    def select_ticket(self, ticket_id, ticket_name, ticket_price):
        app = App.get_running_app()
        app.selected_ticket_type_id = ticket_id
        app.selected_ticket_type_name = ticket_name
        app.selected_ticket_type_price = ticket_price
        app.previous_screen = self.name
        self.manager.current = "ticket_purchase"

    def show_purchase_details(self, purchase_id):
        app = App.get_running_app()
        app.selected_purchase_id = purchase_id
        app.previous_screen = self.name
        self.manager.current = "purchase_details"

class TicketPurchaseScreen(Screen):
    def __init__(self, **kwargs):
        super(TicketPurchaseScreen, self).__init__(**kwargs)
        self.name = "ticket_purchase"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.header_label = HeaderLabel(text="Comprar Ingressos")
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "tickets_list"))
        header_layout.add_widget(self.header_label)
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Form content
        form_layout = BoxLayout(orientation="vertical", spacing=15, padding=10)
        
        # Ticket info
        self.ticket_info = Label(
            text="Selecione a quantidade e data de visita:",
            font_size="18sp",
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.ticket_info)
        
        # Quantity selector
        qty_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        qty_layout.add_widget(Label(text="Quantidade:", size_hint_x=0.4))
        
        qty_selector = BoxLayout(size_hint_x=0.6)
        self.decrease_btn = Button(text="-", size_hint_x=0.3)
        self.decrease_btn.bind(on_press=self.decrease_quantity)
        
        self.quantity_label = Label(text="1", size_hint_x=0.4)
        
        self.increase_btn = Button(text="+", size_hint_x=0.3)
        self.increase_btn.bind(on_press=self.increase_quantity)
        
        qty_selector.add_widget(self.decrease_btn)
        qty_selector.add_widget(self.quantity_label)
        qty_selector.add_widget(self.increase_btn)
        
        qty_layout.add_widget(qty_selector)
        form_layout.add_widget(qty_layout)
        
        # Date selector
        date_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        date_layout.add_widget(Label(text="Data de Visita:", size_hint_x=0.4))
        
        # Create a date spinner with next 30 days
        import datetime as dt
        self.date_spinner = Spinner(
            text=date.today().strftime("%d/%m/%Y"),
            values=[
                (date.today() + dt.timedelta(days=i)).strftime("%d/%m/%Y")
                for i in range(30)
            ],
            size_hint_x=0.6
        )
        date_layout.add_widget(self.date_spinner)
        form_layout.add_widget(date_layout)
        
        # Total price
        self.total_price_label = Label(
            text="Total: R$ 0,00",
            font_size="18sp",
            bold=True,
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.total_price_label)
        
        # Payment method
        payment_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        payment_layout.add_widget(Label(text="Forma de Pagamento:", size_hint_x=0.4))
        
        self.payment_spinner = Spinner(
            text="Cartão de Crédito",
            values=["Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"],
            size_hint_x=0.6
        )
        payment_layout.add_widget(self.payment_spinner)
        form_layout.add_widget(payment_layout)
        
        # Purchase button
        self.purchase_button = StyledButton(
            text="Finalizar Compra",
            size_hint_y=None,
            height=50
        )
        self.purchase_button.bind(on_press=self.process_purchase)
        form_layout.add_widget(self.purchase_button)
        
        # Status message
        self.status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        form_layout.add_widget(self.status_label)
        
        layout.add_widget(form_layout)
        self.add_widget(layout)
        
        # Initialize
        self.quantity = 1
        self.update_total()

    def on_enter(self, *args):
        app = App.get_running_app()
        self.ticket_id = app.selected_ticket_type_id
        self.ticket_name = app.selected_ticket_type_name
        self.ticket_price = app.selected_ticket_type_price
        
        self.header_label.text = f"Comprar - {self.ticket_name}"
        self.ticket_info.text = f"Ingresso: {self.ticket_name} - R$ {self.ticket_price:.2f}".replace(".", ",")
        self.update_total()

    def decrease_quantity(self, instance):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.text = str(self.quantity)
            self.update_total()

    def increase_quantity(self, instance):
        self.quantity += 1
        self.quantity_label.text = str(self.quantity)
        self.update_total()

    def update_total(self):
        total = self.quantity * self.ticket_price
        self.total_price_label.text = f"Total: R$ {total:.2f}".replace(".", ",")

    def process_purchase(self, instance):
        app = App.get_running_app()
        user_id = app.user_id
        
        if not user_id:
            self.status_label.text = "Você precisa estar logado para comprar ingressos."
            return
            
        # Get selected date in YYYY-MM-DD format
        selected_date = datetime.strptime(self.date_spinner.text, "%d/%m/%Y").strftime("%Y-%m-%d")
        payment_method = self.payment_spinner.text
        total_price = self.quantity * self.ticket_price
        
        # Generate a unique transaction code
        import uuid
        transaction_code = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Create purchase record
            cursor.execute(
                "INSERT INTO compras_ingressos (id_usuario_sistema, data_compra, valor_total_compra, metodo_pagamento, status_pagamento, codigo_transacao) "
                "VALUES (?, CURRENT_TIMESTAMP, ?, ?, 'Aprovado', ?)",
                (user_id, total_price, payment_method, transaction_code)
            )
            purchase_id = cursor.lastrowid
            
            # Create ticket items
            for i in range(self.quantity):
                ticket_code = f"{transaction_code}-{i+1}"
                cursor.execute(
                    "INSERT INTO itens_compra_ingressos (id_compra_ingresso, id_tipo_ingresso, quantidade, preco_unitario_cobrado, data_utilizacao_prevista, codigo_ingresso_unico) "
                    "VALUES (?, ?, 1, ?, ?, ?)",
                    (purchase_id, self.ticket_id, self.ticket_price, selected_date, ticket_code)
                )
            
            conn.commit()
            self.status_label.text = "Compra realizada com sucesso!"
            
            # Show success popup
            self.show_success_popup(purchase_id)
            
        except Exception as e:
            conn.rollback()
            self.status_label.text = f"Erro ao processar compra: {e}"
        finally:
            conn.close()

    def show_success_popup(self, purchase_id):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        content.add_widget(Label(
            text="Compra Realizada com Sucesso!",
            font_size="18sp",
            bold=True,
            color=COLOR_ACCENT
        ))
        content.add_widget(Label(
            text=f"Número da compra: #{purchase_id}",
            font_size="16sp"
        ))
        content.add_widget(Label(
            text="Seus ingressos estão disponíveis na seção 'Meus Ingressos'.",
            font_size="14sp"
        ))
        
        view_button = StyledButton(text="Ver Meus Ingressos")
        view_button.bind(on_press=lambda x: self.go_to_my_tickets())
        
        close_button = Button(
            text="Fechar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        buttons_layout.add_widget(view_button)
        buttons_layout.add_widget(close_button)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Compra Confirmada",
            content=content,
            size_hint=(0.9, 0.5),
            auto_dismiss=False
        )
        
        close_button.bind(on_press=popup.dismiss)
        popup.open()

    def go_to_my_tickets(self):
        screen = self.manager.get_screen("tickets_list")
        screen.current_tab = "my_tickets"
        self.manager.current = "tickets_list"

# --- User Profile Screen ---
class MyProfileScreen(Screen):
    def __init__(self, **kwargs):
        super(MyProfileScreen, self).__init__(**kwargs)
        self.name = "my_profile"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Meu Perfil"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)
        
        # Profile content
        scroll_view = ScrollView(size_hint=(1, 1))
        self.profile_content = BoxLayout(orientation="vertical", spacing=15, padding=10, size_hint_y=None)
        self.profile_content.bind(minimum_height=self.profile_content.setter("height"))
        scroll_view.add_widget(self.profile_content)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_profile_data()

    def load_profile_data(self):
        self.profile_content.clear_widgets()
        user_id = App.get_running_app().user_id
        
        if not user_id:
            self.profile_content.add_widget(Label(
                text="Você precisa estar logado para ver seu perfil.",
                color=COLOR_TEXT_DARK
            ))
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute(
            "SELECT username, email_recuperacao, tipo_perfil, data_criacao "
            "FROM usuarios_sistema WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            self.profile_content.add_widget(Label(
                text="Erro ao carregar dados do perfil.",
                color=COLOR_TEXT_DARK
            ))
            conn.close()
            return
        
        # User avatar placeholder
        avatar_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, padding=10)
        avatar_path = os.path.join(ASSETS_PATH, "user_avatar.png")
        
        if os.path.exists(avatar_path):
            avatar_layout.add_widget(KivyImage(
                source=avatar_path,
                size_hint=(None, None),
                size=(100, 100),
                pos_hint={'center_x': 0.5}
            ))
        else:
            avatar_layout.add_widget(Label(
                text="👤",
                font_size="60sp",
                size_hint_y=None,
                height=100
            ))
        
        avatar_layout.add_widget(Label(
            text=user["username"],
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30
        ))
        
        self.profile_content.add_widget(avatar_layout)
        
        # User info section
        info_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=10)
        info_layout.add_widget(Label(
            text="Informações da Conta",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        # Format date
        if user["data_criacao"]:
            try:
                creation_date = datetime.strptime(user["data_criacao"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            except:
                creation_date = user["data_criacao"]
        else:
            creation_date = "N/A"
        
        info_items = [
            f"Email: {user['email_recuperacao']}",
            f"Tipo de Perfil: {user['tipo_perfil']}",
            f"Data de Criação: {creation_date}"
        ]
        
        for item in info_items:
            info_layout.add_widget(Label(
                text=item,
                font_size="16sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
        
        self.profile_content.add_widget(info_layout)
        
        # Get user points from check-ins
        cursor.execute(
            "SELECT SUM(pontos_ganhos) as total_pontos, COUNT(*) as total_checkins "
            "FROM checkins_atracao WHERE id_usuario_sistema = ?",
            (user_id,)
        )
        points_data = cursor.fetchone()
        
        # Points section
        points_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=120, spacing=10)
        points_layout.add_widget(Label(
            text="Pontos e Atividades",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        total_points = points_data["total_pontos"] if points_data and points_data["total_pontos"] else 0
        total_checkins = points_data["total_checkins"] if points_data and points_data["total_checkins"] else 0
        
        points_layout.add_widget(Label(
            text=f"Total de Pontos: {total_points}",
            font_size="16sp",
            color=COLOR_ACCENT,
            bold=True,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        points_layout.add_widget(Label(
            text=f"Check-ins em Atrações: {total_checkins}",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.profile_content.add_widget(points_layout)
        
        # Get recent tickets
        cursor.execute("""
            SELECT ci.data_compra, COUNT(ici.id) as num_tickets, ci.valor_total_compra
            FROM compras_ingressos ci
            LEFT JOIN itens_compra_ingressos ici ON ci.id = ici.id_compra_ingresso
            WHERE ci.id_usuario_sistema = ?
            GROUP BY ci.id
            ORDER BY ci.data_compra DESC
            LIMIT 3
        """, (user_id,))
        recent_tickets = cursor.fetchall()
        
        # Recent tickets section
        if recent_tickets:
            tickets_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=10)
            tickets_layout.bind(minimum_height=tickets_layout.setter("height"))
            
            tickets_layout.add_widget(Label(
                text="Ingressos Recentes",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            for ticket in recent_tickets:
                purchase_date = datetime.strptime(ticket["data_compra"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                
                ticket_item = BoxLayout(
                    orientation="horizontal", 
                    size_hint_y=None, 
                    height=40,
                    spacing=10
                )
                
                ticket_item.add_widget(Label(
                    text=purchase_date,
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_x=0.3,
                    halign="left",
                    text_size=(Window.width * 0.3, None)
                ))
                
                ticket_item.add_widget(Label(
                    text=f"{ticket['num_tickets']} ingresso(s)",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_x=0.4,
                    halign="center",
                    text_size=(Window.width * 0.4, None)
                ))
                
                ticket_item.add_widget(Label(
                    text=f"R$ {ticket['valor_total_compra']:.2f}".replace(".", ","),
                    font_size="14sp",
                    color=COLOR_ACCENT,
                    size_hint_x=0.3,
                    halign="right",
                    text_size=(Window.width * 0.3, None)
                ))
                
                tickets_layout.add_widget(ticket_item)
                tickets_layout.height += 40
            
            view_all_button = StyledButton(
                text="Ver Todos os Ingressos",
                size_hint_y=None,
                height=40
            )
            view_all_button.bind(on_press=self.go_to_tickets)
            tickets_layout.add_widget(view_all_button)
            tickets_layout.height += 50
            
            self.profile_content.add_widget(tickets_layout)
        
        # Account actions
        actions_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=10)
        actions_layout.add_widget(Label(
            text="Ações da Conta",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        change_password_button = StyledButton(
            text="Alterar Senha",
            size_hint_y=None,
            height=40
        )
        change_password_button.bind(on_press=self.show_change_password_popup)
        
        logout_button = Button(
            text="Sair da Conta",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=40
        )
        logout_button.bind(on_press=self.logout)
        
        actions_layout.add_widget(change_password_button)
        actions_layout.add_widget(logout_button)
        
        self.profile_content.add_widget(actions_layout)
        
        conn.close()

    def go_to_tickets(self, instance):
        screen = self.manager.get_screen("tickets_list")
        screen.current_tab = "my_tickets"
        self.manager.current = "tickets_list"

    def show_change_password_popup(self, instance):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        
        content.add_widget(Label(
            text="Alterar Senha",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=30
        ))
        
        current_password = TextInput(
            hint_text="Senha Atual",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40
        )
        content.add_widget(current_password)
        
        new_password = TextInput(
            hint_text="Nova Senha",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40
        )
        content.add_widget(new_password)
        
        confirm_password = TextInput(
            hint_text="Confirmar Nova Senha",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=40
        )
        content.add_widget(confirm_password)
        
        status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        content.add_widget(status_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        save_button = StyledButton(text="Salvar")
        cancel_button = Button(
            text="Cancelar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        
        buttons_layout.add_widget(save_button)
        buttons_layout.add_widget(cancel_button)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Alterar Senha",
            content=content,
            size_hint=(0.9, 0.6),
            auto_dismiss=False
        )
        
        def change_password(instance):
            if not current_password.text:
                status_label.text = "Digite sua senha atual."
                return
                
            if not new_password.text:
                status_label.text = "Digite a nova senha."
                return
                
            if new_password.text != confirm_password.text:
                status_label.text = "As senhas não coincidem."
                return
                
            if len(new_password.text) < 6:
                status_label.text = "A senha deve ter pelo menos 6 caracteres."
                return
            
            user_id = App.get_running_app().user_id
            
            # Verify current password
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT senha_hash FROM usuarios_sistema WHERE id = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                status_label.text = "Erro ao verificar usuário."
                conn.close()
                return
            
            current_hash = hashlib.sha256(current_password.text.encode("utf-8")).hexdigest()
            
            if current_hash != user["senha_hash"]:
                status_label.text = "Senha atual incorreta."
                conn.close()
                return
            
            # Update password
            new_hash = hashlib.sha256(new_password.text.encode("utf-8")).hexdigest()
            
            try:
                cursor.execute(
                    "UPDATE usuarios_sistema SET senha_hash = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                conn.commit()
                status_label.text = "Senha alterada com sucesso!"
                
                # Close popup after a short delay
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: popup.dismiss(), 1.5)
                
            except Exception as e:
                status_label.text = f"Erro ao alterar senha: {e}"
            finally:
                conn.close()
        
        save_button.bind(on_press=change_password)
        cancel_button.bind(on_press=popup.dismiss)
        
        popup.open()

    def logout(self, instance):
        app = App.get_running_app()
        app.user_id = None
        app.user_profile = None
        self.manager.current = "login"

# --- Rating Popup ---
class WarningsListScreen(Screen):
    def __init__(self, **kwargs):
        super(WarningsListScreen, self).__init__(**kwargs)
        self.name = "warnings_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Avisos Importantes"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Lista de avisos
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.warnings_layout = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.warnings_layout.bind(minimum_height=self.warnings_layout.setter("height"))
        scroll_view.add_widget(self.warnings_layout)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_warnings()

    def load_warnings(self):
        self.warnings_layout.clear_widgets()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, titulo, mensagem, tipo_aviso, data_publicacao, data_expiracao
            FROM avisos_parque
            WHERE ativo = 1 AND (data_expiracao IS NULL OR date(data_expiracao) >= date('now'))
            ORDER BY data_publicacao DESC
        """)
        warnings = cursor.fetchall()
        conn.close()
        
        if not warnings:
            self.warnings_layout.add_widget(Label(
                text="Não há avisos importantes no momento.",
                font_size="16sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=50
            ))
            return
        
        for warning in warnings:
            # Determinar cor com base no tipo de aviso
            if warning["tipo_aviso"] == "Urgente":
                bg_color = (0.9, 0.2, 0.2, 0.2)  # Vermelho transparente
                title_color = (0.9, 0.2, 0.2, 1)  # Vermelho
            elif warning["tipo_aviso"] == "Alerta":
                bg_color = (0.9, 0.7, 0.2, 0.2)  # Amarelo transparente
                title_color = (0.9, 0.7, 0.2, 1)  # Amarelo
            else:  # Informativo
                bg_color = (0.2, 0.6, 0.9, 0.2)  # Azul transparente
                title_color = (0.2, 0.6, 0.9, 1)  # Azul
            
            # Formatar data
            pub_date = datetime.strptime(warning["data_publicacao"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            
            # Criar item de aviso
            warning_item = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                padding=10,
                spacing=5
            )
            warning_item.bind(minimum_height=warning_item.setter("height"))
            
            # Adicionar fundo colorido
            with warning_item.canvas.before:
                Color(*bg_color)
                self.rect = Rectangle(pos=warning_item.pos, size=warning_item.size)
            warning_item.bind(pos=self.update_rect, size=self.update_rect)
            
            # Título do aviso
            warning_item.add_widget(Label(
                text=warning["titulo"],
                font_size="18sp",
                bold=True,
                color=title_color,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            # Mensagem do aviso
            message_label = Label(
                text=warning["mensagem"],
                font_size="15sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                halign="left",
                text_size=(Window.width * 0.9, None)
            )
            message_label.bind(texture_size=message_label.setter('size'))
            warning_item.add_widget(message_label)
            
            # Data de publicação
            warning_item.add_widget(Label(
                text=f"Publicado em: {pub_date}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=20,
                halign="right",
                text_size=(Window.width * 0.9, None)
            ))
            
            # Ajustar altura do item
            warning_item.height = 30 + message_label.height + 20 + 20  # título + mensagem + data + padding
            
            self.warnings_layout.add_widget(warning_item)
    
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
class WarningsListScreen(Screen):
    def __init__(self, **kwargs):
        super(WarningsListScreen, self).__init__(**kwargs)
        self.name = "warnings_list"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Avisos Importantes"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Lista de avisos
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.warnings_layout = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=10)
        self.warnings_layout.bind(minimum_height=self.warnings_layout.setter("height"))
        scroll_view.add_widget(self.warnings_layout)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_warnings()

    def load_warnings(self):
        self.warnings_layout.clear_widgets()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, titulo, mensagem, tipo_aviso, data_publicacao, data_expiracao
            FROM avisos_parque
            WHERE ativo = 1 AND (data_expiracao IS NULL OR date(data_expiracao) >= date('now'))
            ORDER BY data_publicacao DESC
        """)
        warnings = cursor.fetchall()
        conn.close()
        
        if not warnings:
            self.warnings_layout.add_widget(Label(
                text="Não há avisos importantes no momento.",
                font_size="16sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=50
            ))
            return
        
        for warning in warnings:
            # Determinar cor com base no tipo de aviso
            if warning["tipo_aviso"] == "Urgente":
                bg_color = (0.9, 0.2, 0.2, 0.2)  # Vermelho transparente
                title_color = (0.9, 0.2, 0.2, 1)  # Vermelho
            elif warning["tipo_aviso"] == "Alerta":
                bg_color = (0.9, 0.7, 0.2, 0.2)  # Amarelo transparente
                title_color = (0.9, 0.7, 0.2, 1)  # Amarelo
            else:  # Informativo
                bg_color = (0.2, 0.6, 0.9, 0.2)  # Azul transparente
                title_color = (0.2, 0.6, 0.9, 1)  # Azul
            
            # Formatar data
            pub_date = datetime.strptime(warning["data_publicacao"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            
            # Criar item de aviso
            warning_item = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                padding=10,
                spacing=5
            )
            warning_item.bind(minimum_height=warning_item.setter("height"))
            
            # Adicionar fundo colorido
            with warning_item.canvas.before:
                Color(*bg_color)
                self.rect = Rectangle(pos=warning_item.pos, size=warning_item.size)
            warning_item.bind(pos=self.update_rect, size=self.update_rect)
            
            # Título do aviso
            warning_item.add_widget(Label(
                text=warning["titulo"],
                font_size="18sp",
                bold=True,
                color=title_color,
                size_hint_y=None,
                height=30,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            # Mensagem do aviso
            message_label = Label(
                text=warning["mensagem"],
                font_size="15sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                halign="left",
                text_size=(Window.width * 0.9, None)
            )
            message_label.bind(texture_size=message_label.setter('size'))
            warning_item.add_widget(message_label)
            
            # Data de publicação
            warning_item.add_widget(Label(
                text=f"Publicado em: {pub_date}",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=20,
                halign="right",
                text_size=(Window.width * 0.9, None)
            ))
            
            # Ajustar altura do item
            warning_item.height = 30 + message_label.height + 20 + 20  # título + mensagem + data + padding
            
            self.warnings_layout.add_widget(warning_item)
    
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class PurchaseDetailsScreen(Screen):
    def __init__(self, **kwargs):
        super(PurchaseDetailsScreen, self).__init__(**kwargs)
        self.name = "purchase_details"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.header_label = HeaderLabel(text="Detalhes da Compra")
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "tickets_list"))
        header_layout.add_widget(self.header_label)
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Content area
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        self.content_layout = BoxLayout(orientation="vertical", spacing=15, padding=10, size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter("height"))
        scroll_view.add_widget(self.content_layout)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.load_purchase_details()

    def load_purchase_details(self):
        self.content_layout.clear_widgets()
        purchase_id = App.get_running_app().selected_purchase_id
        
        if not purchase_id:
            self.content_layout.add_widget(Label(text="Nenhuma compra selecionada.", color=COLOR_TEXT_DARK))
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get purchase info
        cursor.execute("""
            SELECT ci.id, ci.data_compra, ci.valor_total_compra, ci.metodo_pagamento, 
                   ci.status_pagamento, ci.codigo_transacao
            FROM compras_ingressos ci
            WHERE ci.id = ?
        """, (purchase_id,))
        purchase = cursor.fetchone()
        
        if not purchase:
            self.content_layout.add_widget(Label(text="Detalhes da compra não encontrados.", color=COLOR_TEXT_DARK))
            conn.close()
            return
            
        # Format date
        purchase_date = datetime.strptime(purchase["data_compra"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        
        # Purchase header
        self.header_label.text = f"Compra #{purchase_id}"
        
        # Purchase summary
        summary_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5, padding=10)
        summary_layout.canvas.before.add(Color(0.95, 0.95, 0.95, 1))
        summary_layout.canvas.before.add(Rectangle(pos=summary_layout.pos, size=summary_layout.size))
        
        summary_layout.add_widget(Label(
            text=f"Data: {purchase_date}",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        summary_layout.add_widget(Label(
            text=f"Valor Total: R$ {purchase['valor_total_compra']:.2f}".replace(".", ","),
            font_size="16sp",
            bold=True,
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        summary_layout.add_widget(Label(
            text=f"Forma de Pagamento: {purchase['metodo_pagamento']}",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        status_color = COLOR_ACCENT if purchase["status_pagamento"] == "Aprovado" else COLOR_SECONDARY
        summary_layout.add_widget(Label(
            text=f"Status: {purchase['status_pagamento']}",
            font_size="16sp",
            color=status_color,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.content_layout.add_widget(summary_layout)
        
        # Get ticket items
        cursor.execute("""
            SELECT ici.id, ici.quantidade, ici.preco_unitario_cobrado, ici.data_utilizacao_prevista,
                   ici.codigo_ingresso_unico, ici.status_ingresso, ti.nome as tipo_ingresso
            FROM itens_compra_ingressos ici
            JOIN tipos_ingressos ti ON ici.id_tipo_ingresso = ti.id
            WHERE ici.id_compra_ingresso = ?
            ORDER BY ici.id
        """, (purchase_id,))
        tickets = cursor.fetchall()
        
        # Tickets list
        if tickets:
            self.content_layout.add_widget(Label(
                text="Ingressos",
                font_size="18sp",
                bold=True,
                color=COLOR_PRIMARY,
                size_hint_y=None,
                height=40,
                halign="left",
                text_size=(Window.width * 0.9, None)
            ))
            
            for ticket in tickets:
                # Format date
                usage_date = datetime.strptime(ticket["data_utilizacao_prevista"], "%Y-%m-%d").strftime("%d/%m/%Y")
                
                ticket_layout = BoxLayout(orientation="vertical", size_hint_y=None, height=150, spacing=5, padding=10)
                ticket_layout.canvas.before.add(Color(0.98, 0.98, 0.98, 1))
                ticket_layout.canvas.before.add(Rectangle(pos=ticket_layout.pos, size=ticket_layout.size))
                
                ticket_layout.add_widget(Label(
                    text=f"Ingresso: {ticket['tipo_ingresso']}",
                    font_size="16sp",
                    bold=True,
                    color=COLOR_PRIMARY,
                    size_hint_y=None,
                    height=30,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                ticket_layout.add_widget(Label(
                    text=f"Valor: R$ {ticket['preco_unitario_cobrado']:.2f}".replace(".", ","),
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                ticket_layout.add_widget(Label(
                    text=f"Data de Utilização: {usage_date}",
                    font_size="14sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                status_color = COLOR_ACCENT if ticket["status_ingresso"] == "Nao Utilizado" else COLOR_SECONDARY
                ticket_layout.add_widget(Label(
                    text=f"Status: {ticket['status_ingresso']}",
                    font_size="14sp",
                    color=status_color,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                ticket_layout.add_widget(Label(
                    text=f"Código: {ticket['codigo_ingresso_unico']}",
                    font_size="12sp",
                    color=COLOR_TEXT_DARK,
                    size_hint_y=None,
                    height=25,
                    halign="left",
                    text_size=(Window.width * 0.9, None)
                ))
                
                self.content_layout.add_widget(ticket_layout)
        
        conn.close()

class TicketPurchaseScreen(Screen):
    def __init__(self, **kwargs):
        super(TicketPurchaseScreen, self).__init__(**kwargs)
        self.name = "ticket_purchase"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.header_label = HeaderLabel(text="Comprar Ingressos")
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", "tickets_list"))
        header_layout.add_widget(self.header_label)
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Form content
        form_layout = BoxLayout(orientation="vertical", spacing=15, padding=10)
        
        # Ticket info
        self.ticket_info = Label(
            text="Selecione a quantidade e data de visita:",
            font_size="18sp",
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.ticket_info)
        
        # Quantity selector
        qty_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        qty_layout.add_widget(Label(text="Quantidade:", size_hint_x=0.4))
        
        qty_selector = BoxLayout(size_hint_x=0.6)
        self.decrease_btn = Button(text="-", size_hint_x=0.3)
        self.decrease_btn.bind(on_press=self.decrease_quantity)
        
        self.quantity_label = Label(text="1", size_hint_x=0.4)
        
        self.increase_btn = Button(text="+", size_hint_x=0.3)
        self.increase_btn.bind(on_press=self.increase_quantity)
        
        qty_selector.add_widget(self.decrease_btn)
        qty_selector.add_widget(self.quantity_label)
        qty_selector.add_widget(self.increase_btn)
        
        qty_layout.add_widget(qty_selector)
        form_layout.add_widget(qty_layout)
        
        # Date selector
        date_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        date_layout.add_widget(Label(text="Data de Visita:", size_hint_x=0.4))
        
        # Create a date spinner with next 30 days
        import datetime as dt
        self.date_spinner = Spinner(
            text=date.today().strftime("%d/%m/%Y"),
            values=[
                (date.today() + dt.timedelta(days=i)).strftime("%d/%m/%Y")
                for i in range(30)
            ],
            size_hint_x=0.6
        )
        date_layout.add_widget(self.date_spinner)
        form_layout.add_widget(date_layout)
        
        # Total price
        self.total_price_label = Label(
            text="Total: R$ 0,00",
            font_size="18sp",
            bold=True,
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.total_price_label)
        
        # Payment method
        payment_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        payment_layout.add_widget(Label(text="Forma de Pagamento:", size_hint_x=0.4))
        
        self.payment_spinner = Spinner(
            text="Cartão de Crédito",
            values=["Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"],
            size_hint_x=0.6
        )
        payment_layout.add_widget(self.payment_spinner)
        form_layout.add_widget(payment_layout)
        
        # Purchase button
        self.purchase_button = StyledButton(
            text="Finalizar Compra",
            size_hint_y=None,
            height=50
        )
        self.purchase_button.bind(on_press=self.process_purchase)
        form_layout.add_widget(self.purchase_button)
        
        # Status message
        self.status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        form_layout.add_widget(self.status_label)
        
        layout.add_widget(form_layout)
        self.add_widget(layout)
        
        # Initialize
        self.quantity = 1
        # Inicializar ticket_price com valor padrão para evitar o erro
        self.ticket_id = None
        self.ticket_name = ""
        self.ticket_price = 0.0  # Inicialização do atributo ticket_price
        
    def on_enter(self, *args):
        app = App.get_running_app()
        self.ticket_id = app.selected_ticket_type_id
        self.ticket_name = app.selected_ticket_type_name
        self.ticket_price = app.selected_ticket_type_price
        
        self.header_label.text = f"Comprar - {self.ticket_name}"
        self.ticket_info.text = f"Ingresso: {self.ticket_name} - R$ {self.ticket_price:.2f}".replace(".", ",")
        self.update_total()

    def decrease_quantity(self, instance):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.text = str(self.quantity)
            self.update_total()

    def increase_quantity(self, instance):
        self.quantity += 1
        self.quantity_label.text = str(self.quantity)
        self.update_total()

    def update_total(self):
        total = self.quantity * self.ticket_price
        self.total_price_label.text = f"Total: R$ {total:.2f}".replace(".", ",")

    def process_purchase(self, instance):
        app = App.get_running_app()
        user_id = app.user_id
        
        if not user_id:
            self.status_label.text = "Você precisa estar logado para comprar ingressos."
            return
            
        # Get selected date in YYYY-MM-DD format
        selected_date = datetime.strptime(self.date_spinner.text, "%d/%m/%Y").strftime("%Y-%m-%d")
        payment_method = self.payment_spinner.text
        total_price = self.quantity * self.ticket_price
        
        # Generate a unique transaction code
        import uuid
        transaction_code = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Create purchase record
            cursor.execute(
                "INSERT INTO compras_ingressos (id_usuario_sistema, data_compra, valor_total_compra, metodo_pagamento, status_pagamento, codigo_transacao) "
                "VALUES (?, CURRENT_TIMESTAMP, ?, ?, 'Aprovado', ?)",
                (user_id, total_price, payment_method, transaction_code)
            )
            purchase_id = cursor.lastrowid
            
            # Create ticket items
            for i in range(self.quantity):
                ticket_code = f"{transaction_code}-{i+1}"
                cursor.execute(
                    "INSERT INTO itens_compra_ingressos (id_compra_ingresso, id_tipo_ingresso, quantidade, preco_unitario_cobrado, data_utilizacao_prevista, codigo_ingresso_unico) "
                    "VALUES (?, ?, 1, ?, ?, ?)",
                    (purchase_id, self.ticket_id, self.ticket_price, selected_date, ticket_code)
                )
            
            conn.commit()
            self.status_label.text = "Compra realizada com sucesso!"
            
            # Show success popup
            self.show_success_popup(purchase_id)
            
        except Exception as e:
            conn.rollback()
            self.status_label.text = f"Erro ao processar compra: {e}"
        finally:
            conn.close()

    def show_success_popup(self, purchase_id):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        content.add_widget(Label(
            text="Compra Realizada com Sucesso!",
            font_size="18sp",
            bold=True,
            color=COLOR_ACCENT
        ))
        content.add_widget(Label(
            text=f"Número da compra: #{purchase_id}",
            font_size="16sp"
        ))
        content.add_widget(Label(
            text="Seus ingressos estão disponíveis na seção 'Meus Ingressos'.",
            font_size="14sp"
        ))
        
        view_button = StyledButton(text="Ver Meus Ingressos")
        view_button.bind(on_press=lambda x: self.go_to_my_tickets())
        
        close_button = Button(
            text="Fechar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        buttons_layout.add_widget(view_button)
        buttons_layout.add_widget(close_button)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Compra Confirmada",
            content=content,
            size_hint=(0.9, 0.5),
            auto_dismiss=False
        )
        
        close_button.bind(on_press=popup.dismiss)
        popup.open()

    def go_to_my_tickets(self):
        screen = self.manager.get_screen("tickets_list")
        screen.current_tab = "my_tickets"
        self.manager.current = "tickets_list"

class ParkMapScreen(Screen):
    def __init__(self, **kwargs):
        super(ParkMapScreen, self).__init__(**kwargs)
        self.name = "park_map"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Mapa do Parque"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Conteúdo do mapa
        scroll_view = ScrollView(size_hint=(1, 1), bar_width=10, bar_color=COLOR_PRIMARY)
        content_layout = BoxLayout(orientation="vertical", spacing=15, padding=10, size_hint_y=None)
        content_layout.bind(minimum_height=content_layout.setter("height"))
        
        # Imagem do mapa (placeholder)
        map_path = os.path.join(ASSETS_PATH, "park_map.png")
        if os.path.exists(map_path):
            content_layout.add_widget(KivyImage(
                source=map_path,
                size_hint_y=None,
                height=400
            ))
        else:
            # Placeholder para o mapa
            placeholder = BoxLayout(orientation="vertical", size_hint_y=None, height=400)
            placeholder.canvas.before.add(Color(0.9, 0.9, 0.9, 1))
            placeholder.canvas.before.add(Rectangle(pos=placeholder.pos, size=placeholder.size))
            
            placeholder.add_widget(Label(
                text="Mapa do Parque\n(Imagem não disponível)",
                font_size="20sp",
                color=COLOR_TEXT_DARK
            ))
            
            content_layout.add_widget(placeholder)
        
        # Legenda do mapa
        content_layout.add_widget(Label(
            text="Legenda do Mapa",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        ))
        
        # Itens da legenda
        legend_items = [
            ("Atrações Radicais", "Vermelho"),
            ("Atrações Familiares", "Azul"),
            ("Atrações Infantis", "Verde"),
            ("Lanchonetes", "Amarelo"),
            ("Banheiros", "Cinza"),
            ("Lojas", "Roxo"),
            ("Entrada/Saída", "Laranja")
        ]
        
        for item, color in legend_items:
            item_layout = BoxLayout(size_hint_y=None, height=30, spacing=10)
            
            color_box = BoxLayout(size_hint_x=0.1)
            if color == "Vermelho":
                color_box.canvas.before.add(Color(0.9, 0.2, 0.2, 1))
            elif color == "Azul":
                color_box.canvas.before.add(Color(0.2, 0.4, 0.8, 1))
            elif color == "Verde":
                color_box.canvas.before.add(Color(0.2, 0.8, 0.2, 1))
            elif color == "Amarelo":
                color_box.canvas.before.add(Color(0.9, 0.9, 0.2, 1))
            elif color == "Cinza":
                color_box.canvas.before.add(Color(0.5, 0.5, 0.5, 1))
            elif color == "Roxo":
                color_box.canvas.before.add(Color(0.6, 0.2, 0.8, 1))
            elif color == "Laranja":
                color_box.canvas.before.add(Color(0.9, 0.5, 0.1, 1))
            
            color_box.canvas.before.add(Rectangle(pos=color_box.pos, size=color_box.size))
            item_layout.add_widget(color_box)
            
            item_layout.add_widget(Label(
                text=item,
                font_size="16sp",
                color=COLOR_TEXT_DARK,
                size_hint_x=0.9,
                halign="left",
                text_size=(Window.width * 0.7, None)
            ))
            
            content_layout.add_widget(item_layout)
            content_layout.height += 30
        
        # Informações adicionais
        content_layout.add_widget(Label(
            text="Informações Úteis",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        info_text = """
• O parque está dividido em 5 áreas temáticas.
• Banheiros estão disponíveis em todas as áreas.
• Pontos de hidratação gratuitos estão marcados com símbolos de gota d'água.
• Armários para pertences estão disponíveis próximos à entrada principal.
• Em caso de emergência, procure um funcionário ou dirija-se a um ponto de informação.
        """
        
        info_label = Label(
            text=info_text,
            font_size="15sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            halign="left",
            text_size=(Window.width * 0.9, None)
        )
        info_label.bind(texture_size=info_label.setter('size'))
        content_layout.add_widget(info_label)
        
        scroll_view.add_widget(content_layout)
        layout.add_widget(scroll_view)
        
        self.add_widget(layout)

class RatingPopup(Popup):
    def __init__(self, id_referencia, tipo_referencia, **kwargs):
        self.id_referencia = id_referencia
        self.tipo_referencia = tipo_referencia
        
        title_map = {
            "atracao": "Avaliar Atração",
            "show": "Avaliar Show",
            "lanchonete": "Avaliar Lanchonete"
        }
        
        title = title_map.get(tipo_referencia, "Avaliar")
        super(RatingPopup, self).__init__(title=title, size_hint=(0.9, 0.7), **kwargs)
        
        layout = BoxLayout(orientation="vertical", padding=15, spacing=10)
        
        # Rating stars
        layout.add_widget(Label(
            text="Sua Avaliação:",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height=40
        ))
        
        stars_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.star_buttons = []
        
        for i in range(1, 6):
            star = Button(
                text="★",
                font_size="24sp",
                background_color=(0, 0, 0, 0),
                color=COLOR_DISABLED
            )
            star.rating_value = i
            star.bind(on_press=self.set_rating)
            stars_layout.add_widget(star)
            self.star_buttons.append(star)
        
        layout.add_widget(stars_layout)
        
        # Comment
        layout.add_widget(Label(
            text="Comentário (opcional):",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.8, None)
        ))
        
        self.comment_input = TextInput(
            hint_text="Escreva seu comentário aqui...",
            multiline=True,
            size_hint_y=None,
            height=100
        )
        layout.add_widget(self.comment_input)
        
        # Status message
        self.status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        layout.add_widget(self.status_label)
        
        # Buttons
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        submit_button = StyledButton(text="Enviar Avaliação")
        submit_button.bind(on_press=self.submit_rating)
        
        cancel_button = Button(
            text="Cancelar",
            background_color=COLOR_SECONDARY,
            color=COLOR_TEXT_DARK
        )
        cancel_button.bind(on_press=self.dismiss)
        
        buttons_layout.add_widget(submit_button)
        buttons_layout.add_widget(cancel_button)
        layout.add_widget(buttons_layout)
        
        self.content = layout
        self.rating = 0

    def set_rating(self, instance):
        self.rating = instance.rating_value
        
        for i, star in enumerate(self.star_buttons):
            if i < self.rating:
                star.color = COLOR_SECONDARY  # Filled star
            else:
                star.color = COLOR_DISABLED  # Empty star

    def submit_rating(self, instance):
        if self.rating == 0:
            self.status_label.text = "Por favor, selecione uma avaliação de 1 a 5 estrelas."
            return
        
        user_id = App.get_running_app().user_id
        if not user_id:
            self.status_label.text = "Você precisa estar logado para avaliar."
            return
        
        comment = self.comment_input.text
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user already rated this item
            cursor.execute(
                "SELECT id FROM avaliacoes WHERE id_usuario_sistema = ? AND id_referencia = ? AND tipo_referencia = ?",
                (user_id, self.id_referencia, self.tipo_referencia)
            )
            existing_rating = cursor.fetchone()
            
            if existing_rating:
                # Update existing rating
                cursor.execute(
                    "UPDATE avaliacoes SET nota = ?, comentario = ?, data_avaliacao = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (self.rating, comment, existing_rating["id"])
                )
                self.status_label.text = "Sua avaliação foi atualizada!"
            else:
                # Create new rating
                cursor.execute(
                    "INSERT INTO avaliacoes (id_usuario_sistema, id_referencia, tipo_referencia, nota, comentario) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, self.id_referencia, self.tipo_referencia, self.rating, comment)
                )
                self.status_label.text = "Avaliação enviada com sucesso!"
            
            conn.commit()
            
            # Close popup after a short delay
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.dismiss(), 1.5)
            
        except Exception as e:
            self.status_label.text = f"Erro ao enviar avaliação: {e}"
        finally:
            conn.close()
class CreateItineraryScreen(Screen):
    def __init__(self, **kwargs):
        super(CreateItineraryScreen, self).__init__(**kwargs)
        self.name = "create_itinerary"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        header_layout.add_widget(HeaderLabel(text="Criar Itinerário"))
        back_button = StyledButton(text="Voltar", size_hint_x=0.25, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, "current", App.get_running_app().get_previous_screen()))
        header_layout.add_widget(back_button)
        layout.add_widget(header_layout)

        # Formulário de criação de itinerário
        form_layout = BoxLayout(orientation="vertical", spacing=15, padding=10)
        
        # Nome do itinerário
        form_layout.add_widget(Label(
            text="Nome do Itinerário:",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.name_input = TextInput(
            hint_text="Ex: Meu dia no parque",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.name_input)
        
        # Data da visita
        form_layout.add_widget(Label(
            text="Data da Visita:",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        # Create a date spinner with next 30 days
        import datetime as dt
        self.date_spinner = Spinner(
            text=date.today().strftime("%d/%m/%Y"),
            values=[
                (date.today() + dt.timedelta(days=i)).strftime("%d/%m/%Y")
                for i in range(30)
            ],
            size_hint_y=None,
            height=40
        )
        form_layout.add_widget(self.date_spinner)
        
        # Lista de atrações disponíveis
        form_layout.add_widget(Label(
            text="Selecione as Atrações:",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        # Carregar atrações do banco de dados
        self.attractions_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.attractions_layout.bind(minimum_height=self.attractions_layout.setter("height"))
        
        attractions_scroll = ScrollView(size_hint_y=None, height=200)
        attractions_scroll.add_widget(self.attractions_layout)
        form_layout.add_widget(attractions_scroll)
        
        # Botão para adicionar atração selecionada ao itinerário
        add_attraction_button = StyledButton(
            text="Adicionar Atração Selecionada",
            size_hint_y=None,
            height=40
        )
        add_attraction_button.bind(on_press=self.add_selected_attraction)
        form_layout.add_widget(add_attraction_button)
        
        # Lista de itens do itinerário
        form_layout.add_widget(Label(
            text="Seu Itinerário:",
            font_size="16sp",
            color=COLOR_TEXT_DARK,
            size_hint_y=None,
            height=30,
            halign="left",
            text_size=(Window.width * 0.9, None)
        ))
        
        self.itinerary_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.itinerary_layout.bind(minimum_height=self.itinerary_layout.setter("height"))
        
        itinerary_scroll = ScrollView(size_hint_y=None, height=200)
        itinerary_scroll.add_widget(self.itinerary_layout)
        form_layout.add_widget(itinerary_scroll)
        
        # Botão para salvar itinerário
        save_button = StyledButton(
            text="Salvar Itinerário",
            size_hint_y=None,
            height=50
        )
        save_button.bind(on_press=self.save_itinerary)
        form_layout.add_widget(save_button)
        
        # Status message
        self.status_label = Label(
            text="",
            color=COLOR_ACCENT,
            size_hint_y=None,
            height=30
        )
        form_layout.add_widget(self.status_label)
        
        layout.add_widget(form_layout)
        self.add_widget(layout)
        
        # Lista para armazenar os itens do itinerário
        self.itinerary_items = []
        self.selected_attraction = None

    def on_enter(self, *args):
        self.load_attractions()
        self.update_itinerary_list()

    def load_attractions(self):
        self.attractions_layout.clear_widgets()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, tipo_atracao FROM atracoes WHERE status = 'Operacional' ORDER BY nome")
        attractions = cursor.fetchall()
        conn.close()
        
        if not attractions:
            self.attractions_layout.add_widget(Label(
                text="Nenhuma atração disponível no momento.",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=40
            ))
            return
        
        for attraction in attractions:
            item = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=10)
            
            select_button = Button(
                text="Selecionar",
                size_hint_x=0.3,
                background_color=COLOR_PRIMARY
            )
            select_button.bind(on_press=lambda _, id=attraction["id"], name=attraction["nome"]: self.select_attraction(id, name))
            
            item.add_widget(select_button)
            
            item.add_widget(Label(
                text=f"{attraction['nome']} ({attraction['tipo_atracao']})",
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                size_hint_x=0.7,
                halign="left",
                text_size=(Window.width * 0.6, None)
            ))
            
            self.attractions_layout.add_widget(item)
    
    def select_attraction(self, attraction_id, attraction_name):
        self.selected_attraction = {
            "id": attraction_id,
            "name": attraction_name
        }
        self.status_label.text = f"Atração selecionada: {attraction_name}"
    
    def add_selected_attraction(self, instance):
        if not self.selected_attraction:
            self.status_label.text = "Selecione uma atração primeiro."
            return
        
        # Adicionar horário padrão (pode ser personalizado depois)
        current_time = datetime.now().strftime("%H:%M")
        
        self.itinerary_items.append({
            "id": self.selected_attraction["id"],
            "name": self.selected_attraction["name"],
            "time": current_time,
            "type": "atracao"
        })
        
        self.update_itinerary_list()
        self.status_label.text = f"Atração {self.selected_attraction['name']} adicionada ao itinerário."
        self.selected_attraction = None
    
    def update_itinerary_list(self):
        self.itinerary_layout.clear_widgets()
        
        if not self.itinerary_items:
            self.itinerary_layout.add_widget(Label(
                text="Seu itinerário está vazio. Adicione atrações.",
                color=COLOR_TEXT_DARK,
                size_hint_y=None,
                height=40
            ))
            return
        
        for i, item in enumerate(self.itinerary_items):
            item_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=10)
            
            # Botão para remover item
            remove_button = Button(
                text="X",
                size_hint_x=0.1,
                background_color=(0.9, 0.2, 0.2, 1)
            )
            remove_button.bind(on_press=lambda _, idx=i: self.remove_item(idx))
            
            item_layout.add_widget(remove_button)
            
            # Horário
            time_input = TextInput(
                text=item["time"],
                multiline=False,
                size_hint_x=0.2
            )
            time_input.bind(text=lambda instance, value, idx=i: self.update_item_time(idx, value))
            item_layout.add_widget(time_input)
            
            # Nome da atração
            item_layout.add_widget(Label(
                text=item["name"],
                font_size="14sp",
                color=COLOR_TEXT_DARK,
                size_hint_x=0.7,
                halign="left",
                text_size=(Window.width * 0.5, None)
            ))
            
            self.itinerary_layout.add_widget(item_layout)
    
    def update_item_time(self, index, value):
        if 0 <= index < len(self.itinerary_items):
            self.itinerary_items[index]["time"] = value
    
    def remove_item(self, index):
        if 0 <= index < len(self.itinerary_items):
            del self.itinerary_items[index]
            self.update_itinerary_list()
    
    def save_itinerary(self, instance):
        user_id = App.get_running_app().user_id
        
        if not user_id:
            self.status_label.text = "Você precisa estar logado para salvar um itinerário."
            return
        
        if not self.name_input.text:
            self.status_label.text = "Digite um nome para o itinerário."
            return
        
        if not self.itinerary_items:
            self.status_label.text = "Adicione pelo menos uma atração ao itinerário."
            return
        
        # Converter data para formato YYYY-MM-DD
        visit_date = datetime.strptime(self.date_spinner.text, "%d/%m/%Y").strftime("%Y-%m-%d")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Criar registro do itinerário
            cursor.execute(
                "INSERT INTO itinerarios (id_usuario_sistema, nome, data_visita) VALUES (?, ?, ?)",
                (user_id, self.name_input.text, visit_date)
            )
            itinerary_id = cursor.lastrowid
            
            # Adicionar itens ao itinerário
            for i, item in enumerate(self.itinerary_items):
                cursor.execute(
                    "INSERT INTO itens_itinerario (id_itinerario, tipo_item, id_referencia, horario_previsto, ordem) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (itinerary_id, item["type"], item["id"], item["time"], i+1)
                )
            
            conn.commit()
            self.status_label.text = "Itinerário salvo com sucesso!"
            
            # Limpar formulário
            self.name_input.text = ""
            self.itinerary_items = []
            self.update_itinerary_list()
            
        except Exception as e:
            conn.rollback()
            self.status_label.text = f"Erro ao salvar itinerário: {e}"
        finally:
            conn.close()

# --- Main App ---
class InfinityParkApp(App):
    def __init__(self, **kwargs):
        super(InfinityParkApp, self).__init__(**kwargs)
        self.title = APP_NAME
        self.user_id = None
        self.user_profile = None
        self.previous_screen = "login"
        self.selected_attraction_id = None
        self.selected_show_id = None
        self.selected_lanchonete_id = None
        self.selected_ticket_type_id = None
        self.selected_ticket_type_name = None
        self.selected_ticket_type_price = 0
        self.selected_purchase_id = None

    def build(self):
        init_db()
        self.sm = ScreenManager(transition=FadeTransition())
        
        screens = [
            LoginScreen(),
            RegisterScreen(),
            UserHomeScreen(),
            AdminHomeScreen(),
            AttractionsListScreen(),
            AttractionDetailScreen(),
            AdminManageAttractionsScreen(),
            ShowsListScreen(),
            ShowDetailScreen(),
            AdminManageShowsScreen(),
            FoodCourtsListScreen(),
            FoodCourtDetailScreen(),
            TicketsListScreen(),
            TicketPurchaseScreen(),
            MyProfileScreen(),
            PurchaseDetailsScreen(),
            # Adicionar as novas telas
            ParkMapScreen(),
            AboutParkScreen(),
            WarningsListScreen(),
            CreateItineraryScreen(),
            MyItineraryScreen()
        ]
        
        for screen in screens:
            self.sm.add_widget(screen)
            
        return self.sm

    def get_previous_screen(self):
        if self.sm.current in ["attraction_detail", "show_detail", "food_court_detail"]:
            return {
                "attraction_detail": "attractions_list",
                "show_detail": "shows_list",
                "food_court_detail": "food_courts_list"
            }.get(self.sm.current, "user_home")
        
        admin_screens = ["admin_manage_users", "admin_manage_attractions", 
                        "admin_manage_shows", "admin_manage_food_courts",
                        "admin_manage_warnings", "admin_system_logs"]
        
        return "admin_home" if self.sm.current in admin_screens else "user_home"

if __name__ == "__main__":
    InfinityParkApp().run()