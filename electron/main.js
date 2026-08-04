// Clear problematic env variable BEFORE requiring electron
if (process.env.ELECTRON_RUN_AS_NODE) {
    delete process.env.ELECTRON_RUN_AS_NODE;
    console.log('[Electron] Cleared ELECTRON_RUN_AS_NODE before require');
}

const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');

let mainWindow;
let widgetWindow;
let pythonProcess;
let agentProcess;
let viteProcess;

function createWindow() {
    // Prevent multiple windows
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.focus();
        return;
    }
    
    mainWindow = new BrowserWindow({
        width: 1920,
        height: 1080,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            webviewTag: true,
            preload: path.join(__dirname, 'preload.js'),
            sandbox: false,
        },
        backgroundColor: '#04080B',
        transparent: false,
        frame: true,
        show: false,
    });

    const loadFrontend = () => {
        const http = require('http');
        const distPath = `file://${path.join(__dirname, '..', 'dist', 'index.html').replace(/\\/g, '/')}`;
        
        const findVitePort = () => {
            return new Promise((resolve) => {
                const check = (port) => {
                    if (port > 5183) {
                        resolve(null);
                        return;
                    }
                    http.get(`http://localhost:${port}`, (res) => {
                        if (res.statusCode === 200) {
                            console.log(`[SODA] Found Vite on port ${port}`);
                            resolve(port);
                        } else {
                            check(port + 1);
                        }
                    }).on('error', () => {
                        check(port + 1);
                    });
                };
                check(5173);
            });
        };
        
        findVitePort().then(port => {
            if (port) {
                // Dev mode — Vite is running, skip backend spawn
                console.log('[SODA] Dev mode: waiting for backend on :8000...');
                waitForBackend(45000).then(() => {
                    const url = `http://localhost:${port}`;
                    console.log(`[SODA] Loading frontend from ${url}`);
                    mainWindow.loadURL(url)
                        .then(() => {
                            console.log('[SODA] Frontend loaded successfully!');
                            mainWindow.show();
                        })
                        .catch((err) => {
                            console.error(`[SODA] Failed to load frontend: ${err.message}`);
                        });
                }).catch(() => {
                    console.error('[SODA] Backend not available, loading frontend anyway...');
                    const url = `http://localhost:${port}`;
                    mainWindow.loadURL(url).then(() => mainWindow.show());
                });
            } else {
                // Production mode — start backend then load dist
                console.log('[SODA] Production mode: starting backend...');
                startPythonBackend();
                waitForBackend(60000).then(() => {
                    console.log(`[SODA] Loading from dist: ${distPath}`);
                    mainWindow.loadURL(distPath)
                        .then(() => {
                            console.log('[SODA] Frontend loaded successfully from dist!');
                            mainWindow.show();
                        })
                        .catch((err) => {
                            console.error(`[SODA] Failed to load dist frontend: ${err.message}`);
                        });
                }).catch((err) => {
                    console.error(`[SODA] Backend failed to start: ${err.message}`);
                    const { dialog } = require('electron');
                    dialog.showErrorBox(
                        'SODA Backend Error',
                        `Failed to start the Python backend.\n\n${err.message}\n\nPlease check that Python 3.11 is installed and try again.`
                    );
                    app.quit();
                });
            }
        });
    };

    loadFrontend();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function getAppBaseUrl() {
    const http = require('http');
    const distPath = `file://${path.join(__dirname, '..', 'dist', 'index.html').replace(/\\/g, '/')}`;
    
    const findVitePort = () => {
        return new Promise((resolve) => {
            const check = (port) => {
                if (port > 5183) { resolve(null); return; }
                http.get(`http://localhost:${port}`, (res) => {
                    if (res.statusCode === 200) {
                        console.log(`[SODA] Found Vite on port ${port}`);
                        resolve(port);
                    } else { check(port + 1); }
                }).on('error', () => { check(port + 1); });
            };
            check(5173);
        });
    };
    
    return findVitePort().then(port => {
        if (port) return `http://localhost:${port}`;
        return distPath;
    });
}

function createWidgetWindow() {
    widgetWindow = new BrowserWindow({
        width: 140,
        height: 44,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        hasShadow: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });
    
    getAppBaseUrl().then(baseUrl => {
        const url = `${baseUrl}${baseUrl.startsWith('http') ? '/?widget=1' : '?widget=1'}`;
        console.log(`[SODA] Loading widget from ${url}`);
        widgetWindow.loadURL(url);
    });
    
    widgetWindow.on('closed', () => {
        widgetWindow = null;
    });
}

