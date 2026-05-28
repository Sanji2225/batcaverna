import axios from 'axios';

// Configuração base do Axios
const api = axios.create({
    baseURL: 'http://localhost:5000', // URL padrão do Flask em desenvolvimento
    headers: {
        'Content-Type': 'application/json'
    }
});

/**
 * Envia uma fórmula para o backend realizar a otimização via Gradiente.
 * @param {Object} payload { formula, learningRate }
 */
export const requestOptimization = async (payload) => {
    const { formula, learningRate } = payload;

    try {
        const response = await api.post('/api/optimizer/gradiente', {
            funcao_latex: formula,
            objetivo: 'min', // Por padrão buscando o mínimo
            parametros: {
                step_size: learningRate,
                max_iter: 100
            }
        });

        // O backend já retorna no formato esperado pelo componente Graph (path, iterations, grid)
        return {
            success: true,
            data: response.data.data
        };

    } catch (error) {
        console.error('Erro na requisição API:', error);
        
        // Trata erro de validação (ex: modelo linear) ou erro de servidor
        const errorMessage = error.response?.data?.error || 
                             error.response?.data?.message || 
                             'Erro de conexão com o servidor. Verifique se o backend está rodando.';
        
        return {
            success: false,
            error: errorMessage
        };
    }
};

export default api;
