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

O frontend deve se comunicar com o backend através dos endpoints abaixo. Ambos os endpoints compartilham a mesma estrutura de requisição e as mesmas regras de validação.

### 1. Método de Direções Aleatórias
- **URL:** `POST /api/optimizer/direcoes-aleatorias`
- **Descrição:** Aciona o algoritmo heurístico de busca por direções aleatórias.

### 2. Método do Gradiente
- **URL:** `POST /api/optimizer/gradiente`
- **Descrição:** Aciona o algoritmo determinístico baseado no vetor gradiente (Descida ou Ascensão).

### Estrutura do Payload (Requisição)

Ambos os endpoints esperam um objeto `JSON` no corpo da requisição (*Body*):
```json
{
  "funcao_latex": "\\sin(x) + x^2 - y",
  "objetivo": "min"
}
```
* **`funcao_latex`** (String): A expressão matemática formatada em LaTeX (gerada pelo MathLive). Lembre-se de escapar barras invertidas no JSON (ex: `\\sin`).
* **`objetivo`** (String): Define a direção da otimização. Valores aceitos: `"min"` ou `"max"`.

### Respostas de Sucesso (Status 200 OK)

Se a função for validada com sucesso (ou seja, for confirmada como **não linear**), a API retornará os dados processados:
```json
{
  "status": "sucesso",
  "metodo": "Gradiente",
  "objetivo": "MIN",
  "mensagem": "Função não linear validada. (Cálculo real do algoritmo será implementado aqui)",
  "dados_interpretados": {
    "is_linear": false,
    "parsed_expression": "x**2 - y + sin(x)",
    "variables": ["x", "y"]
  }
}
```

### Respostas de Erro (Status 400 Bad Request)

Se o usuário enviar uma **função linear** (ex: `2x + 3y`), o servidor barrará o cálculo imediatamente, pois os métodos são exclusivos para problemas não lineares:
```json
{
  "codigo": 400,
  "valido": false,
  "resposta": {
    "error": "Modelo Linear detectado.",
    "message": "Os métodos de otimização suportam exclusivamente funções não lineares.",
    "detalhes": {
      "is_linear": true,
      "parsed_expression": "2*x + 3*y",
      "variables": ["x", "y"]
    }
  }
}
```

---

## Frontend

> **Aviso para a equipe de Frontend:** Preencham esta seção com as instruções de como instalar as dependências do React (`npm install`), como rodar o servidor de desenvolvimento (`npm run dev` ou `npm start`) e quais bibliotecas principais estão sendo utilizadas (ex: Vite, MathLive, Axios, etc.).

### Como rodar o Frontend localmente

1. Navegue até a pasta do frontend:
   ```bash
   cd frontend
   
```

2. Instale as dependências:
   ```bash
   [Comando de instalação aqui]
   ```

3. Inicie a aplicação:
   
```bash
   [Comando de execução aqui]
   ```

---
*Projeto desenvolvido para fins acadêmicos - UNIMONTES.*