-- Criação do Banco de Dados
CREATE DATABASE IF NOT EXISTS infinity_Park_215 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE infinity_Park_215;

-- Tabela de Tipos de Ingressos
CREATE TABLE IF NOT EXISTS tipos_ingressos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE COMMENT 'Ex: Adulto, Criança, Idoso, VIP',
    descricao TEXT,
    preco_base DECIMAL(10,2) NOT NULL,
    idade_minima INT DEFAULT 0,
    idade_maxima INT DEFAULT 120,
    ativo BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tipos de ingressos disponíveis e seus preços base.';

-- Tabela de Visitantes
CREATE TABLE IF NOT EXISTS visitantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpf VARCHAR(11) UNIQUE NOT NULL COMMENT 'CPF do visitante, sem formatação',
    nome_completo VARCHAR(150) NOT NULL,
    data_nascimento DATE NOT NULL,
    altura_cm INT COMMENT 'Altura em centímetros',
    email VARCHAR(100) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    restricoes_medicas TEXT COMMENT 'Descrição de restrições médicas relevantes',
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Informações dos visitantes do parque.';

-- Tabela de Atrações
CREATE TABLE IF NOT EXISTS atracoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao_curta VARCHAR(255) COMMENT 'Um resumo da atração',
    descricao_detalhada TEXT COMMENT 'Descrição completa da atração',
    capacidade_por_ciclo INT NOT NULL COMMENT 'Número de pessoas por vez/ciclo',
    duracao_ciclo_minutos INT COMMENT 'Duração aproximada de um ciclo da atração em minutos',
    altura_minima_cm INT COMMENT 'Altura mínima em centímetros para participar',
    altura_maxima_cm INT COMMENT 'Altura máxima em centímetros para participar (se aplicável)',
    idade_minima_anos INT COMMENT 'Idade mínima em anos para participar',
    acompanhante_obrigatorio_ate_idade INT COMMENT 'Idade até a qual um acompanhante é obrigatório',
    tipo_atracao VARCHAR(50) COMMENT 'Ex: Radical, Familiar, Infantil, Aquática, Show',
    localizacao_mapa VARCHAR(100) COMMENT 'Referência de localização no mapa do parque (ex: Setor A, Perto da Praça de Alimentação)',
    url_foto_principal VARCHAR(255) COMMENT 'URL de uma foto de destaque da atração',
    status ENUM('Operacional', 'Manutenção Programada', 'Manutenção Corretiva', 'Fechada Temporariamente', 'Em Breve') DEFAULT 'Operacional',
    data_ultima_manutencao DATE,
    proxima_manutencao_programada DATE,
    nivel_emocao ENUM('Baixo', 'Médio', 'Alto', 'Muito Alto') COMMENT 'Nível de emoção da atração',
    acessibilidade TEXT COMMENT 'Informações sobre acessibilidade para PCDs'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Detalhes das atrações do parque.';

-- Tabela de Funcionários
CREATE TABLE IF NOT EXISTS funcionarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpf VARCHAR(11) UNIQUE NOT NULL,
    nome_completo VARCHAR(150) NOT NULL,
    data_nascimento DATE,
    cargo VARCHAR(50) NOT NULL,
    departamento VARCHAR(50),
    turno ENUM('Manhã', 'Tarde', 'Noite', 'Integral') COMMENT 'Turno de trabalho do funcionário',
    data_admissao DATE NOT NULL,
    data_desligamento DATE,
    salario DECIMAL(10,2),
    email_corporativo VARCHAR(100) UNIQUE,
    telefone_contato VARCHAR(20),
    status ENUM('Ativo', 'Inativo', 'Férias', 'Licença') DEFAULT 'Ativo'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Informações dos funcionários do parque.';

