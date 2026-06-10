import math
import random
import numpy as np
import sympy as sp
from sympy.parsing.latex.errors import LaTeXParsingError

def sanitize_and_parse(s):
    """
    Tenta converter uma string (LaTeX, ASCII ou Math) para SymPy de forma agressiva.
    """
    if not s or not isinstance(s, str): return None
    
    # Remove "f(x,y) =" ou similares
    if '=' in s:
        s = s.split('=')[-1].strip()

    # 1. Tenta sympify direto (notação de programação)
    try:
        return sp.sympify(s)
    except Exception:
        pass

    # 2. Tenta parse_latex padrão
    try:
        return parse_latex(s).doit()
    except Exception:
        pass

    # 3. Limpeza agressiva para fallback
    # Substitui padrões LaTeX por notação matemática padrão
    s_clean = s.replace('**', '^')
    s_clean = s_clean.replace('\\cdot', '*').replace('\\times', '*')
    s_clean = s_clean.replace('\\left(', '(').replace('\\right)', ')')
    s_clean = s_clean.replace('\\left[', '[').replace('\\right]', ']')
    s_clean = s_clean.replace('{', '(').replace('}', ')')
    s_clean = s_clean.replace('\\', '') # Remove barras restantes

    try:
        return sp.sympify(s_clean)
    except Exception:
        pass

    # 4. Tenta parse_latex com a string limpa (caso tenha sobrado algo)
    try:
        return parse_latex(s_clean).doit()
    except Exception:
        pass

    return None

def process_latex_function(latex_str, constraints_latex=None):
    """
    Motor matemático: Converte o modelo para sympy usando o parser robusto.
    """
    expressao = sanitize_and_parse(latex_str)
    
    if expressao is None:
        raise ValueError("O formato da função é inválido. Use LaTeX ou notação matemática padrão (ex: x^2 + 2*y).")

    variaveis = sorted(list(expressao.free_symbols), key=lambda x: x.name)
    is_linear = False # Assume não linear por padrão se for constante (ou sem vars)
    
    if variaveis:
        is_linear = True # Se tem variáveis, testamos
        try:
            polinomio = sp.Poly(expressao, *variaveis)
            if polinomio.total_degree() > 1:
                is_linear = False
        except sp.PolynomialError:
            is_linear = False

    restricoes_sympy = []
    if constraints_latex:
        for c_latex in constraints_latex:
            if not c_latex.strip(): continue
            c_expr = sanitize_and_parse(c_latex)
            if c_expr is not None:
                restricoes_sympy.append(c_expr)
            
    return {
        "parsed_expression": str(expressao),
        "is_linear": is_linear,
        "variables": [str(v) for v in variaveis],
        "sympy_expr": expressao,
        "sympy_vars": variaveis,
        "sympy_constraints": restricoes_sympy
    }

def gerar_grid(expressao_sympy, variaveis_sympy, range_val=5, step=0.5):
    """
    Gera a malha topográfica (Grid 3D) para o frontend.
    Suporta apenas 2 variáveis (x e y).
    """
    if len(variaveis_sympy) != 2:
        return None

    # Garante que a ordem seja x, y
    vars_map = {v.name: v for v in variaveis_sympy}
    x_sym = vars_map.get('x')
    y_sym = vars_map.get('y')

    if not x_sym or not y_sym:
        return None

    func = sp.lambdify((x_sym, y_sym), expressao_sympy, modules=['numpy', 'math'])

    x_vals = []
    y_vals = []
    curr = -float(range_val)
    while curr <= range_val:
        x_vals.append(round(curr, 2))
        y_vals.append(round(curr, 2))
        curr += step

    z_vals = []
    for xv in x_vals:
        row = []
        for yv in y_vals:
            try:
                row.append(float(func(xv, yv)))
            except (ValueError, ZeroDivisionError, TypeError):
                row.append(0.0)
        z_vals.append(row)

    return {"x": x_vals, "y": y_vals, "z": z_vals}

def avaliar_restricoes_compiladas(ponto_vals, restricoes_funcs):
    """
    Verifica se um ponto viola alguma restrição g(x) <= 0 usando funções compiladas.
    """
    for r_func in restricoes_funcs:
        if float(r_func(*ponto_vals)) > 0:
            return False
    return True

