from flask import Blueprint, request, jsonify
from app.services.math_engine import process_latex_function, rodar_direcoes_aleatorias, rodar_gradiente, gerar_grid, gerar_grid_restricoes

optimizer_bp = Blueprint('optimizer', __name__)

def pre_processamento(dados):
    """
    Função auxiliar interna para validar o payload e a linearidade 
    antes de rodar qualquer algoritmo de otimização.
    """
    latex_str = dados.get('funcao_latex')
    restricoes_latex = dados.get('restricoes_latex', []) # Nova lista de restrições g(x) <= 0
    objetivo = dados.get('objetivo') # Tem que ser 'max' ou 'min'

    if not latex_str:
        return {"valido": False, "codigo": 400, "resposta": {"error": "O campo 'funcao_latex' é obrigatório."}}
    
    if objetivo not in ['max', 'min']:
        return {"valido": False, "codigo": 400, "resposta": {"error": "O campo 'objetivo' deve ser 'max' ou 'min'."}}

    try:
        resultado_math = process_latex_function(latex_str, restricoes_latex)

        if resultado_math['is_linear']:
            # Remove os objetos SymPy puros (não serializáveis em JSON) dos detalhes
            detalhes_serializaveis = {
                chave: valor for chave, valor in resultado_math.items()
                if chave not in ('sympy_expr', 'sympy_vars', 'sympy_constraints')
            }
            return {
                "valido": False, 
                "codigo": 400, 
                "resposta": {
                    "error": "Modelo Linear detectado.",
                    "message": "Os métodos de otimização suportam exclusivamente funções não lineares.",
                    "detalhes": detalhes_serializaveis
                }
            }
            
        return {"valido": True, "dados_matematicos": resultado_math, "objetivo": objetivo}

    except ValueError as e:
        return {"valido": False, "codigo": 400, "resposta": {"error": str(e)}}
    except Exception as e:
        return {"valido": False, "codigo": 500, "resposta": {"error": "Erro interno no processamento matemático.", "details": str(e)}}


@optimizer_bp.route('/direcoes-aleatorias', methods=['POST'])
def otimizar_direcoes_aleatorias():
    dados = request.json
    validacao = pre_processamento(dados)

    if not validacao['valido']:
        return jsonify(validacao['resposta']), validacao['codigo']

    dados_math = validacao['dados_matematicos']
    objetivo = validacao['objetivo']

    parametros = dados.get('parametros', {})
    step_size = float(parametros.get('step_size', 0.1))
    max_iter = int(parametros.get('max_iter', 1000))
    x_inicial = parametros.get('x_inicial', None)

    try:
        # Extrai os objetos SymPy
        expressao_sympy = dados_math['sympy_expr']
        variaveis_sympy = dados_math['sympy_vars']
        restricoes_sympy = dados_math['sympy_constraints']

        # Executa o cálculo
        resultado_otimizacao = rodar_direcoes_aleatorias(
            expressao_sympy=expressao_sympy,
            variaveis_sympy=variaveis_sympy,
            objetivo=objetivo,
            restricoes_sympy=restricoes_sympy,
            x_inicial=x_inicial,
            step_size=step_size,
            max_iter=max_iter
        )

        grid = gerar_grid(expressao_sympy, variaveis_sympy)
        grid_restricoes = gerar_grid_restricoes(restricoes_sympy, variaveis_sympy)

        return jsonify({
            "success": True,
            "data": {
                "method": "Direções Aleatórias",
                "objetivo": objetivo.upper(),
                "result": resultado_otimizacao,
                "grid": grid,
                "constraints": grid_restricoes
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Falha interna ao executar o algoritmo de otimização.",
            "detalhes": str(e)
        }), 500


@optimizer_bp.route('/gradiente', methods=['POST'])
def otimizar_gradiente():
    """
    Endpoint: POST /api/optimizer/gradiente
    """
    dados = request.json
    validacao = pre_processamento(dados)

    if not validacao['valido']:
        return jsonify(validacao['resposta']), validacao['codigo']

    dados_math = validacao['dados_matematicos']
    objetivo = validacao['objetivo']

    parametros = dados.get('parametros', {})
    learning_rate = float(parametros.get('learning_rate', 0.1))
    max_iter = int(parametros.get('max_iter', 100))
    x_inicial = parametros.get('x_inicial', None)
    tolerancia = float(parametros.get('tolerancia', 1e-6))

    try:
        expressao_sympy = dados_math['sympy_expr']
        variaveis_sympy = dados_math['sympy_vars']
        restricoes_sympy = dados_math['sympy_constraints']

        # Executa o Gradiente
        resultado = rodar_gradiente(
            expressao_sympy=expressao_sympy,
            variaveis_sympy=variaveis_sympy,
            objetivo=objetivo,
            restricoes_sympy=restricoes_sympy,
            x_inicial=x_inicial,
            step_size=learning_rate,
            max_iter=max_iter,
            tolerance=tolerancia
        )

        # Gera o Grid para o gráfico
        grid = gerar_grid(expressao_sympy, variaveis_sympy)
        grid_restricoes = gerar_grid_restricoes(restricoes_sympy, variaveis_sympy)

        return jsonify({
            "success": True,
            "data": {
                "path": resultado['path'],
                "iterations": resultado['iterations'],
                "grid": grid,
                "constraints": grid_restricoes,
                "ponto_otimo": resultado['ponto_otimo'],
                "valor_otimo": resultado['valor_otimo'],
                "diverged": resultado.get('diverged', False),
                "viavel": resultado.get('viavel', True),
                "start_projetado": resultado.get('start_projetado', False)
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
