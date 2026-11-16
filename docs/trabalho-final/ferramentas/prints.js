// Captura os prints do estado inicial (Fase 0) com o Chrome do host em modo headless.
// Uso: node prints.js <pasta-de-saida> [alvo...]   alvos: superset superset-query airflow airflow-run docs cube
const { chromium } = require('/home/igor/.npm/_npx/9833c18b2d85bc59/node_modules/playwright-core');
const out = process.argv[2];
const targets = process.argv.slice(3);

(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();

  if (targets.some(t => t.startsWith('superset'))) {
    await page.goto('http://localhost:8088/login/');
    await page.waitForLoadState('networkidle');
    await page.fill('input[name="username"], #username', 'admin');
    await page.fill('input[name="password"], #password', 'secret');
    await page.click('button:has-text("Sign in")');
    await page.waitForURL(u => !u.toString().includes('/login'), { timeout: 30000 });
  }

  if (targets.includes('superset')) {
    // SUPERSET_DASHBOARD / SUPERSET_FILE escolhem o dashboard e o nome do arquivo
    // (padrão: o print da Fase 0)
    await page.goto(`http://localhost:8088/superset/dashboard/${process.env.SUPERSET_DASHBOARD || 1}/`);
    await page.waitForSelector('.chart-container, .dashboard-chart', { timeout: 60000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(8000);
    await page.screenshot({ path: `${out}/${process.env.SUPERSET_FILE || '0-06-superset-dashboard.png'}`, fullPage: true });
    console.log('superset ok');
  }

  if (targets.includes('superset-query')) {
    // Abre o menu ⋮ do gráfico SUPERSET_CHART no dashboard e clica em "View query":
    // o modal mostra o SQL que o Superset manda para a SQL API do Cube.
    await page.goto(`http://localhost:8088/superset/dashboard/${process.env.SUPERSET_DASHBOARD || 1}/`);
    await page.waitForSelector('.chart-container, .dashboard-chart', { timeout: 60000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    const chart = process.env.SUPERSET_CHART || 1;
    await page.locator(`#slice_${chart}-controls`).click();
    await page.locator('[role="menuitem"]:has-text("View query")').click();
    await page.waitForSelector('.ant-modal-content pre, .ant-modal-content code', { timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${out}/${process.env.SUPERSET_FILE || 'superset-view-query.png'}`, fullPage: false });
    console.log('superset-query ok');
  }

  if (targets.includes('airflow')) {
    await page.goto('http://localhost:8080/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await page.goto('http://localhost:8080/dags/extract_movies');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    const g = page.locator('button[aria-label*="raph" i], button[aria-label*="rafo" i], button:has-text("Graph"), button:has-text("Grafo")').first();
    if (await g.count()) { await g.click(); } else { await page.mouse.click(160, 82); }
    await page.waitForTimeout(6000);
    await page.screenshot({ path: `${out}/0-07-airflow-extract-movies.png`, fullPage: false });
    console.log('airflow ok');
  }

  if (targets.includes('airflow-run')) {
    // Uma execução da DAG (Airflow 3.1): grafo, Gantt e o log de uma tarefa.
    // AIRFLOW_DAG, AIRFLOW_RUN (run_id), AIRFLOW_TASK e AIRFLOW_PREFIX (prefixo dos arquivos).
    const dag = process.env.AIRFLOW_DAG || 'movies_daily';
    const run = encodeURIComponent(process.env.AIRFLOW_RUN);
    const task = process.env.AIRFLOW_TASK || 'dbt-build';
    const prefix = process.env.AIRFLOW_PREFIX || 'airflow';
    await page.goto('http://localhost:8080/');   // o login automático redireciona para a home
    await page.waitForLoadState('networkidle');
    const runUrl = `http://localhost:8080/dags/${dag}/runs/${run}`;

    await page.goto(runUrl);
    await page.waitForLoadState('networkidle');
    await page.locator('button[aria-label^="Mostrar Gráfico"]').click();
    await page.waitForTimeout(5000);
    await page.screenshot({ path: `${out}/${prefix}-grafo.png`, fullPage: false });
    console.log('airflow grafo ok');

    await page.goto(runUrl);
    await page.waitForLoadState('networkidle');
    await page.locator('button[aria-label^="Mostrar Grade"]').click();
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("Opções")').click();
    await page.locator('text=Mostrar Gantt').click();
    await page.keyboard.press('Escape');
    // recolhe o painel de detalhes da direita para o Gantt ocupar a largura toda
    await page.locator('button[aria-label="Recolher Painel de Detalhes"]').click().catch(() => {});
    await page.waitForTimeout(4000);
    await page.screenshot({ path: `${out}/${prefix}-gantt.png`, fullPage: false });
    console.log('airflow gantt ok');

    await page.goto(`${runUrl}/tasks/${task}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    // rola o log até o fim (o resumo do dbt, `Done. PASS=...`, fica nas últimas linhas)
    // (a lista é virtualizada: cada rolagem carrega mais linhas, então rola várias vezes)
    for (let i = 0; i < 8; i++) {
      await page.evaluate(() => document.querySelectorAll('*').forEach(el => {
        if (el.scrollHeight > el.clientHeight + 50 && getComputedStyle(el).overflowY !== 'visible') el.scrollTop = el.scrollHeight;
      }));
      await page.waitForTimeout(700);
    }
    await page.screenshot({ path: `${out}/${prefix}-log-${task}.png`, fullPage: false });
    console.log('airflow log ok');
  }

  if (targets.includes('docs')) {
    // DOCS_MODEL / DOCS_FILE escolhem a model e o nome do arquivo (padrão: o print da Fase 0)
    const model = process.env.DOCS_MODEL || 'fct_titles';
    await page.goto(`http://localhost:8082/#!/model/model.movies_transform.${model}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    // abre o grafo de linhagem completo (botão no canto inferior direito)
    const btn = page.locator('[data-toggle="tooltip"][title*="ineage"], .lineage-button, button:has-text("View Lineage Graph")').first();
    if (await btn.count()) { await btn.click(); } else { console.log('botão de linhagem não achado'); }
    await page.waitForTimeout(3000);
    await page.mouse.click(1549, 51); // expandir o grafo em tela cheia
    await page.waitForTimeout(4000);
    await page.screenshot({ path: `${out}/${process.env.DOCS_FILE || '0-08-dbt-docs-linhagem.png'}`, fullPage: false });
    console.log('docs ok');
  }

  if (targets.includes('cube')) {
    // CUBE_QUERY (JSON da REST API) e CUBE_FILE escolhem a consulta e o nome do arquivo.
    // O Playground lê a consulta do hash da URL; falta só clicar em "Run Query".
    const query = process.env.CUBE_QUERY || '{}';
    await page.goto(`http://localhost:4000/#/build?query=${encodeURIComponent(query)}`);
    await page.waitForLoadState('networkidle');
    await page.locator('button:has-text("Run Query")').first().click();
    await page.waitForSelector('text=No results available', { state: 'detached', timeout: 60000 });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${out}/${process.env.CUBE_FILE || 'cube-playground.png'}`, fullPage: true });
    console.log('cube ok');
  }

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