def rodar_gradiente(expressao_sympy, variaveis_sympy, objetivo, restricoes_sympy=None, x_inicial=None, step_size=0.1, max_iter=100, tolerance=0.0001):
    """
    Executa a Descida/Ascensão do Gradiente com Momentum para convergência acelerada.
    """
    restricoes_sympy = restricoes_sympy or []
    if len(variaveis_sympy) != 2:
        raise ValueError("O método do gradiente suporta exatamente 2 variáveis (x e y).")

    vars_map = {v.name: v for v in variaveis_sympy}
    x_sym, y_sym = vars_map.get('x'), vars_map.get('y')

    f_func = sp.lambdify((x_sym, y_sym), expressao_sympy, modules=['numpy', 'math'])
    dx_func = sp.lambdify((x_sym, y_sym), sp.diff(expressao_sympy, x_sym), modules=['numpy', 'math'])
    dy_func = sp.lambdify((x_sym, y_sym), sp.diff(expressao_sympy, y_sym), modules=['numpy', 'math'])
    restricoes_funcs = [sp.lambdify((x_sym, y_sym), r, modules=['numpy', 'math']) for r in restricoes_sympy]

    curr_x, curr_y = x_inicial if x_inicial else [0.0, 0.0]
    
    hist_x, hist_y, hist_z = [curr_x], [curr_y], [float(f_func(curr_x, curr_y))]
    is_max = (objetivo.lower() == 'max')
    mult = 1 if is_max else -1

    # Memória para o passo de Barzilai-Borwein (BB)
    prev_x, prev_y = None, None
    prev_gx, prev_gy = None, None

    for _ in range(int(max_iter)):
        try:
            gx, gy = float(dx_func(curr_x, curr_y)), float(dy_func(curr_x, curr_y))
            f_atual = float(f_func(curr_x, curr_y))
        except (ValueError, ZeroDivisionError): break

        norm = math.sqrt(gx**2 + gy**2)
        if norm < tolerance: break

        # Direção Exata do Gradiente Puro
        p_x = mult * gx
        p_y = mult * gy
        
        # Produto escalar do gradiente com a direção para o Armijo
        m = gx * p_x + gy * p_y

        # Barzilai-Borwein (BB): Chute inteligente para o tamanho do passo inicial
        if prev_x is not None:
            s_x = curr_x - prev_x
            s_y = curr_y - prev_y
            
            # Variação do gradiente de minimização (-mult * g)
            y_x = -mult * gx - (-mult * prev_gx)
            y_y = -mult * gy - (-mult * prev_gy)
            
            s_dot_s = s_x**2 + s_y**2
            s_dot_y = s_x * y_x + s_y * y_y
            
            # Aproximação escalar da Hessiana Inversa (Passo BB)
            if s_dot_y > 1e-10:
                alpha = s_dot_s / s_dot_y
            else:
                alpha = 1.0
        else:
            alpha = 1.0 
            
        c = 1e-4
        rho = 0.5
        
        while True:
            prox_x = curr_x + alpha * p_x
            prox_y = curr_y + alpha * p_y
            
            if restricoes_funcs and not avaliar_restricoes_compiladas([prox_x, prox_y], restricoes_funcs):
                alpha *= rho
                if alpha < 1e-10: break
                continue

            try:
                f_prox = float(f_func(prox_x, prox_y))
                # Condição de Armijo
                if is_max:
                    if f_prox >= f_atual + c * alpha * m:
                        break
                else:
                    if f_prox <= f_atual + c * alpha * m:
                        break
            except (ValueError, ZeroDivisionError, TypeError):
                pass
                
            alpha *= rho
            if alpha < 1e-10:
                break

        if math.sqrt((prox_x - curr_x)**2 + (prox_y - curr_y)**2) < 1e-9:
            curr_x, curr_y = prox_x, prox_y
            hist_x.append(curr_x); hist_y.append(curr_y); hist_z.append(float(f_func(curr_x, curr_y)))
            break

        # Salva as posições atuais para o cálculo do BB na próxima iteração
        prev_x, prev_y = curr_x, curr_y
        prev_gx, prev_gy = gx, gy

        curr_x, curr_y = prox_x, prox_y
        hist_x.append(curr_x); hist_y.append(curr_y); hist_z.append(float(f_func(curr_x, curr_y)))

    return {
        "path": {"x": hist_x, "y": hist_y, "z": hist_z},
        "iterations": len(hist_x) - 1,
        "ponto_otimo": {"x": curr_x, "y": curr_y},
        "valor_otimo": hist_z[-1]
    }
    
