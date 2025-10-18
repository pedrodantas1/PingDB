const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const yargs = require('yargs-parser');
const isRunning = require('is-running');
const sql = require('mssql');

// --- ARQUIVOS DE CONTROLE ---
// Usamos __dirname, que dentro do 'pkg' aponta para um local temporário.
// Para garantir que os arquivos fiquem ao lado do .exe, usamos process.cwd().
const basePath = process.pkg ? path.dirname(process.execPath) : __dirname;
const lockFilePath = path.join(basePath, '.pingdb.lock');
const logFilePath = path.join(basePath, 'ping-service.log');

// --- CONFIGURAÇÕES DO BANCO ---
const config = {
    server: 'localhost',
    port: 1433,
    database: 'Etrade',
    user: 'meuUsuarioNode',
    password: 'SenhaForte123!',
    options: { trustedConnection: true, enableArithAbort: true, encrypt: false },
    pool: { max: 10, min: 1, idleTimeoutMillis: 30000 },
    connectionTimeout: 15000,
    requestTimeout: 15000
};
const PING_INTERVALO_SEGUNDOS = 10;

// --- FUNÇÕES DE LOG ---
const log = (message) => {
    const timestamp = new Date().toLocaleString('pt-BR');
    fs.appendFileSync(logFilePath, `[${timestamp}] ${message}\n`);
};

// --- LÓGICA DO SERVIÇO DE PING (BACKGROUND) ---
async function runPingLoop() {
    log('Serviço de background iniciado.');
    let pool;

    const conectar = async () => {
        try {
            if (!pool || !pool.connected) {
                pool = await sql.connect(config);
                log('Conexão com o banco estabelecida.');
            }
        } catch (err) {
            log(`ERRO de conexão: ${err.message.split('\n')[0]}`);
            pool = null; // Força a tentativa de reconexão
        }
    };
    
    const ping = async () => {
        if (!pool) {
            await conectar();
            // Se a conexão falhar, tenta novamente no próximo ciclo
            if (!pool) return;
        }
        try {
            const start = Date.now();
            await pool.request().query('SELECT 1');
            const tempo = Date.now() - start;
            log(`Ping realizado com sucesso (${tempo} ms).`);
        } catch (err) {
            log(`ERRO no ping: ${err.message.split('\n')[0]}`);
            pool = null; // Força a reconexão
        }
    };
    
    await conectar(); // Tenta conectar na inicialização
    setInterval(ping, PING_INTERVALO_SEGUNDOS * 1000);
}


// --- FUNÇÕES DE CONTROLE (START, STOP, STATUS) ---

function getRunningPid() {
    if (!fs.existsSync(lockFilePath)) return null;
    const pid = parseInt(fs.readFileSync(lockFilePath, 'utf8'), 10);
    if (isRunning(pid)) {
        return pid;
    }
    // Arquivo de lock antigo, remove
    fs.unlinkSync(lockFilePath);
    return null;
}

function startService() {
    if (getRunningPid()) {
        console.log('Serviço já está em execução.');
        return;
    }

    // Inicia um novo processo em background, detached (independente)
    const child = spawn(process.execPath, [__filename, '--background'], {
        detached: true,
        stdio: 'ignore',
        windowsHide: true
    });
    child.unref(); // Permite que o processo pai (este) termine
    
    fs.writeFileSync(lockFilePath, child.pid.toString());
    console.log(`Serviço iniciado com PID ${child.pid}.`);
}

function stopService() {
    const pid = getRunningPid();
    if (!pid) {
        console.log('Serviço não estava em execução.');
        return;
    }
    try {
        process.kill(pid);
        fs.unlinkSync(lockFilePath);
        console.log(`Serviço com PID ${pid} foi parado.`);
        log('Serviço parado pelo usuário.');
    } catch (err) {
        console.error(`Falha ao parar o serviço: ${err.message}`);
    }
}

// --- PONTO DE ENTRADA DO SCRIPT ---
function main() {
    const args = yargs(process.argv.slice(2));

    if (args.background) {
        runPingLoop();
        return;
    }

    if (args._.includes('start')) {
        startService();
    } else if (args._.includes('stop')) {
        stopService();
    } else if (args._.includes('status')) {
        // Retorna um código de saída para o HTA poder ler
        process.exit(getRunningPid() ? 0 : 1);
    }
}

main();
