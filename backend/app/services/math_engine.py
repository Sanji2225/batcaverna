import math
import random
import numpy as np
import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError

def sanitize_and_parse(s):
    """
    Tenta converter uma string (LaTeX, ASCII ou Math) para SymPy de forma agressiva.
    """
    if not s or not isinstance(s, str): return None

    # Remove "f(x,y) =" ou similares, mas PRESERVA desigualdades das restrições
    # (<=, >=, ==, !=), pois elas são fundamentais para o modelo g(x,y) <= 0.
    _rel_ops = ('<=', '>=', '==', '!=', '\\le', '\\ge', '\\leq', '\\geq', '\\neq')
    if '=' in s and not any(op in s for op in _rel_ops):
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
            if not c_latex or not c_latex.strip(): continue
            c_expr = sanitize_and_parse(c_latex)
            if c_expr is None:
                continue

            # Normaliza qualquer relação (g >= h, g <= h, g = h) para a forma
            # padrão do modelo: g'(x,y) <= 0. Assim o usuário pode digitar a
            # restrição completa (ex.: "x + y >= 5") em vez de só a expressão.
            if isinstance(c_expr, sp.core.relational.Relational):
                if c_expr.rel_op in ('>=', '>'):
                    c_expr = c_expr.rhs - c_expr.lhs
                else:  # '<=', '<', '==', '!='
                    c_expr = c_expr.lhs - c_expr.rhs

            restricoes_sympy.append(c_expr)
            
    return {
        "parsed_expression": str(expressao),
        "is_linear": is_linear,
        "variables": [str(v) for v in variaveis],
        "sympy_expr": expressao,
        "sympy_vars": variaveis,
        "sympy_constraints": restricoes_sympy
    }

def _gerar_eixos(range_val=5, step=0.5):
    """Gera o vetor de coordenadas de um eixo (compartilhado por objetivo e restrições)."""
    vals = []
    curr = -float(range_val)
    while curr <= range_val:
        vals.append(round(curr, 2))
        curr += step
    return vals

def _avaliar_malha(func, x_vals, y_vals):
    """
    Avalia func(x, y) sobre a malha (linhas = y, colunas = x). Vetoriza com numpy
    (necessário com o grid fino); cai no laço ponto-a-ponto se a expressão não
    suportar broadcasting. Retorna um array numpy com np.nan onde não avaliou.
    """
    X, Y = np.meshgrid(np.array(x_vals, dtype=float), np.array(y_vals, dtype=float))
    try:
        with np.errstate(all='ignore'):
            Z = func(X, Y)
        Z = np.asarray(Z, dtype=float)
        if Z.shape != X.shape:      # expressão constante -> resultado escalar
            Z = np.full(X.shape, float(Z))
        return Z
    except Exception:
        Z = np.empty(X.shape, dtype=float)
        for i, yv in enumerate(y_vals):
            for j, xv in enumerate(x_vals):
                try:
                    Z[i, j] = float(func(xv, yv))
                except (ValueError, ZeroDivisionError, TypeError):
                    Z[i, j] = np.nan
        return Z

