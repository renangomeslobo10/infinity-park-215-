# 🎢 Infinity Park 215 - Sistema de Gerenciamento de Parque de Diversões

Sistema completo para gerenciamento de parque de diversões desenvolvido em Python com interface desktop multiplataforma usando Kivy.

## 📋 Sobre o Projeto

O **Infinity Park 215** é um sistema robusto que simula todas as operações de um parque temático, desde o cadastro de visitantes até o controle de atrações e vendas de ingressos. Foi desenvolvido como um projeto pessoal para demonstrar conhecimentos em desenvolvimento desktop, banco de dados e arquitetura de software.

## ✨ Principais Funcionalidades

### 👥 Gestão de Usuários
- Sistema de login/cadastro com hash de senhas (SHA-256)
- Diferentes níveis de acesso (Comum, Administrador, Operador)
- Perfil de usuário com histórico de atividades
- Sistema de pontuação gamificado

### 🎠 Gestão de Atrações
- Cadastro completo de atrações com restrições de idade/altura
- Status operacional (Operacional, Manutenção, etc.)
- Sistema de avaliações com estrelas (1-5)
- Check-ins com pontuação para gamificação
- Agendamento de FastPass

### 🎭 Shows e Eventos
- Programação de shows com horários
- Gestão de localizações e capacidade
- Sistema de avaliações
- Controle de status (ativo/inativo)

### 🎫 Sistema de Ingressos
- Diferentes tipos de ingressos (Adulto, Criança, Idoso, PCD, VIP)
- Compra integrada com simulação de pagamento
- Códigos únicos para cada ingresso
- Histórico completo de compras
- Status de utilização

### 🍔 Lanchonetes
- Cadastro de estabelecimentos
- Cardápio com categorias e preços
- Horários de funcionamento
- Sistema de avaliações

### 📅 Itinerários Personalizados
- Criação de roteiros personalizados
- Agendamento por horário
- Gestão de múltiplos itinerários

### 🛠️ Painel Administrativo
- Gestão completa de atrações, shows e lanchonetes
- Controle de usuários do sistema
- Relatórios e estatísticas
- Gestão de avisos e comunicados

## 🚀 Tecnologias Utilizadas

- **Python 3.x** - Linguagem principal
- **Kivy** - Framework para interface gráfica multiplataforma
- **SQLite** - Banco de dados local para desenvolvimento
- **MySQL** - Banco de dados para produção
- **Hashlib** - Criptografia de senhas
- **UUID** - Geração de códigos únicos
- **Datetime** - Manipulação de datas e horários

## 🏗️ Arquitetura

O projeto segue o padrão **MVC (Model-View-Controller)**:

- **Models**: Estruturas de dados e lógica de banco
- **Views**: Telas e componentes visuais (Kivy Screens)
- **Controllers**: Lógica de negócio e fluxo da aplicação

### 📊 Estrutura do Banco de Dados

O sistema possui **15+ tabelas** principais:
- `usuarios_sistema` - Usuários do sistema
- `visitantes` - Dados dos visitantes
- `atracoes` - Informações das atrações
- `tipos_ingressos` - Tipos de ingressos disponíveis
- `compras_ingressos` - Transações de compra
- `itens_compra_ingressos` - Ingressos individuais
- `shows` - Programação de shows
- `lanchonetes` - Estabelecimentos de alimentação
- `cardapio_itens` - Itens do cardápio
- `avaliacoes` - Sistema de avaliações
- `checkins_atracao` - Check-ins gamificados
- `itinerarios` - Roteiros personalizados
- E mais...

## 🎨 Interface

O sistema possui **20+ telas** diferentes:

### Telas Principais
- **Login/Cadastro** - Autenticação de usuários
- **Home do Usuário** - Dashboard principal
- **Home do Admin** - Painel administrativo

### Módulos do Usuário
- **Lista de Atrações** - Visualização de todas as atrações
- **Detalhes da Atração** - Informações completas + avaliações
- **Lista de Shows** - Programação de espetáculos
- **Lanchonetes** - Cardápios e estabelecimentos
- **Compra de Ingressos** - Sistema de vendas
- **Meus Ingressos** - Histórico de compras
- **Meu Perfil** - Dados pessoais e pontuação
- **Criar Itinerário** - Planejamento de visita
- **Mapa do Parque** - Localização das atrações

### Módulos Administrativos
- **Gerenciar Atrações** - CRUD completo
- **Gerenciar Shows** - Controle de programação
- **Gerenciar Lanchonetes** - Administração de estabelecimentos
- **Gerenciar Usuários** - Controle de acesso

## 🔧 Componentes Customizados

- **HeaderLabel** - Cabeçalhos padronizados
- **StyledButton** - Botões com tema personalizado
- **ClickableLabel** - Labels interativos
- **RatingPopup** - Sistema de avaliação com estrelas
- **FormPopups** - Formulários modais para CRUD

## 🎯 Funcionalidades Avançadas

### Gamificação
- Sistema de pontos por check-ins
- Ranking de usuários mais ativos
- Badges e conquistas

### Segurança
- Hash SHA-256 para senhas
- Validação de dados de entrada
- Controle de acesso por roles
- Códigos únicos para ingressos

### Experiência do Usuário
- Interface responsiva
- Navegação intuitiva
- Feedback visual para ações
- Popups informativos
- Scroll views para listas grandes

## 📱 Multiplataforma

Graças ao Kivy, o sistema roda nativamente em:
- **Windows** (testado)
- **Linux** 
- **macOS**
- **Android** (com buildozer)
- **iOS** (com kivy-ios)

## 🚀 Como Executar

1. **Instalar dependências:**
```bash
pip install kivy
```

2. **Executar o sistema:**
```bash
python main.py
```

3. **Login padrão:**
- Usuário: `admin`
- Senha: `admin123`

## 📈 Estatísticas do Projeto

- **Linhas de código:** ~3.000+
- **Telas implementadas:** 20+
- **Tabelas no banco:** 15+
- **Funcionalidades principais:** 10+
- **Tempo de desenvolvimento:** 3+ meses

## 🎓 Aprendizados

Este projeto me permitiu aprofundar conhecimentos em:
- Desenvolvimento de interfaces desktop com Kivy
- Modelagem de banco de dados complexo
- Arquitetura MVC em Python
- Gestão de estado em aplicações desktop
- Criptografia e segurança
- UX/UI para aplicações desktop
- Integração entre SQLite e MySQL

## 🔮 Próximas Funcionalidades

- [ ] Relatórios em PDF
- [ ] Integração com APIs de pagamento reais
- [ ] Sistema de notificações push
- [ ] Modo offline completo
- [ ] Dashboard com gráficos
- [ ] Exportação de dados

## 📞 Contato

**Renan Gomes Lobo**
- Email: renan.gomesdf3@email.com
- Instagram: [@renan.gomeslobo](https://instagram.com/renan.gomeslobo)
- Telefone: (61) 99947-1051

---

*Desenvolvido com ❤️ por Renan Gomes Lobo*