function startPythonBackend() {
    const scriptPath = path.join(__dirname, '../backend/server.py');
    console.log(`[SODA] Starting Python backend: ${scriptPath}`);

    pythonProcess = spawn('py', ['-3.11', scriptPath], {
        cwd: path.join(__dirname, '../backend'),
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error]: ${data}`);
    });
}

function startLocalAgent() {
    const agentPath = path.join(__dirname, '../backend/local_agent.py');
    console.log(`[SODA] Starting local agent: ${agentPath}`);

    try {
        agentProcess = spawn('py', ['-3.11', agentPath], {
            cwd: path.join(__dirname, '../backend'),
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        agentProcess.stdout.on('data', (data) => {
            console.log(`[Agent]: ${data}`);
        });

        agentProcess.stderr.on('data', (data) => {
            console.error(`[Agent Error]: ${data}`);
        });

        agentProcess.on('close', (code) => {
            console.log(`[SODA] Local agent exited with code ${code}`);
            agentProcess = null;
        });

        agentProcess.on('error', (err) => {
            console.error(`[SODA] Failed to start local agent: ${err.message}`);
            agentProcess = null;
        });

        console.log('[SODA] Local agent started');
    } catch (err) {
        console.error(`[SODA] Local agent start failed: ${err.message}`);
    }
}

app.whenReady().then(() => {
    // Grant camera & microphone permission
    session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
        if (permission === 'media' || permission === 'camera' || permission === 'microphone') {
            callback(true)
        } else {
            callback(false)
        }
    })

    // IPC handlers for window controls
    ipcMain.on('window-minimize', () => {
        if (mainWindow) mainWindow.minimize();
    });

    ipcMain.on('window-restore', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();
        }
    });

    ipcMain.on('window-maximize', () => {
        if (mainWindow) {
            if (mainWindow.isMaximized()) {
                mainWindow.unmaximize();
            } else {
                mainWindow.maximize();
            }
        }
    });

    ipcMain.on('window-close', () => {
        if (mainWindow) mainWindow.close();
    });

    // Handle window control from frontend
    ipcMain.on('window-control', (event, action) => {
        console.log('[Electron] Window control:', action);
        if (!mainWindow) {
            console.log('[Electron] No mainWindow!');
            return;
        }
        
        if (action === 'minimize') {
            console.log('[Electron] Calling minimize');
            mainWindow.minimize();
        } else if (action === 'maximize') {
            if (mainWindow.isMaximized()) {
                mainWindow.unmaximize();
            } else {
                mainWindow.maximize();
            }
        } else if (action === 'close') {
            // Kill agent + backend before closing
            if (agentProcess) {
                try { agentProcess.kill(); } catch (e) {}
            }
            if (pythonProcess) {
                pythonProcess.kill();
            }
            // Kill ports
            const killPort = (port) => {
                require('child_process').execSync(`powershell -Command "Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"`, { stdio: 'ignore' });
            }
            killPort(8000);
            for (let p = 5173; p <= 5183; p++) killPort(p);
            
            mainWindow.destroy();
            app.quit();
        } else if (action === 'background') {
            // Minimize main window + spawn widget window on top
            mainWindow.minimize();
            if (!widgetWindow || widgetWindow.isDestroyed()) {
                createWidgetWindow();
            }
        } else if (action === 'restore-from-background') {
            // Restore main window + close widget
            if (mainWindow) {
                if (mainWindow.isMinimized()) mainWindow.restore();
                mainWindow.show();
                mainWindow.focus();
            }
            if (widgetWindow && !widgetWindow.isDestroyed()) {
                widgetWindow.close();
                widgetWindow = null;
            }
        }
    });

    // IPC for widget window drag
    ipcMain.on('widget-drag', (event, { dx, dy }) => {
        if (widgetWindow && !widgetWindow.isDestroyed()) {
            const [x, y] = widgetWindow.getPosition();
            widgetWindow.setPosition(x + dx, y + dy);
        }
    });

    // Create window first — it detects dev vs production mode
    createWindow();

    // Auto-start local agent for desktop control (Spotify, apps, etc.)
    startLocalAgent();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

function checkBackendPort(port, retries = 5, delay = 1500) {
    return new Promise((resolve) => {
        const attempt = (remaining) => {
            const net = require('net');
            const server = net.createServer();
            server.once('error', (err) => {
                if (err.code === 'EADDRINUSE') {
                    resolve(true);
                } else if (remaining > 0) {
                    console.log(`[SODA] Port ${port} check failed, retrying (${remaining} left)...`);
                    setTimeout(() => attempt(remaining - 1), delay);
                } else {
                    resolve(false);
                }
            });
            server.once('listening', () => {
                server.close();
                resolve(false);
            });
            server.listen(port);
        };
        attempt(retries);
    });
}

function waitForBackend(timeoutMs = 30000) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const check = () => {
            const http = require('http');
            http.get('http://127.0.0.1:8000/status', (res) => {
                if (res.statusCode === 200) {
                    console.log('[SODA] Backend is ready!');
                    resolve();
                } else {
                    if (Date.now() - startTime > timeoutMs) {
                        reject(new Error('Backend startup timed out'));
                        return;
                    }
                    setTimeout(check, 1000);
                }
            }).on('error', () => {
                if (Date.now() - startTime > timeoutMs) {
                    reject(new Error('Backend startup timed out'));
                    return;
                }
                setTimeout(check, 1000);
            });
        };
        check();
    });
}

let windowWasShown = false;

app.on('window-all-closed', () => {
    console.log('[SODA] Window closed - quitting app');
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

function killPort(port) {
    try {
        const { execSync } = require('child_process');
        // Kill all processes on this port
        execSync(`powershell -Command "Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"`, { stdio: 'ignore' });
        console.log(`[SODA] Killed port ${port}`);
    } catch (e) {
        // Port already free
    }
}

app.on('will-quit', () => {
    console.log('[SODA] App closing... Cleaning up.');
    
    if (widgetWindow && !widgetWindow.isDestroyed()) {
        widgetWindow.close();
        widgetWindow = null;
    }
    
    // Kill local agent
    if (agentProcess) {
        try {
            agentProcess.kill();
        } catch (e) {}
    }
    
    // Kill Python backend
    if (pythonProcess) {
        try {
            pythonProcess.kill();
        } catch (e) {}
    }
    
    // Kill all development ports
    killPort(8000);  // Python backend
    for (let port = 5173; port <= 5183; port++) {
        killPort(port);  // Vite
    }
});