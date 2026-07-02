// src/App.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import Plot from 'react-plotly.js';
import 'mathlive';
import { requestOptimization } from './services/api';

const App = () => {
  // Estados da Aplicação
  const [path, setPath] = useState({ x: [], y: [], z: [] });
  const [grid, setGrid] = useState({ x: [], y: [], z: [] });
  const [constraints, setConstraints] = useState([]);
  const [iterations, setIterations] = useState(0);
  const [learningRate, setLearningRate] = useState(0.5);
  const [stepSize, setStepSize] = useState(0.5);
  const [maxIter, setMaxIter] = useState(200);
  const [x0, setX0] = useState('3, 3');

  const [formula, setFormula] = useState('x^2 + 2y^2');
  const [constraint, setConstraint] = useState('');
  const [method, setMethod] = useState('gradiente');
  const [objective, setObjective] = useState('min');

  // Estados da Interface
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [notice, setNotice] = useState('');

  const mathFieldRef = useRef(null);
  const constraintFieldRef = useRef(null);

  // Escuta as mudanças no campo de fórmula
  useEffect(() => {
    const mf = mathFieldRef.current;
    if (mf) {
      mf.setValue(formula, { silenceInternalErrors: true });
      let timeoutId;
      const handleInput = () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          setFormula(mf.getValue('latex'));
        }, 800); // 800ms de debounce
      };
      mf.addEventListener('input', handleInput);
      return () => {
        mf.removeEventListener('input', handleInput);
        clearTimeout(timeoutId);
      };
    }
  }, []);

  // Escuta as mudanças no campo de restrição
  useEffect(() => {
    const cf = constraintFieldRef.current;
    if (cf) {
      cf.setValue(constraint, { silenceInternalErrors: true });
      let timeoutId;
      const handleInput = () => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          setConstraint(cf.getValue('latex'));
        }, 800);
      };
      cf.addEventListener('input', handleInput);
      return () => {
        cf.removeEventListener('input', handleInput);
        clearTimeout(timeoutId);
      };
    }
  }, []);

  // Função que se comunica com o Backend
  const triggerScan = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg('');
    setNotice('');

    const startPoint = x0.split(',').map(v => parseFloat(v.trim()));
    if (startPoint.some(isNaN)) {
      setErrorMsg('Ponto inicial inválido. Use o formato: x, y');
      setIsLoading(false);
      return;
    }

    const payload = {
      method,
      formula,
      objective,
      constraints: constraint ? [constraint] : [],
      params: {
        learning_rate: learningRate,
        step_size: stepSize,
        max_iter: maxIter,
        x_inicial: startPoint
      }
    };

    const response = await requestOptimization(payload);

    if (response.success) {
      const data = response.data;
      let flags = {};
      if (method === 'gradiente') {
        setPath(data.path);
        setIterations(data.iterations);
        flags = data;
      } else {
        // Para Direções Aleatórias, usamos o valor real de z inicial retornado pelo backend
        const pt = data.result.ponto_otimo;
        setPath({
          x: [startPoint[0], pt.x],
          y: [startPoint[1], pt.y],
          z: [data.result.valor_inicial, data.result.valor_otimo]
        });
        setIterations(data.result.iteracoes_realizadas);
        flags = data.result;
      }
      setGrid(data.grid);
      setConstraints(data.constraints || []);

      // Avisos (não são erros): divergência, projeção de ponto e inviabilidade
      const avisos = [];
      if (flags.diverged) avisos.push('Função ilimitada nessa direção — não há ótimo finito, o método divergiu (trajetória truncada).');
      if (flags.start_projetado) avisos.push('Ponto inicial fora da região viável: foi projetado para dentro da restrição antes de otimizar.');
      if (flags.viavel === false) avisos.push('Não foi possível encontrar um ponto viável para as restrições informadas.');
      setNotice(avisos.join(' '));
    } else {
      setErrorMsg(response.error);
    }

    setIsLoading(false);
  }, [formula, constraint, method, objective, learningRate, stepSize, maxIter, x0]);

  useEffect(() => {
    triggerScan();
  }, [triggerScan]);

  const iterArray = path.z ? path.z.map((_, i) => i) : [];

  // Paleta de cores da Batcaverna
  const batColors = {
    bgFull: '#050505', bgPanel: '#111111', text: '#E0E0E0',
    yellow: '#FCE205', grid: '#333333', border: '#2A2A2A', error: '#FF4444'
  };

  const constraintColor = '#FF3B3B'; // Vermelho para a zona proibida (g > 0)

  // Superfície 3D: destaca em vermelho a parte da objetiva sobre a região inviável.
  // Um ponto é inviável se ALGUMA restrição tem g(x,y) > 0 ali.
  const buildInfeasibleSurface = () => {
    if (!grid.z || !grid.z.length || !constraints.length) return null;
    const z = grid.z.map((row, i) =>
      row.map((val, j) => {
        const inviavel = constraints.some(c => {
          const g = c.z?.[i]?.[j];
          return g != null && g > 0;
        });
        return inviavel ? val : null;
      })
    );
    return { x: grid.x, y: grid.y, z };
  };

  const infeasibleSurface = buildInfeasibleSurface();

  // Interpolação bilinear do valor da objetiva num ponto (px,py) qualquer do grid.
  const bilinear = (gz, xs, ys, px, py) => {
    const nx = xs.length, ny = ys.length;
    if (nx < 2 || ny < 2) return null;
    const stepx = (xs[nx - 1] - xs[0]) / (nx - 1);
    const stepy = (ys[ny - 1] - ys[0]) / (ny - 1);
    const j0 = Math.max(0, Math.min(nx - 2, Math.floor((px - xs[0]) / stepx)));
    const i0 = Math.max(0, Math.min(ny - 2, Math.floor((py - ys[0]) / stepy)));
    const tj = (px - xs[j0]) / stepx, ti = (py - ys[i0]) / stepy;
    const z00 = gz[i0]?.[j0], z10 = gz[i0]?.[j0 + 1], z01 = gz[i0 + 1]?.[j0], z11 = gz[i0 + 1]?.[j0 + 1];
    if ([z00, z10, z01, z11].some(v => v == null)) return null;
    return z00 * (1 - tj) * (1 - ti) + z10 * tj * (1 - ti) + z01 * (1 - tj) * ti + z11 * tj * ti;
  };

  // Fronteira g = 0 como CURVA suave sobre a superfície (marching squares + z bilinear).
  // Dá um anel contínuo em vez da borda "em escada" do overlay mascarado.
  const buildConstraintRings3D = () => {
    if (!grid.z || !grid.z.length || !constraints.length) return null;
    const xs = grid.x, ys = grid.y;
    const xr = [], yr = [], zr = [];
    constraints.forEach(c => {
      const z = c.z; if (!z) return;
      for (let i = 0; i < ys.length - 1; i++) {
        for (let j = 0; j < xs.length - 1; j++) {
          const corners = [
            { v: z[i]?.[j],         x: xs[j],     y: ys[i] },
            { v: z[i]?.[j + 1],     x: xs[j + 1], y: ys[i] },
            { v: z[i + 1]?.[j + 1], x: xs[j + 1], y: ys[i + 1] },
            { v: z[i + 1]?.[j],     x: xs[j],     y: ys[i + 1] },
          ];
          if (corners.some(k => k.v == null)) continue;
          const pts = [];
          for (let e = 0; e < 4; e++) {
            const a = corners[e], b = corners[(e + 1) % 4];
            if ((a.v < 0 && b.v >= 0) || (a.v >= 0 && b.v < 0)) {
              const t = (0 - a.v) / (b.v - a.v);
              pts.push({ x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) });
            }
          }
          for (let p = 0; p + 1 < pts.length; p += 2) {
            [pts[p], pts[p + 1]].forEach(pt => {
              const zz = bilinear(grid.z, xs, ys, pt.x, pt.y);
              xr.push(pt.x); yr.push(pt.y); zr.push(zz == null ? null : zz);
            });
            xr.push(null); yr.push(null); zr.push(null); // quebra entre segmentos
          }
        }
      }
    });
    return xr.length ? { x: xr, y: yr, z: zr } : null;
  };
  const constraintRing = buildConstraintRings3D();

  // Zona proibida (g > 0) como CONTORNO PREENCHIDO. Diferente do heatmap (que
  // pinta célula por célula e sai quadriculado), o contorno interpola a fronteira
  // (marching squares) => borda suave/redonda.
  // 'operation: <=' declara a região VIÁVEL (g <= 0); o Plotly preenche o
  // COMPLEMENTO (g > 0 = proibido), que é exatamente o mesmo critério do overlay 3D.
  const constraintTraces = constraints.map((c) => ({
    z: c.z, x: c.x, y: c.y,
    type: 'contour',
    contours: { type: 'constraint', operation: '<=', value: 0 },
    fillcolor: 'rgba(255,59,59,0.30)',
    line: { color: constraintColor, width: 2.5 },
    showscale: false, showlegend: false, hoverinfo: 'skip'
  }));

  // Item de legenda dedicado para a zona proibida (contorno não gera um bom swatch)
  const forbiddenLegendProxy = constraints.length ? {
    x: [null], y: [null], type: 'scatter', mode: 'markers',
    marker: { color: 'rgba(255,59,59,0.65)', size: 12, symbol: 'square' },
    name: 'Zona proibida (g > 0)', hoverinfo: 'skip'
  } : null;

  const darkLayoutBase = {
    paper_bgcolor: '#FFFFFF', plot_bgcolor: '#FFFFFF',
    font: { color: '#000000', family: '"Courier New", Courier, monospace' },
    margin: { t: 50, b: 50, l: 50, r: 50 }
  };

  const batColorScale = [[0, '#000000'], [0.5, '#222222'], [1, '#555555']];

  // Trava os eixos ao domínio do grid. Assim, se a trajetória divergir (max
  // ilimitado), a superfície e as restrições continuam visíveis em vez de
  // colapsarem num ponto por causa da escala astronômica do path.
  const axisRange = (vals) => (vals && vals.length ? [vals[0], vals[vals.length - 1]] : undefined);
  const xRange = axisRange(grid.x);
  const yRange = axisRange(grid.y);
  let zMin = Infinity, zMax = -Infinity;
  (grid.z || []).forEach(row => (row || []).forEach(v => {
    if (v != null && Number.isFinite(v)) { if (v < zMin) zMin = v; if (v > zMax) zMax = v; }
  }));
  const zRange = Number.isFinite(zMin) && Number.isFinite(zMax) ? [zMin, zMax] : undefined;

  // Recorta a trajetória ao domínio visível. No 3D o Plotly NÃO recorta scatter
  // pelo range dos eixos: se a busca diverge (max ilimitado), pontos em ~1e12
  // forçam a cena a encolher a superfície a um ponto. Pontos fora viram null.
  const px = path.x || [], py = path.y || [], pz = path.z || [];
  const inRange = (v, r) => !r || (v >= r[0] && v <= r[1]);
  const mask2D = px.map((_, i) => inRange(px[i], xRange) && inRange(py[i], yRange));
  const mask3D = px.map((_, i) => mask2D[i] && inRange(pz[i], zRange));
  const clip = (arr, mask) => arr.map((v, i) => (mask[i] ? v : null));
  const path2D = { x: clip(px, mask2D), y: clip(py, mask2D) };
  const path3D = { x: clip(px, mask3D), y: clip(py, mask3D), z: clip(pz, mask3D) };
  const lastIdx = px.length - 1;
  const otimo2Dvisivel = lastIdx >= 0 && mask2D[lastIdx];
  const otimo3Dvisivel = lastIdx >= 0 && mask3D[lastIdx];

  return (
    <div style={{ padding: '30px', fontFamily: '"Courier New", Courier, monospace', backgroundColor: batColors.bgFull, color: batColors.text, minHeight: '100vh' }}>
      <h1 style={{ textTransform: 'uppercase', letterSpacing: '2px', borderBottom: `2px solid ${batColors.yellow}`, paddingBottom: '10px', display: 'inline-block' }}>
        Batcomputador: Sistema de Otimização Restrita
      </h1>

      <div style={{ marginBottom: '30px', marginTop: '20px', padding: '20px', background: batColors.bgPanel, border: `1px solid ${batColors.border}`, borderRadius: '4px', boxShadow: `0 0 15px rgba(0,0,0,0.8)` }}>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '10px', color: batColors.yellow }}>
              Função Objetivo f(x,y):
            </label>
            <math-field ref={mathFieldRef} style={mathFieldStyle}></math-field>
          </div>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '10px', color: batColors.yellow }}>
              Zona de Restrição g(x,y) ≤ 0:
            </label>
            <math-field ref={constraintFieldRef} style={mathFieldStyle}></math-field>
            <small style={{ color: '#888' }}>Deixe vazio para sem restrição</small>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', alignItems: 'flex-end', marginBottom: '20px' }}>
          <label style={controlLabelStyle}>
            Método:
            <select value={method} onChange={(e) => setMethod(e.target.value)} style={selectStyle}>
              <option value="gradiente">Gradiente</option>
              <option value="direcoes-aleatorias">Direções Aleatórias</option>
            </select>
          </label>

          <label style={controlLabelStyle}>
            Objetivo:
            <select value={objective} onChange={(e) => setObjective(e.target.value)} style={selectStyle}>
              <option value="min">Minimizar</option>
              <option value="max">Maximizar</option>
            </select>
          </label>

          {method === 'direcoes-aleatorias' ? (
            <label style={controlLabelStyle}>
              Passo Inicial (α):
              <input type="number" step="0.01" value={stepSize} onChange={(e) => {
                setStepSize(e.target.value);
                setLearningRate(e.target.value);
              }} style={inputStyle} />
            </label>
          ) : (
            <div style={{ ...controlLabelStyle, maxWidth: '200px' }}>
              Passo (α):
              <span style={{ marginTop: '5px', padding: '8px', border: `1px dashed ${batColors.grid}`, color: '#888', fontSize: '12px', lineHeight: 1.4 }}>
                Automático (regra de Armijo + Barzilai-Borwein)
              </span>
            </div>
          )}

          <label style={controlLabelStyle}>
            Máx Iterações:
            <input type="number" value={maxIter} onChange={(e) => setMaxIter(e.target.value)} style={inputStyle} />
          </label>

          <label style={controlLabelStyle}>
            Ponto Inicial (x, y):
            <input type="text" value={x0} onChange={(e) => setX0(e.target.value)} style={inputStyle} />
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button onClick={triggerScan} disabled={isLoading} style={btnStyle}>
            {isLoading ? 'PROCESSANDO...' : 'INICIAR VARREDURA'}
          </button>
          {errorMsg && <p style={{ color: batColors.error, fontWeight: 'bold', margin: 0 }}>[ERRO]: {errorMsg}</p>}
        </div>

        <p style={{ marginTop: '20px', opacity: 0.8 }}>
          <strong>Telemetria:</strong> {isLoading ? 'Calculando trajetória...' : `Convergência em ${iterations} iterações.`}
          {!isLoading && path.x.length > 0 && (
            otimo2Dvisivel ? (
              <span style={{ marginLeft: '20px', color: batColors.yellow }}>
                Ótimo em: <strong>({px[lastIdx].toFixed(4)}, {py[lastIdx].toFixed(4)})</strong>
                | Valor: <strong>{pz[lastIdx].toFixed(6)}</strong>
              </span>
            ) : (
              <span style={{ marginLeft: '20px', color: batColors.error }}>
                Divergiu — sem ótimo finito nessa direção.
              </span>
            )
          )}
        </p>

        {notice && (
          <p style={{ marginTop: '10px', padding: '10px', border: `1px solid ${batColors.yellow}`, color: batColors.yellow, background: 'rgba(252,226,5,0.05)', margin: '10px 0 0' }}>
            [AVISO]: {notice}
          </p>
        )}
      </div>

      {!errorMsg && grid.z && grid.z.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '30px', opacity: isLoading ? 0.5 : 1, transition: 'opacity 0.3s' }}>
          <Plot
            useResizeHandler={true}
            style={{ flex: '1 1 45%', minWidth: '400px', height: '550px' }}
            data={[
              { z: grid.z, x: grid.x, y: grid.y, type: 'surface', opacity: 0.9, colorscale: batColorScale, showscale: false, name: 'Objetivo' },
              ...(infeasibleSurface ? [{
                z: infeasibleSurface.z, x: infeasibleSurface.x, y: infeasibleSurface.y,
                type: 'surface', showscale: false, opacity: 0.55,
                colorscale: [[0, constraintColor], [1, constraintColor]],
                name: 'Região Inviável', hoverinfo: 'name'
              }] : []),
              ...(constraintRing ? [{
                x: constraintRing.x, y: constraintRing.y, z: constraintRing.z,
                type: 'scatter3d', mode: 'lines',
                line: { color: constraintColor, width: 6 },
                name: 'Fronteira g = 0', hoverinfo: 'name'
              }] : []),
              { x: path3D.x, y: path3D.y, z: path3D.z, type: 'scatter3d', mode: 'lines+markers', connectgaps: false, marker: { color: batColors.yellow, size: 4 }, line: { color: batColors.yellow, width: 4 }, name: 'Trajetória' },
              ...(otimo3Dvisivel ? [{ x: [px[lastIdx]], y: [py[lastIdx]], z: [pz[lastIdx]], type: 'scatter3d', mode: 'markers', marker: { color: '#FF0000', size: 8, symbol: 'diamond' }, name: 'Ponto Ótimo' }] : [])
            ]}
            layout={{
              ...darkLayoutBase, autosize: true, title: 'Visualização Topográfica 3D', showlegend: true, legend: { x: 0, y: 1 },
              margin: { t: 40, b: 0, l: 0, r: 0 },
              scene: {
                xaxis: { range: xRange }, yaxis: { range: yRange }, zaxis: { range: zRange },
                aspectmode: 'cube',
                camera: { eye: { x: 1.5, y: 1.5, z: 1.1 } }
              }
            }}
          />

          <Plot
            useResizeHandler={true}
            style={{ flex: '1 1 45%', minWidth: '400px', height: '550px' }}
            data={[
              ...constraintTraces,
              {
                z: grid.z, x: grid.x, y: grid.y, type: 'contour',
                colorscale: [[0, '#1d3b53'], [0.5, '#3d7ea6'], [1, '#a9d6e5']],
                contours: { coloring: 'lines', showlabels: true, labelfont: { size: 10, color: '#a9d6e5', family: 'monospace' } },
                line: { width: 1.4 }, ncontours: 18,
                showscale: false, name: 'Curvas de Nível', hoverinfo: 'skip'
              },
              ...(forbiddenLegendProxy ? [forbiddenLegendProxy] : []),
              { x: path2D.x, y: path2D.y, type: 'scatter', mode: 'lines+markers', connectgaps: false, marker: { color: batColors.yellow, size: 6 }, line: { color: batColors.yellow, width: 2 }, name: 'Deslocamento' },
              ...(otimo2Dvisivel ? [{ x: [px[lastIdx]], y: [py[lastIdx]], type: 'scatter', mode: 'markers', marker: { color: '#FF0000', size: 12, symbol: 'x' }, name: 'Ponto Ótimo' }] : [])
            ]}
            layout={{
              ...darkLayoutBase, autosize: true, title: 'Mapa de Isolinhas 2D', showlegend: true, legend: { x: 0, y: 1 },
              xaxis: { range: xRange }, yaxis: { range: yRange }
            }}
          />

          <Plot
            useResizeHandler={true}
            style={{ width: '100%', height: '400px' }}
            data={[
              { x: iterArray, y: path.z, type: 'scatter', mode: 'lines+markers', marker: { color: batColors.yellow, size: 5 }, line: { color: batColors.yellow, width: 2 } },
            ]}
            layout={{
              ...darkLayoutBase, autosize: true, title: 'Telemetria de Convergência (f(x,y) por Iteração)',
              xaxis: { title: 'Iterações', gridcolor: batColors.grid, zerolinecolor: batColors.grid },
              yaxis: { title: 'Valor do Alvo', gridcolor: batColors.grid, zerolinecolor: batColors.grid }
            }}
          />
        </div>
      )}
    </div>
  );
};

const mathFieldStyle = {
  fontSize: '20px', padding: '10px', backgroundColor: '#000',
  color: '#FCE205', border: '1px solid #FCE205',
  borderRadius: '4px', outline: 'none', width: '100%'
};

const controlLabelStyle = { display: 'inline-flex', flexDirection: 'column', fontWeight: 'bold', fontSize: '14px' };

const selectStyle = {
  marginTop: '5px', padding: '8px', background: '#000',
  color: '#FCE205', border: '1px solid #333', outline: 'none',
  fontFamily: 'inherit'
};

const inputStyle = {
  marginTop: '5px', padding: '8px', background: '#000',
  color: '#FCE205', border: '1px solid #333', outline: 'none',
  width: '100px', fontFamily: 'inherit'
};

const btnStyle = {
  padding: '12px 30px', cursor: 'pointer',
  background: '#FCE205', color: '#000', fontWeight: 'bold',
  border: 'none', borderRadius: '2px', textTransform: 'uppercase'
};

export default App;