def gerar_grid(expressao_sympy, variaveis_sympy, range_val=5, step=0.1):
    """
    Gera a malha topográfica (Grid 3D) para o frontend.
    Suporta apenas 2 variáveis (x e y).

    Convenção do Plotly: z[i][j] corresponde ao ponto (x[j], y[i]).
    Ou seja, as LINHAS variam em y e as COLUNAS variam em x.
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

    x_vals = _gerar_eixos(range_val, step)
    y_vals = _gerar_eixos(range_val, step)

    Z = _avaliar_malha(func, x_vals, y_vals)
    Z = np.where(np.isfinite(Z), Z, 0.0)   # buracos viram 0 (superfície contínua)

    return {"x": x_vals, "y": y_vals, "z": Z.tolist()}

def gerar_grid_restricoes(restricoes_sympy, variaveis_sympy, range_val=5, step=0.1):
    """
    Para cada restrição g(x,y) <= 0, gera uma malha 2D com os valores de g
    sobre o MESMO grid da função objetivo. Com isso o frontend consegue
    desenhar a fronteira (g = 0) e sombrear a região inviável (g > 0).

    Retorna uma lista de dicts: [{"latex": str, "x": [...], "y": [...], "z": [[...]]}].
    """
    if len(variaveis_sympy) != 2 or not restricoes_sympy:
        return []

    vars_map = {v.name: v for v in variaveis_sympy}
    x_sym = vars_map.get('x')
    y_sym = vars_map.get('y')
    if not x_sym or not y_sym:
        return []

    x_vals = _gerar_eixos(range_val, step)
    y_vals = _gerar_eixos(range_val, step)

    grids = []
    for r in restricoes_sympy:
        try:
            g_func = sp.lambdify((x_sym, y_sym), r, modules=['numpy', 'math'])
        except Exception:
            continue

        Z = _avaliar_malha(g_func, x_vals, y_vals)
        # Mantém None onde não avaliou (não cria fronteira falsa)
        z_vals = [[(float(v) if np.isfinite(v) else None) for v in row] for row in Z]

        grids.append({"latex": str(r), "x": x_vals, "y": y_vals, "z": z_vals})

    return grids

def avaliar_restricoes_compiladas(ponto_vals, restricoes_funcs):
    """
    Verifica se um ponto viola alguma restrição g(x) <= 0 usando funções compiladas.
    """
    for r_func in restricoes_funcs:
        if float(r_func(*ponto_vals)) > 0:
            return False
    return True

# Se o iterado escapar deste limite, consideramos que o método divergiu
# (função ilimitada na direção de busca). Evita valores como 1e280 que
# tornam o gráfico impossível de renderizar.
DOMINIO_LIMITE = 1e6

def _restaurar_viabilidade(ponto, restricoes_funcs, restricoes_grad_funcs, max_steps=300):
    """
    Métodos de direções viáveis (rejeição de passo) precisam COMEÇAR dentro da
    região viável. Se o ponto inicial violar alguma restrição (algum g_i > 0),
    projeta ele de volta minimizando a violação total via descida de subgradiente
    com backtracking.

    Retorna (ponto_corrigido, viavel_bool).
    """
    p = [float(v) for v in ponto]
    n = len(p)

    def violacao_total(q):
        total = 0.0
        for f in restricoes_funcs:
            try:
                g = float(f(*q))
            except (ValueError, ZeroDivisionError, TypeError):
                g = float('inf')
            if g > 0:
                total += g
        return total

    v = violacao_total(p)
    if v <= 1e-9:
        return p, True

    for _ in range(max_steps):
        # Subgradiente = soma dos gradientes das restrições atualmente violadas
        grad = [0.0] * n
        for f, grads in zip(restricoes_funcs, restricoes_grad_funcs):
            try:
                if float(f(*p)) > 0:
                    for i in range(n):
                        grad[i] += float(grads[i](*p))
            except (ValueError, ZeroDivisionError, TypeError):
                pass

        norma = math.sqrt(sum(g * g for g in grad))
        if norma < 1e-12:
            break

        direcao = [-g / norma for g in grad]
        passo = 1.0
        avancou = False
        while passo > 1e-9:
            q = [p[i] + passo * direcao[i] for i in range(n)]
            nv = violacao_total(q)
            if nv < v - 1e-12:
                p, v = q, nv
                avancou = True
                break
            passo *= 0.5

        if not avancou or v <= 1e-9:
            break

    return p, v <= 1e-6

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
    restricoes_grad_funcs = [
        [sp.lambdify((x_sym, y_sym), sp.diff(r, x_sym), modules=['numpy', 'math']),
         sp.lambdify((x_sym, y_sym), sp.diff(r, y_sym), modules=['numpy', 'math'])]
        for r in restricoes_sympy
    ]

    curr_x, curr_y = x_inicial if x_inicial else [0.0, 0.0]
    curr_x, curr_y = float(curr_x), float(curr_y)

    # Se o ponto inicial estiver fora da região viável, projeta ele para dentro
    # antes de começar (senão o método pode "convergir" num ponto que viola g).
    viavel = True
    start_projetado = False
    if restricoes_funcs:
        ponto0 = [curr_x, curr_y]
        (curr_x, curr_y), viavel = _restaurar_viabilidade(ponto0, restricoes_funcs, restricoes_grad_funcs)
        start_projetado = (abs(curr_x - ponto0[0]) > 1e-9 or abs(curr_y - ponto0[1]) > 1e-9)

    diverged = False
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

        # Guarda anti-divergência: função ilimitada faz o ponto escapar para o
        # infinito, gerando valores (ex.: 1e280) que quebram a renderização.
        if (abs(curr_x) > DOMINIO_LIMITE or abs(curr_y) > DOMINIO_LIMITE
                or not math.isfinite(hist_z[-1])):
            diverged = True
            break

    return {
        "path": {"x": hist_x, "y": hist_y, "z": hist_z},
        "iterations": len(hist_x) - 1,
        "ponto_otimo": {"x": curr_x, "y": curr_y},
        "valor_otimo": hist_z[-1],
        "diverged": diverged,
        "viavel": viavel,
        "start_projetado": start_projetado
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
    restricoes_grad_funcs = [
        [sp.lambdify(variaveis_sympy, sp.diff(r, v), modules=['numpy', 'math']) for v in variaveis_sympy]
        for r in restricoes_sympy
    ]

    x_atual = [float(x) for x in x_inicial] if x_inicial else [0.0] * n_vars

    # Projeta um ponto inicial infactível de volta para a região viável.
    viavel = True
    start_projetado = False
    if restricoes_funcs:
        ponto0 = list(x_atual)
        x_atual, viavel = _restaurar_viabilidade(ponto0, restricoes_funcs, restricoes_grad_funcs)
        start_projetado = any(abs(a - b) > 1e-9 for a, b in zip(x_atual, ponto0))

    f_inicial = float(func(*x_atual))
    f_atual = f_inicial
    is_max = (objetivo.lower() == 'max')
    diverged = False

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
                # Guarda anti-divergência (função ilimitada)
                if not math.isfinite(f_atual) or any(abs(v) > DOMINIO_LIMITE for v in x_atual):
                    diverged = True
                    break
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
        "iteracoes_realizadas": passos_com_sucesso,
        "diverged": diverged,
        "viavel": viavel,
        "start_projetado": start_projetado
    }
