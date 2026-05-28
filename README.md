# Projeto Batcaverna: Otimização de Funções Não Lineares

Repositório central do sistema de otimização matemática para a disciplina de Otimização Não Linear (Engenharia de Sistemas - UNIMONTES).

Este projeto é dividido em duas frentes:
- **Backend (`/backend`)**: API construída em Python (Flask + SymPy) responsável por interpretar modelos matemáticos em LaTeX, validar a não-linearidade e executar os métodos numéricos.
- **Frontend (`/frontend`)**: Interface de usuário interativa construída em React.

---

## Backend (Python / Flask)

O backend atua como o motor matemático da aplicação. Ele recebe as requisições, transforma o LaTeX em expressões algébricas (SymPy), garante que a função é não-linear e então executa os algoritmos.

### Como rodar o Backend localmente

1. Abra o terminal e navegue até a pasta do backend:
   ```bash
   cd backend
   ```

2. Crie um ambiente virtual para isolar as dependências:
   ```bash
   python -m venv .venv
   ```

3. Ative o ambiente virtual:
   - **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
   - **Linux / Mac:** `source .venv/bin/activate`

4. Instale as bibliotecas necessárias:
   ```bash
   pip install -r requirements.txt
   ```

5. Inicialize o servidor Flask:
   ```bash
   python run.py
   ```
   *O servidor estará rodando em `http://127.0.0.1:5000` (e também acessível via IP local da rede para a equipe de frontend).*

---

## Documentação da API

O frontend deve se comunicar com o backend através dos endpoints abaixo. Ambos os endpoints compartilham as mesmas regras de validação (campos obrigatórios e rejeição de funções lineares) e o mesmo formato de resposta.

> **Importante sobre os algoritmos:** Os métodos de otimização são implementados manualmente (sem bibliotecas de otimização). O SymPy é usado apenas como auxílio matemático — parsing do LaTeX, derivação simbólica do gradiente e avaliação numérica das expressões (`lambdify`).

### 1. Método de Direções Aleatórias
- **URL:** `POST /api/optimizer/direcoes-aleatorias`
- **Descrição:** Algoritmo heurístico de busca: a cada iteração sorteia uma direção aleatória unitária e só aceita o passo se ele melhorar o objetivo.

### 2. Método do Gradiente
- **URL:** `POST /api/optimizer/gradiente`
- **Descrição:** Algoritmo determinístico baseado no vetor gradiente. Caminha na direção do gradiente para **maximizar** (ascensão) ou na direção oposta para **minimizar** (descida), parando quando a norma do gradiente fica abaixo da tolerância (ponto estacionário).

### Estrutura do Payload (Requisição)

Ambos os endpoints esperam um objeto `JSON` no corpo da requisição (*Body*). O campo `parametros` é opcional — quando omitido, valores padrão são usados.

* **`funcao_latex`** (String): A expressão matemática formatada em LaTeX (gerada pelo MathLive). Lembre-se de escapar barras invertidas no JSON (ex: `\\sin`).
* **`objetivo`** (String): Define a direção da otimização. Valores aceitos: `"min"` ou `"max"`.
* **`parametros`** (Objeto, opcional): Configuração do algoritmo (varia conforme o método).

#### Parâmetros — Direções Aleatórias
```json
{
  "funcao_latex": "x^2 + 2y^2",
  "objetivo": "min",
  "parametros": {
    "step_size": 0.1,
    "max_iter": 1000,
    "x_inicial": [3, 3]
  }
}
```
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `step_size` | Float | `0.1` | Tamanho do passo a cada iteração. |
| `max_iter` | Int | `1000` | Número máximo de iterações. |
| `x_inicial` | Lista | `[0, 0, ...]` | Ponto inicial (ordem alfabética das variáveis, ex: `x`, `y`). |

#### Parâmetros — Gradiente
```json
{
  "funcao_latex": "x^2 + 2y^2",
  "objetivo": "min",
  "parametros": {
    "learning_rate": 0.1,
    "max_iter": 1000,
    "x_inicial": [3, 3],
    "tolerancia": 1e-6
  }
}
```
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `learning_rate` | Float | `0.1` | Taxa de aprendizado (tamanho do passo na direção do gradiente). |
| `max_iter` | Int | `1000` | Número máximo de iterações. |
| `x_inicial` | Lista | `[0, 0, ...]` | Ponto inicial (ordem alfabética das variáveis, ex: `x`, `y`). |
| `tolerancia` | Float | `1e-6` | Critério de parada: para quando a norma do gradiente fica abaixo deste valor. |

### Respostas de Sucesso (Status 200 OK)

Se a função for validada com sucesso (ou seja, confirmada como **não linear**), a API executa o algoritmo e retorna o resultado da otimização.

**Direções Aleatórias:**
```json
{
  "status": "sucesso",
  "metodo": "Direções Aleatórias",
  "objetivo": "MIN",
  "dados_interpretados": {
    "is_linear": false,
    "parsed_expression": "x**2 + 2*y**2",
    "variables": ["x", "y"]
  },
  "resultado": {
    "ponto_otimo": { "x": -0.0036, "y": -0.0132 },
    "valor_otimo": 0.00036,
    "iteracoes_realizadas": 2000,
    "step_size_utilizado": 0.05
  }
}
```

**Gradiente:**
```json
{
  "status": "sucesso",
  "metodo": "Gradiente",
  "objetivo": "MIN",
  "dados_interpretados": {
    "is_linear": false,
    "parsed_expression": "x**2 + 2*y**2",
    "variables": ["x", "y"]
  },
  "resultado": {
    "ponto_otimo": { "x": 4.93e-07, "y": 8.86e-16 },
    "valor_otimo": 2.43e-13,
    "iteracoes_realizadas": 71,
    "convergiu": true,
    "learning_rate_utilizado": 0.1
  }
}
```

### Respostas de Erro (Status 400 Bad Request)

Se o usuário enviar uma **função linear** (ex: `2x + 3y`), o servidor barrará o cálculo imediatamente, pois os métodos são exclusivos para problemas não lineares:
```json
{
  "error": "Modelo Linear detectado.",
  "message": "Os métodos de otimização suportam exclusivamente funções não lineares.",
  "detalhes": {
    "is_linear": true,
    "parsed_expression": "2*x + 3*y",
    "variables": ["x", "y"]
  }
}
```

Outros erros de validação (status 400) incluem campo `funcao_latex` ausente, `objetivo` diferente de `"min"`/`"max"` ou LaTeX inválido.

---

## Frontend

A interface de usuário é construída em React, permitindo a inserção de fórmulas matemáticas via MathLive e a visualização gráfica dos resultados com Plotly.

### Bibliotecas Principais
- **React**: Biblioteca base para a UI.
- **MathLive**: Componente para entrada de fórmulas matemáticas (LaTeX).
- **Plotly.js / React-Plotly.js**: Renderização de gráficos 2D e 3D.
- **Math.js**: Utilitários matemáticos para o frontend.

### Como rodar o Frontend localmente

1. Navegue até a pasta do frontend:
   ```bash
   cd frontend
   ```

2. Instale as dependências:
   ```bash
   npm install
   ```

3. Inicie a aplicação:
   ```bash
   npm start
   ```
   *A aplicação abrirá automaticamente em `http://localhost:3000`.*

---
*Projeto desenvolvido para fins acadêmicos - UNIMONTES.*