-- Tabela de Usuários do Sistema (para login no app Kivy)
CREATE TABLE IF NOT EXISTS usuarios_sistema (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_visitante INT NULL UNIQUE COMMENT 'Link para visitante, se o usuário for um cliente',
    id_funcionario INT NULL UNIQUE COMMENT 'Link para funcionário, se o usuário for um admin/operador',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT 'Nome de usuário para login',
    senha_hash VARCHAR(255) NOT NULL COMMENT 'Hash da senha',
    tipo_perfil ENUM('Comum', 'Administrador', 'Operador') NOT NULL DEFAULT 'Comum',
    email_recuperacao VARCHAR(100) NOT NULL UNIQUE,
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_login TIMESTAMP NULL,
    FOREIGN KEY (id_visitante) REFERENCES visitantes(id) ON DELETE SET NULL,
    FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Usuários para acesso ao sistema (app Kivy).';

-- Tabela de Compras de Ingressos
CREATE TABLE IF NOT EXISTS compras_ingressos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario_sistema INT NOT NULL COMMENT 'Usuário que realizou a compra (logado no sistema)',
    id_visitante_responsavel INT NOT NULL COMMENT 'Visitante principal da compra (pode ser o mesmo do usuário ou outro)',
    data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valor_total_compra DECIMAL(10,2) NOT NULL,
    metodo_pagamento VARCHAR(50) COMMENT 'Ex: Cartão de Crédito, PIX, Boleto',
    status_pagamento ENUM('Pendente', 'Aprovado', 'Recusado', 'Estornado') DEFAULT 'Pendente',
    codigo_transacao VARCHAR(100) UNIQUE COMMENT 'Código da transação do gateway de pagamento',
    FOREIGN KEY (id_usuario_sistema) REFERENCES usuarios_sistema(id),
    FOREIGN KEY (id_visitante_responsavel) REFERENCES visitantes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Registra cada transação de compra de ingressos.';

-- Tabela de Itens da Compra de Ingressos (Ingressos Individuais)
CREATE TABLE IF NOT EXISTS itens_compra_ingressos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_compra_ingresso INT NOT NULL,
    id_tipo_ingresso INT NOT NULL,
    quantidade INT NOT NULL DEFAULT 1,
    preco_unitario_cobrado DECIMAL(10,2) NOT NULL COMMENT 'Preço no momento da compra, pode incluir promoções',
    data_utilizacao_prevista DATE NOT NULL COMMENT 'Data para a qual o ingresso é válido',
    codigo_ingresso_unico VARCHAR(50) UNIQUE NOT NULL COMMENT 'Código único para cada ingresso individual gerado',
    status_ingresso ENUM('Não Utilizado', 'Utilizado', 'Cancelado', 'Expirado') DEFAULT 'Não Utilizado',
    id_visitante_portador INT NULL COMMENT 'Visitante que utilizará este ingresso específico (opcional, pode ser preenchido depois)',
    FOREIGN KEY (id_compra_ingresso) REFERENCES compras_ingressos(id) ON DELETE CASCADE,
    FOREIGN KEY (id_tipo_ingresso) REFERENCES tipos_ingressos(id),
    FOREIGN KEY (id_visitante_portador) REFERENCES visitantes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Detalha cada ingresso individual dentro de uma compra.';

-- Tabela de Horários de Funcionamento do Parque
CREATE TABLE IF NOT EXISTS horarios_funcionamento_parque (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data_especifica DATE UNIQUE COMMENT 'Para horários em datas específicas (feriados, eventos)',
    dia_semana ENUM('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo') COMMENT 'Para horários recorrentes',
    horario_abertura TIME,
    horario_fechamento TIME,
    observacao TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Horários de funcionamento do parque.';

-- Tabela de Manutenções de Atrações
CREATE TABLE IF NOT EXISTS manutencoes_atracoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_atracao INT NOT NULL,
    data_inicio_manutencao DATETIME NOT NULL,
    data_fim_prevista_manutencao DATETIME,
    data_fim_real_manutencao DATETIME,
    tipo_manutencao ENUM('Preventiva', 'Corretiva', 'Melhoria') NOT NULL,
    descricao_servico TEXT NOT NULL,
    id_funcionario_responsavel INT,
    custo_estimado DECIMAL(10,2),
    custo_real DECIMAL(10,2),
    status_manutencao ENUM('Agendada', 'Em Andamento', 'Concluída', 'Cancelada') DEFAULT 'Agendada',
    FOREIGN KEY (id_atracao) REFERENCES atracoes(id) ON DELETE CASCADE,
    FOREIGN KEY (id_funcionario_responsavel) REFERENCES funcionarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Registro de manutenções realizadas nas atrações.';


-- INSERINDO DADOS DE EXEMPLO --

-- Tipos de Ingressos
INSERT INTO tipos_ingressos (nome, descricao, preco_base, idade_minima, idade_maxima) VALUES
('Adulto', 'Ingresso para maiores de 12 anos.', 150.00, 13, 59),
('Criança', 'Ingresso para crianças de 3 a 12 anos.', 75.00, 3, 12),
('Idoso', 'Ingresso para maiores de 60 anos.', 70.00, 60, 120),
('PCD', 'Ingresso para Pessoa com Deficiência (acompanhante paga meia se necessário, verificar regras).', 0.00, 0, 120),
('VIP Pass', 'Acesso rápido a atrações selecionadas e áreas exclusivas.', 300.00, 0, 120);

-- Visitantes
INSERT INTO visitantes (cpf, nome_completo, data_nascimento, altura_cm, email, telefone, restricoes_medicas) VALUES
('11122233344', 'Carlos Alberto Nobrega', '1985-03-15', 175, 'carlos.nobrega@email.com', '(11) 91111-1111', 'Alergia a amendoim'),
('55566677788', 'Fernanda Montenegro', '1990-07-22', 165, 'fernanda.montenegro@email.com', '(21) 92222-2222', NULL),
('99988877766', 'Pedro Alvares Cabral', '2015-01-10', 120, 'pedrinho.cabral@email.com', '(71) 93333-3333', 'Asma leve');

-- Atrações
INSERT INTO atracoes (nome, descricao_curta, descricao_detalhada, capacidade_por_ciclo, duracao_ciclo_minutos, altura_minima_cm, tipo_atracao, localizacao_mapa, url_foto_principal, status, nivel_emocao, acessibilidade) VALUES
('Dragão Flamejante', 'Montanha russa invertida com 5 loopings!', 'Sinta a adrenalina pura na Dragão Flamejante, uma montanha russa que desafia a gravidade com seus loopings e quedas vertiginosas. Prepare-se para gritar!', 32, 3, 140, 'Radical', 'Área Vulcânica, Lado Leste', 'https://via.placeholder.com/800x600.png/FF5733/FFFFFF?Text=DragaoFlamejante', 'Operacional', 'Muito Alto', 'Não acessível para cadeirantes nesta atração.'),
('Carrossel Encantado', 'Um clássico para toda a família.', 'Gire suavemente ao som de músicas mágicas no Carrossel Encantado. Cavalos coloridos e criaturas fantásticas esperam por você.', 40, 5, NULL, 'Familiar', 'Vila da Fantasia, Centro', 'https://via.placeholder.com/800x600.png/33FF57/FFFFFF?Text=CarrosselEncantado', 'Operacional', 'Baixo', 'Acessível para cadeirantes com auxílio.'),
('Torre do Terror', 'Despenque de uma altura de 60 metros!', 'Encare seus medos na Torre do Terror. Uma subida lenta e uma queda livre de tirar o fôlego. Você tem coragem?', 16, 2, 130, 'Radical', 'Zona do Medo, Norte', 'https://via.placeholder.com/800x600.png/3333FF/FFFFFF?Text=TorreDoTerror', 'Manutenção Programada', 'Alto', 'Consultar operadores para acessibilidade.'),
('Rio Bravo Kids', 'Aventura aquática para os pequenos.', 'Navegue por corredeiras suaves e divirta-se com esguichos d''água no Rio Bravo Kids. Perfeito para refrescar e para os pequenos aventureiros.', 20, 10, 90, 'Infantil', 'Aqua Parque, Oeste', 'https://via.placeholder.com/800x600.png/33CFFF/FFFFFF?Text=RioBravoKids', 'Operacional', 'Médio', 'Acessível.');

-- Funcionários
INSERT INTO funcionarios (cpf, nome_completo, data_nascimento, cargo, departamento, turno, data_admissao, email_corporativo, telefone_contato, status) VALUES
('12312312311', 'Mariana Silva', '1992-05-20', 'Gerente de Operações', 'Operações', 'Integral', '2018-03-01', 'mariana.silva@infinitypark.com', '(11) 98888-7777', 'Ativo'),
('45645645622', 'Roberto Lima', '1988-11-10', 'Operador de Atração', 'Operações', 'Tarde', '2022-07-15', 'roberto.lima@infinitypark.com', '(11) 97777-6666', 'Ativo'),
('78978978933', 'Juliana Costa', '2000-02-28', 'Atendente de Bilheteria', 'Comercial', 'Manhã', '2023-01-20', 'juliana.costa@infinitypark.com', '(11) 96666-5555', 'Ativo');

-- Usuários do Sistema
-- Senha para todos os usuários de exemplo: 'senha123' (o hash abaixo é para 'senha123' usando um gerador online de bcrypt, idealmente seria gerado pela aplicação)
-- Para o Kivy, provavelmente usaremos SQLite e o hash será diferente ou gerenciado pela lógica Python.
-- Este é um placeholder para o conceito.
INSERT INTO usuarios_sistema (id_visitante, username, senha_hash, tipo_perfil, email_recuperacao) VALUES
((SELECT id FROM visitantes WHERE cpf = '11122233344'), 'carlos.nobrega', '$2a$12$5N0Yg0gQ0Z4qj3Y.X.Y.Z.e1W9X.Z.Y.X.Y.Z.e1W9X.Z.Y.X', 'Comum', 'carlos.nobrega@email.com'),
((SELECT id FROM visitantes WHERE cpf = '55566677788'), 'fernanda.m', '$2a$12$5N0Yg0gQ0Z4qj3Y.X.Y.Z.e1W9X.Z.Y.X.Y.Z.e1W9X.Z.Y.X', 'Comum', 'fernanda.montenegro@email.com');

INSERT INTO usuarios_sistema (id_funcionario, username, senha_hash, tipo_perfil, email_recuperacao) VALUES
((SELECT id FROM funcionarios WHERE cpf = '12312312311'), 'admin_mariana', '$2a$12$5N0Yg0gQ0Z4qj3Y.X.Y.Z.e1W9X.Z.Y.X.Y.Z.e1W9X.Z.Y.X', 'Administrador', 'mariana.silva@infinitypark.com'),
((SELECT id FROM funcionarios WHERE cpf = '45645645622'), 'op_roberto', '$2a$12$5N0Yg0gQ0Z4qj3Y.X.Y.Z.e1W9X.Z.Y.X.Y.Z.e1W9X.Z.Y.X', 'Operador', 'roberto.lima@infinitypark.com');

-- Compras de Ingressos (Exemplo)
INSERT INTO compras_ingressos (id_usuario_sistema, id_visitante_responsavel, valor_total_compra, metodo_pagamento, status_pagamento, codigo_transacao) VALUES
((SELECT id FROM usuarios_sistema WHERE username = 'carlos.nobrega'), (SELECT id FROM visitantes WHERE cpf = '11122233344'), 225.00, 'Cartão de Crédito', 'Aprovado', 'TRN12345ABC'),
((SELECT id FROM usuarios_sistema WHERE username = 'fernanda.m'), (SELECT id FROM visitantes WHERE cpf = '55566677788'), 75.00, 'PIX', 'Aprovado', 'TRN67890DEF');

-- Itens da Compra de Ingressos (Exemplo)
INSERT INTO itens_compra_ingressos (id_compra_ingresso, id_tipo_ingresso, quantidade, preco_unitario_cobrado, data_utilizacao_prevista, codigo_ingresso_unico, id_visitante_portador) VALUES
((SELECT id FROM compras_ingressos WHERE codigo_transacao = 'TRN12345ABC'), (SELECT id FROM tipos_ingressos WHERE nome = 'Adulto'), 1, 150.00, CURDATE() + INTERVAL 7 DAY, CONCAT('INFADU', UUID_SHORT()), (SELECT id FROM visitantes WHERE cpf = '11122233344')),
((SELECT id FROM compras_ingressos WHERE codigo_transacao = 'TRN12345ABC'), (SELECT id FROM tipos_ingressos WHERE nome = 'Criança'), 1, 75.00, CURDATE() + INTERVAL 7 DAY, CONCAT('INFCRI', UUID_SHORT()), (SELECT id FROM visitantes WHERE cpf = '99988877766')),
((SELECT id FROM compras_ingressos WHERE codigo_transacao = 'TRN67890DEF'), (SELECT id FROM tipos_ingressos WHERE nome = 'Criança'), 1, 75.00, CURDATE() + INTERVAL 10 DAY, CONCAT('INFCRI', UUID_SHORT()), NULL);

-- Horários de Funcionamento
INSERT INTO horarios_funcionamento_parque (dia_semana, horario_abertura, horario_fechamento, observacao) VALUES
('Segunda', '10:00:00', '18:00:00', 'Baixa temporada'),
('Terça', '10:00:00', '18:00:00', 'Baixa temporada'),
('Quarta', '10:00:00', '19:00:00', NULL),
('Quinta', '10:00:00', '19:00:00', NULL),
('Sexta', '10:00:00', '20:00:00', 'Shows noturnos'),
('Sábado', '09:00:00', '21:00:00', 'Shows noturnos e queima de fogos'),
('Domingo', '09:00:00', '20:00:00', NULL);

INSERT INTO horarios_funcionamento_parque (data_especifica, horario_abertura, horario_fechamento, observacao) VALUES
('2025-12-25', '14:00:00', '22:00:00', 'Especial de Natal'),
('2026-01-01', '12:00:00', '22:00:00', 'Ano Novo');

-- Manutenções de Atrações (Exemplo)
INSERT INTO manutencoes_atracoes (id_atracao, data_inicio_manutencao, data_fim_prevista_manutencao, tipo_manutencao, descricao_servico, id_funcionario_responsavel, status_manutencao) VALUES
((SELECT id FROM atracoes WHERE nome = 'Torre do Terror'), NOW(), NOW() + INTERVAL 3 DAY, 'Preventiva', 'Revisão geral do sistema de freios e cabos.', (SELECT id FROM funcionarios WHERE email_corporativo = 'roberto.lima@infinitypark.com'), 'Agendada');

SELECT 'Banco de dados infinity_Park_215 e tabelas criadas com sucesso. Dados de exemplo inseridos.' AS status_geral;