def rodar_direcoes_aleatorias(expressao_sympy, variaveis_sympy, objetivo, restricoes_sympy=None, x_inicial=None, step_size=0.1, max_iter=1000, tolerance=0.0001):
    """
    Otimização por Direções Aleatórias com Step Size adaptativo e parada antecipada.
    """
    restricoes_sympy = restricoes_sympy or []
    n_vars = len(variaveis_sympy)
    if n_vars == 0:
        return {"ponto_otimo": {}, "valor_otimo": float(expressao_sympy), "iteracoes_realizadas": 0}

    func = sp.lambdify(variaveis_sympy, expressao_sympy, modules=['numpy', 'math'])
    restricoes_funcs = [sp.lambdify(variaveis_sympy, r, modules=['numpy', 'math']) for r in restricoes_sympy]
    
    x_atual = [float(x) for x in x_inicial] if x_inicial else [0.0] * n_vars
    f_inicial = float(func(*x_atual))
    f_atual = f_inicial
    is_max = (objetivo.lower() == 'max')

    paciencia = 80 
    tentativas_sem_melhora = 0
    passos_com_sucesso = 0
    curr_step = float(step_size)
    
    # Têmpera Simulada (Simulated Annealing)
    temperatura = 1.0
    taxa_resfriamento = 0.99
    
    direcao_vencedora = None # Memória de Sucesso

    for i in range(int(max_iter)):
        if direcao_vencedora is not None:
            # Reutiliza a direção que gerou progresso na última iteração
            direcao = direcao_vencedora
        else:
            # Sorteia e normaliza uma nova direção aleatória
            direcao_bruta = [random.gauss(0.0, max(0.1, temperatura)) for _ in range(n_vars)]
            norma = math.sqrt(sum(d**2 for d in direcao_bruta))
            if norma == 0: continue
            direcao = [d/norma for d in direcao_bruta]
            
        x_novo = [x_atual[j] + curr_step * direcao[j] for j in range(n_vars)]
        
        try:
            if restricoes_funcs and not avaliar_restricoes_compiladas(x_novo, restricoes_funcs):
                direcao_vencedora = None # Bateu na parede, esquece a direção
                tentativas_sem_melhora += 1
                curr_step *= 0.95
                if tentativas_sem_melhora > paciencia: break
                continue
            
            f_novo = float(func(*x_novo))
            delta = f_novo - f_atual
            
            melhorou = (delta > 1e-9) if is_max else (delta < -1e-9)
            
            aceitar_pior = False
            if not melhorou and temperatura > 0.1 and direcao_vencedora is None:
                p_aceitacao = math.exp(-abs(delta) / temperatura)
                if random.random() < p_aceitacao:
                    aceitar_pior = True
            
            if melhorou or aceitar_pior:
                x_atual, f_atual = x_novo, f_novo
                if melhorou:
                    direcao_vencedora = direcao # Memoriza o acerto para acelerar no mesmo sentido
                    tentativas_sem_melhora = 0 
                    passos_com_sucesso += 1
                    curr_step *= 1.2 # Embala na descida boa (aumenta o passo mais agressivamente)
            else:
                direcao_vencedora = None # Direção falhou, limpa a memória
                tentativas_sem_melhora += 1
                curr_step *= 0.95 
        
            temperatura *= taxa_resfriamento
            
            if tentativas_sem_melhora > paciencia:
                break
                
        except (ValueError, ZeroDivisionError, TypeError): 
            direcao_vencedora = None
            continue

    vars_str_list = [str(v) for v in variaveis_sympy]
    return {
        "ponto_otimo": {name: val for name, val in zip(vars_str_list, x_atual)},
        "valor_otimo": float(f_atual),
        "valor_inicial": float(f_inicial),
        "iteracoes_realizadas": passos_com_sucesso
    }
