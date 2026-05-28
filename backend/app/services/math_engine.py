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

    # Ordena as variáveis pelo nome para manter uma ordem determinística (ex: x, y)
    variaveis = sorted(expressao.free_symbols, key=lambda s: s.name)
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
        "variables": [str(v) for v in variaveis],
        "sympy_expr": expressao,
        "sympy_vars": variaveis
    }
    
def rodar_direcoes_aleatorias(expressao_sympy, variaveis_sympy, objetivo, x_inicial=None, step_size=0.1, max_iter=1000):
    """
    Executa o método de otimização por Direções Aleatórias recebendo 
    diretamente os objetos SymPy (Sem necessidade de parse_expr).
    """
    n_vars = len(variaveis_sympy)
    
    # Verifica se a função possui variáveis
    if n_vars == 0:
        return {
            "ponto_otimo": {},
            "valor_otimo": float(expressao_sympy),
            "iteracoes_realizadas": 0,
            "mensagem": "A função é constante, não há variáveis para otimizar."
        }

    # Converte para uma função executável
    func = sp.lambdify(variaveis_sympy, expressao_sympy, modules=['math'])

    if x_inicial is None:
        x_atual = [0.0] * n_vars
    else:
        x_atual = [float(x) for x in x_inicial]

    try:
        f_atual = func(*x_atual)
    except Exception as e:
        raise ValueError(f"Erro ao calcular a função no ponto inicial: {str(e)}")

    is_max = (objetivo.lower() == 'max')

    # Loop Principal do Algoritmo
    for _ in range(max_iter):
        direcao = [random.gauss(0.0, 1.0) for _ in range(n_vars)]
        
        norma = math.sqrt(sum(d**2 for d in direcao))
        if norma == 0:
            continue
            
        direcao_normalizada = [d / norma for d in direcao]
        x_novo = [x_atual[i] + step_size * direcao_normalizada[i] for i in range(n_vars)]
        
        try:
            f_novo = func(*x_novo)
        except (ValueError, ZeroDivisionError):
            continue

        melhorou = (f_novo > f_atual) if is_max else (f_novo < f_atual)

        if melhorou:
            x_atual = x_novo
            f_atual = f_novo

    # Estruturação do resultado final
    vars_str_list = [str(v) for v in variaveis_sympy]
    resultado = {
        "ponto_otimo": {var_nome: float(val) for var_nome, val in zip(vars_str_list, x_atual)},
        "valor_otimo": float(f_atual),
        "iteracoes_realizadas": max_iter,
        "step_size_utilizado": step_size
    }
    
    return resultado


def rodar_gradiente(expressao_sympy, variaveis_sympy, objetivo, x_inicial=None, learning_rate=0.1, max_iter=1000, tolerancia=1e-6):
    """
    Executa o método de otimização por Gradiente (Descida/Ascensão) recebendo
    diretamente os objetos SymPy.

    O SymPy é usado apenas como auxílio matemático: derivação simbólica do
    gradiente e avaliação numérica da função/derivadas (lambdify). O algoritmo
    de otimização em si (atualização do ponto e critério de parada) é implementado
    manualmente, sem nenhuma biblioteca de otimização.
    """
    n_vars = len(variaveis_sympy)

    if n_vars == 0:
        return {
            "ponto_otimo": {},
            "valor_otimo": float(expressao_sympy),
            "iteracoes_realizadas": 0,
            "mensagem": "A função é constante, não há variáveis para otimizar."
        }

    # Gradiente simbólico: vetor de derivadas parciais (auxílio matemático do SymPy)
    gradiente_simbolico = [sp.diff(expressao_sympy, var) for var in variaveis_sympy]

    # Converte a função e cada derivada parcial em funções executáveis
    func = sp.lambdify(variaveis_sympy, expressao_sympy, modules=['math'])
    grad_funcs = [sp.lambdify(variaveis_sympy, derivada, modules=['math']) for derivada in gradiente_simbolico]

    if x_inicial is None:
        x_atual = [0.0] * n_vars
    else:
        x_atual = [float(x) for x in x_inicial]

    try:
        f_atual = func(*x_atual)
    except Exception as e:
        raise ValueError(f"Erro ao calcular a função no ponto inicial: {str(e)}")

    is_max = (objetivo.lower() == 'max')

    # Para maximizar, sobe-se na direção do gradiente (+); para minimizar, desce-se (-)
    sinal = 1.0 if is_max else -1.0

    iteracoes_realizadas = 0
    convergiu = False

    # Loop Principal do Algoritmo
    for i in range(max_iter):
        iteracoes_realizadas = i + 1

        try:
            grad_atual = [derivada(*x_atual) for derivada in grad_funcs]
        except (ValueError, ZeroDivisionError):
            break

        # Norma do gradiente (math, apenas auxílio para o critério de parada)
        norma = math.sqrt(sum(g**2 for g in grad_atual))

        # Critério de parada: gradiente próximo de zero indica ponto estacionário
        if norma < tolerancia:
            convergiu = True
            break

        x_novo = [x_atual[j] + sinal * learning_rate * grad_atual[j] for j in range(n_vars)]

        try:
            f_novo = func(*x_novo)
        except (ValueError, ZeroDivisionError):
            break

        x_atual = x_novo
        f_atual = f_novo

    # Estruturação do resultado final
    vars_str_list = [str(v) for v in variaveis_sympy]
    resultado = {
        "ponto_otimo": {var_nome: float(val) for var_nome, val in zip(vars_str_list, x_atual)},
        "valor_otimo": float(f_atual),
        "iteracoes_realizadas": iteracoes_realizadas,
        "convergiu": convergiu,
        "learning_rate_utilizado": learning_rate
    }

    return resultado
