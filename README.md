# MAZURON ERP

**Mais controle para o seu negócio.**

O MAZURON ERP é um sistema de gestão empresarial desenvolvido para pequenos negócios, com foco inicial em microempreendedores que fabricam e comercializam produtos utilizando impressão 3D.

O projeto busca centralizar o controle de materiais, estoque, compras, produção, produtos e finanças em uma aplicação desktop simples, organizada e confiável.

<details>
<summary>Prévia da proposta</summary>

- Gestão de produtos e materiais.
- Controle de estoque por movimentações.
- Registro de compras e fornecedores.
- Controle de receitas e produção.
- Gestão de vendas e financeiro.
- Integração futura com Telegram para lançamentos por mensagens.

</details>

> **Status:** Em desenvolvimento.

---

## Objetivos do projeto

- Facilitar a gestão de pequenos negócios.
- Reduzir controles manuais e planilhas dispersas.
- Garantir consistência e rastreabilidade das movimentações de estoque.
- Automatizar cálculos de custos de materiais e produção.
- Oferecer uma interface desktop intuitiva e profissional.
- Preparar uma futura integração com Telegram para facilitar os lançamentos do dia a dia.

## Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal |
| PySide6 | Interface gráfica desktop |
| SQLite | Banco de dados local |
| Pytest | Testes automatizados |
| Ruff | Análise e padronização do código |
| Git | Controle de versão |

## Funcionalidades implementadas

### Produtos
- Cadastro e gerenciamento de produtos.
- Organização por categorias.
- Controle de preço de venda.

### Materiais
- Cadastro e gerenciamento de matérias-primas.
- Definição de unidades de medida.
- Configuração de estoque mínimo.

### Estoque
- Registro de movimentações.
- Entradas e saídas de materiais.
- Controle de saldo e valorização.
- Cálculo de custo médio.
- Histórico de movimentações.
- Estorno de movimentações sem apagar o histórico original.

### Fornecedores
- Cadastro de fornecedores.
- Consulta e atualização de dados.
- Desativação de cadastros.

### Compras
- Registro de compras de materiais.
- Associação opcional a fornecedores.
- Registro de nota fiscal.
- Inclusão de frete e descontos.
- Conversão de unidades de compra.
- Atualização automática do estoque.
- Incorporação dos custos adicionais ao custo de aquisição.

## Arquitetura e integridade dos dados

O projeto utiliza SQLite como banco de dados local e separa as responsabilidades entre interface gráfica, serviços de negócio e persistência.

Algumas decisões importantes:

- O estoque é calculado a partir de um histórico de movimentações.
- Valores monetários são armazenados em centavos inteiros.
- Quantidades são armazenadas em milésimos da unidade de medida.
- Operações críticas utilizam transações no banco de dados.
- Estornos preservam o histórico por meio de novas movimentações.
- O custo médio é calculado a partir dos valores de aquisição.

## Estrutura do projeto

```text
mini-erp/
├── app/
│   ├── database/
│   │   ├── connection.py
│   │   ├── initialize.py
│   │   └── seed_units.py
│   ├── services/
│   │   ├── unit_converter.py
│   │   ├── cost_calculator.py
│   │   ├── supplier_service.py
│   │   ├── material_service.py
│   │   ├── stock_service.py
│   │   ├── average_cost_calculator.py
│   │   ├── purchase_service.py
│   │   ├── product_service.py
│   │   ├── recipe_service.py
│   │   ├── recipe_cost_calculator.py
│   │   └── production_service.py
│   ├── ui/
│   │   ├── pages/
│   │   ├── main_window.py
│   │   └── styles.py
│   └── main.py
├── tests/
├── requirements.txt
└── README.md
```

## Como executar o projeto

### 1. Pré-requisitos

- Windows.
- Python 3.13 ou superior.
- Git.

### 2. Clonar o repositório

```powershell
git clone https://github.com/LucasMazur/mini-erp.git
cd mini-erp
```

### 3. Criar o ambiente virtual

```powershell
python -m venv .venv
```

### 4. Ativar o ambiente virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5. Instalar as dependências

```powershell
python -m pip install -r requirements.txt
```

### 6. Executar a aplicação

```powershell
python -m app.main
```

## Testes e qualidade do código

Para executar os testes automatizados:

```powershell
python -m pytest -v
```

Para verificar a qualidade e padronização do código:

```powershell
ruff check app tests
```

## Próximas etapas

O desenvolvimento seguirá com a implementação de:

- Finalização da interface de compras e consulta do histórico de compras.
- Gestão de receitas e composição de produtos.
- Controle de produção e consumo de materiais.
- Gestão de vendas.
- Módulo financeiro.
- Relatórios gerenciais.
- Integração com Telegram para lançamentos por mensagens.
- Empacotamento e distribuição para Windows.

## Autor

**Lucas Mazur**

GitHub: [@LucasMazur](https://github.com/LucasMazur)

---

*MAZURON ERP — Mais controle para o seu negócio.*