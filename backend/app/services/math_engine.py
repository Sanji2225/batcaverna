import math
import random
import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError

def process_latex_function(latex_str):
    """
    Motor matemático: Converte o modelo LaTeX (que vem da lib Mathlive.io do front) para sympy e realiza a análise de linearidade.
    """
    try:
        expressao = parse_latex(latex_str).doit()
    except LaTeXParsingError:
        raise ValueError("O formato LaTeX fornecido é inválido ou não suportado.")
    except Exception as e:
        raise ValueError(f"Erro ao processar o modelo matemático: {str(e)}")

    variaveis = list(expressao.free_symbols)
    is_linear = True
    
    if variaveis:
        try:
            polinomio = sp.Poly(expressao, *variaveis)
            if polinomio.total_degree() > 1:
                is_linear = False
        except sp.PolynomialError:
            is_linear = False
            
    return {
        "parsed_expression": str(expressao),
        "is_linear": is_linear,
        "variables": [str(v) for v in variaveis]
    }

def rodar_direcoes_aleatorias(expressao_str, vars_str_list, objetivo, x_inicial=None, step_size=0.1, max_iter=1000):
    """
    Executa o método de otimização por Direções Aleatórias recebendo 
    a equação e as variáveis em formato string.
    """
    # 1. Reconstrói os objetos SymPy a partir das strings
    variaveis_sympy = [sp.Symbol(v) for v in vars_str_list]
    expressao_sympy = sp.parse_expr(expressao_str)
    n_vars = len(variaveis_sympy)
    
    # 2. Verifica se a função possui variáveis
    if n_vars == 0:
        return {
            "ponto_otimo": {},
            "valor_otimo": float(expressao_sympy),
            "iteracoes_realizadas": 0,
            "mensagem": "A função é constante, não há variáveis para otimizar."
        }

    # 3. Converte para uma função executável usando a biblioteca 'math' padrão do Python
    func = sp.lambdify(variaveis_sympy, expressao_sympy, modules=['math'])

    # 4. Define o ponto de partida (usando listas padrão)
    if x_inicial is None:
        x_atual = [0.0] * n_vars
    else:
        x_atual = [float(x) for x in x_inicial]

    # 5. Avaliação do ponto inicial
    try:
        f_atual = func(*x_atual)
    except Exception as e:
        raise ValueError(f"Erro ao calcular a função no ponto inicial: {str(e)}")

    is_max = (objetivo.lower() == 'max')

    # 6. Loop Principal do Algoritmo
    for _ in range(max_iter):
        # Gera uma direção aleatória usando a distribuição gaussiana do pacote 'random'
        direcao = [random.gauss(0.0, 1.0) for _ in range(n_vars)]
        
        # Calcula a norma Euclidiana
        norma = math.sqrt(sum(d**2 for d in direcao))
        if norma == 0:
            continue
            
        # Normaliza o vetor direção
        direcao_normalizada = [d / norma for d in direcao]

        # Calcula o novo ponto (soma de listas ponto a ponto)
        x_novo = [x_atual[i] + step_size * direcao_normalizada[i] for i in range(n_vars)]
        
        # Avalia a função no novo ponto
        try:
            f_novo = func(*x_novo)
        except (ValueError, ZeroDivisionError):
            # Se o ponto cair fora do domínio (ex: raiz de número negativo, divisão por zero)
            # ignora esta direção e tenta a próxima
            continue

        # Verifica se o novo ponto melhora o objetivo
        melhorou = (f_novo > f_atual) if is_max else (f_novo < f_atual)

        if melhorou:
            x_atual = x_novo
            f_atual = f_novo

    # 7. Estruturação do resultado final
    resultado = {
        "ponto_otimo": {var_nome: float(val) for var_nome, val in zip(vars_str_list, x_atual)},
        "valor_otimo": float(f_atual),
        "iteracoes_realizadas": max_iter,
        "step_size_utilizado": step_size
    }
    
    return resultado
