// src/services/api.js
import * as math from 'mathjs';

// No futuro, você vai apagar todo este código e substituir por um fetch real
// para a sua URL do Flask (ex: http://localhost:5000/api/optimize)
export const requestOptimization = async (payload) => {
    const { formula, learningRate } = payload;

    // 1. Simula o tempo de resposta da rede (delay de 500ms)
    await new Promise(resolve => setTimeout(resolve, 500));

    try {
        // Compila a função e as derivadas
        const node = math.parse(formula);
        const compiled = node.compile();
        const dxCompiled = math.derivative(node, 'x').compile();
        const dyCompiled = math.derivative(node, 'y').compile();

        // 2. O Backend calcula a malha topográfica (Grid 3D) para o frontend desenhar
        const range = 5;
        const step = 0.5;
        const gridX = [];
        const gridY = [];

        for (let i = -range; i <= range; i += step) gridX.push(i);
        for (let j = -range; j <= range; j += step) gridY.push(j);

        const gridZ = [];
        for (let xi = 0; xi < gridX.length; xi++) {
            const zRow = [];
            for (let yj = 0; yj < gridY.length; yj++) {
                zRow.push(compiled.evaluate({ x: gridX[xi], y: gridY[yj] }));
            }
            gridZ.push(zRow);
        }

        // 3. O Backend calcula a Descida do Gradiente
        let currentX = (Math.random() * 8) - 4;
        let currentY = (Math.random() * 8) - 4;

        const histX = [currentX];
        const histY = [currentY];
        const histZ = [compiled.evaluate({ x: currentX, y: currentY })];

        const tolerance = 0.01;
        const maxIter = 100;
        let iter = 0;

        while (iter < maxIter) {
            const gradX = dxCompiled.evaluate({ x: currentX, y: currentY });
            const gradY = dyCompiled.evaluate({ x: currentX, y: currentY });

            const gradNorm = Math.sqrt(gradX * gradX + gradY * gradY);
            if (gradNorm < tolerance) break;

            currentX = currentX - learningRate * gradX;
            currentY = currentY - learningRate * gradY;

            histX.push(currentX);
            histY.push(currentY);
            histZ.push(compiled.evaluate({ x: currentX, y: currentY }));

            iter++;
        }

        // 4. Retorna a resposta empacotada como se fosse um JSON do Flask
        return {
            success: true,
            data: {
                path: { x: histX, y: histY, z: histZ },
                iterations: iter,
                grid: { x: gridX, y: gridY, z: gridZ }
            }
        };

    } catch (error) {
        // Retorna erro se a fórmula estiver errada
        return {
            success: false,
            error: 'Falha na matriz matemática. Use variáveis x e y. Ex: x^2 + 2*y^2'
        };
    }
};