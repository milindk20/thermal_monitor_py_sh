import re
import os
import glob
import json
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = load_config()

app = Flask(__name__)

LOG_DIR = config.get("log_dir", "./logs")
LOG_PATTERN = config.get("log_prefix", "log_thermals.log") + "*"

def get_log_files():
    files = sorted(glob.glob(os.path.join(LOG_DIR, LOG_PATTERN)))
    return [os.path.basename(f) for f in files]

def parse_log_file(filepath):
    data = {"timestamps": [], "cpu_core0": [], "cpu_core2": []}
    
    if not os.path.exists(filepath):
        return data
    
    with open(filepath, "r") as f:
        content = f.read()
    
    cpu_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \|CPU\|.*?Core 0:\s*\+(\d+\.?\d*)°C.*?Core 2:\s*\+(\d+\.?\d*)°C"
    
    for match in re.finditer(cpu_pattern, content):
        timestamp_str = match.group(1)
        core0 = float(match.group(2))
        core2 = float(match.group(3))
        
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            data["timestamps"].append(timestamp_str)
            data["cpu_core0"].append(core0)
            data["cpu_core2"].append(core2)
        except:
            continue
    
    return data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Thermal Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); 
            color: #eee;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            padding: 15px 25px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .header h1 {
            color: #00d9ff;
            font-size: 1.5rem;
            font-weight: 600;
            text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header h1::before {
            content: "🌡️";
        }
        
        .controls {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.1);
            padding: 6px 12px;
            border-radius: 8px;
        }
        
        .control-group label {
            color: #aaa;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        select, button {
            padding: 8px 14px;
            font-size: 0.85rem;
            cursor: pointer;
            background: #00d9ff;
            border: none;
            border-radius: 6px;
            color: #1a1a2e;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        select:hover, button:hover {
            background: #00b8d9;
            transform: translateY(-1px);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button.active {
            background: #ff6b6b;
            color: white;
        }
        
        button.secondary {
            background: rgba(255,255,255,0.15);
            color: #eee;
        }
        
        button.secondary:hover {
            background: rgba(255,255,255,0.25);
        }
        
        select {
            background: rgba(255,255,255,0.9);
            min-width: 120px;
        }
        
        .stats-bar {
            display: flex;
            gap: 15px;
            padding: 15px 25px;
            background: rgba(0,0,0,0.2);
            flex-wrap: wrap;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 12px 20px;
            min-width: 120px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .stat-card h3 {
            font-size: 0.75rem;
            color: #888;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .stat-card .value {
            font-size: 1.4rem;
            font-weight: 700;
        }
        
        .stat-card .value.hot { color: #ff6b6b; }
        .stat-card .value.warm { color: #ffd93d; }
        .stat-card .value.cool { color: #6bcb77; }
        .stat-card .value.normal { color: #4ecdc4; }
        
        .chart-wrapper {
            flex: 1;
            padding: 20px 25px;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        
        .chart-container {
            flex: 1;
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            min-height: 400px;
        }
        
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(0,217,255,0.3);
            border-top-color: #00d9ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .zoom-controls {
            position: absolute;
            top: 15px;
            right: 15px;
            display: flex;
            gap: 8px;
            z-index: 10;
        }
        
        .zoom-controls button {
            padding: 8px 12px;
            font-size: 1rem;
            background: rgba(255,255,255,0.15);
            color: #eee;
        }
        
        .zoom-controls button:hover {
            background: rgba(255,255,255,0.25);
        }
        
        .status-bar {
            padding: 10px 25px;
            background: rgba(0,0,0,0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            color: #888;
        }
        
        .keyboard-hint {
            opacity: 0.7;
        }
        
        .keyboard-hint kbd {
            background: rgba(255,255,255,0.1);
            padding: 2px 6px;
            border-radius: 4px;
            margin: 0 2px;
        }
        
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.3);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(0,217,255,0.4);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(0,217,255,0.6);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>CPU Thermal Monitor</h1>
        <div class="controls">
            <div class="control-group">
                <label>File:</label>
                <select id="fileSelect" onchange="changeFile()">
                    {% for file in files %}
                    <option value="{{ file }}">{{ file.replace('log_thermals.log', '') }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="control-group">
                <label>View:</label>
                <select id="pointsSelect" onchange="updateView()">
                    <option value="50">50 pts</option>
                    <option value="100">100 pts</option>
                    <option value="200">200 pts</option>
                    <option value="500">500 pts</option>
                    <option value="1000" selected>1000 pts</option>
                    <option value="2000">2000 pts</option>
                    <option value="5000">5000 pts</option>
                    <option value="all">All</option>
                </select>
            </div>
            <button id="toggleBtn" onclick="toggleRealtime()">Live</button>
            <button class="secondary" onclick="resetZoom()">Reset</button>
        </div>
    </div>
    
    <div class="stats-bar">
        <div class="stat-card">
            <h3>Current Core 0</h3>
            <div class="value hot" id="current0">--°C</div>
        </div>
        <div class="stat-card">
            <h3>Current Core 2</h3>
            <div class="value hot" id="current2">--°C</div>
        </div>
        <div class="stat-card">
            <h3>Max (All Time)</h3>
            <div class="value warm" id="maxTemp">--°C</div>
        </div>
        <div class="stat-card">
            <h3>Min (All Time)</h3>
            <div class="value cool" id="minTemp">--°C</div>
        </div>
        <div class="stat-card">
            <h3>Average</h3>
            <div class="value normal" id="avgTemp">--°C</div>
        </div>
    </div>
    
    <div class="chart-wrapper">
        <div class="chart-container">
            <div class="zoom-controls">
                <button onclick="chartZoom(0)" title="Zoom Out (see more)">+</button>
                <button onclick="chartZoom(1)" title="Zoom In (see less)">-</button>
                <button onclick="chartPan('left')" title="See older data">◀</button>
                <button onclick="chartPan('right')" title="See newer data">▶</button>
            </div>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <span>Loading data...</span>
            </div>
            <canvas id="thermalChart"></canvas>
        </div>
    </div>
    
    <div class="status-bar">
        <span id="dataInfo">Loading...</span>
        <span class="keyboard-hint">
            <kbd>Scroll</kbd> to zoom • <kbd>Drag</kbd> to pan • <kbd>R</kbd> to reset
        </span>
    </div>
    
    <script>
        let chart;
        let realtimeEnabled = false;
        let updateInterval;
        let currentFile;
        let allData = { timestamps: [], cpu_core0: [], cpu_core2: [] };
        
        const ctx = document.getElementById('thermalChart').getContext('2d');
        
        async function loadData(file) {
            const response = await fetch('/api/data?file=' + encodeURIComponent(file));
            const data = await response.json();
            return data;
        }
        
        function updateStats() {
            if (!allData.timestamps.length) return;
            
            const current0 = allData.cpu_core0[allData.cpu_core0.length - 1];
            const current2 = allData.cpu_core2[allData.cpu_core2.length - 1];
            const max = Math.max(...allData.cpu_core0, ...allData.cpu_core2);
            const min = Math.min(...allData.cpu_core0, ...allData.cpu_core2);
            const avg = (allData.cpu_core0.reduce((a,b) => a+b, 0) + allData.cpu_core2.reduce((a,b) => a+b, 0)) / (allData.cpu_core0.length + allData.cpu_core2.length);
            
            document.getElementById('current0').textContent = current0.toFixed(1) + '°C';
            document.getElementById('current2').textContent = current2.toFixed(1) + '°C';
            document.getElementById('maxTemp').textContent = max.toFixed(1) + '°C';
            document.getElementById('minTemp').textContent = min.toFixed(1) + '°C';
            document.getElementById('avgTemp').textContent = avg.toFixed(1) + '°C';
            
            document.getElementById('current0').className = 'value ' + getTempClass(current0);
            document.getElementById('current2').className = 'value ' + getTempClass(current2);
            document.getElementById('maxTemp').className = 'value ' + getTempClass(max);
            document.getElementById('minTemp').className = 'value ' + getTempClass(min);
            document.getElementById('avgTemp').className = 'value ' + getTempClass(avg);
        }
        
        function getTempClass(temp) {
            if (temp >= 80) return 'hot';
            if (temp >= 60) return 'warm';
            if (temp >= 40) return 'normal';
            return 'cool';
        }
        
        function updateView() {
            const pointsInView = document.getElementById('pointsSelect').value;
            const totalPoints = allData.timestamps.length;
            
            if (pointsInView === 'all') {
                chart.options.scales.x.min = undefined;
                chart.options.scales.x.max = undefined;
                document.getElementById('dataInfo').textContent = `Showing all ${totalPoints} points`;
            } else {
                const points = parseInt(pointsInView);
                const startIdx = Math.max(0, totalPoints - points);
                chart.options.scales.x.min = startIdx;
                chart.options.scales.x.max = totalPoints - 1;
                document.getElementById('dataInfo').textContent = `Showing ${Math.min(points, totalPoints)} of ${totalPoints} points (newest)`;
            }
            chart.update();
        }
        
        function chartZoom(factor) {
            if (factor < 1) {
                chart.zoom(1.25);
            } else {
                chart.zoom(0.8);
            }
        }
        
        function chartPan(direction) {
            const diff = chart.scales.x.max - chart.scales.x.min;
            const shift = Math.floor(diff * 0.3);
            
            if (direction === 'left') {
                chart.pan({ x: shift });
            } else {
                chart.pan({ x: -shift });
            }
        }
        
        function resetZoom() {
            chart.resetZoom();
            updateView();
        }
        
        async function initChart() {
            currentFile = document.getElementById('fileSelect').value;
            allData = await loadData(currentFile);
            
            document.getElementById('loading').style.display = 'none';
            
            updateStats();
            
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: allData.timestamps,
                    datasets: [
                        {
                            label: 'CPU Core 0',
                            data: allData.cpu_core0,
                            borderColor: '#ff6b6b',
                            backgroundColor: 'rgba(255, 107, 107, 0.15)',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 0,
                            pointHoverRadius: 4
                        },
                        {
                            label: 'CPU Core 2',
                            data: allData.cpu_core2,
                            borderColor: '#4ecdc4',
                            backgroundColor: 'rgba(78, 205, 196, 0.15)',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 0,
                            pointHoverRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { color: '#eee', usePointStyle: true, padding: 20 }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: '#00d9ff',
                            bodyColor: '#eee',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: true,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '°C';
                                }
                            }
                        },
                        zoom: {
                            pan: {
                                enabled: true,
                                mode: 'x'
                            },
                            zoom: {
                                wheel: { enabled: true },
                                pinch: { enabled: true },
                                mode: 'x'
                            }
                        }
                    },
                    scales: {
                        x: { 
                            ticks: { 
                                color: '#888',
                                maxTicksLimit: 20,
                                maxRotation: 0
                            },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        y: { 
                            ticks: { 
                                color: '#888',
                                callback: function(value) { return value + '°C'; }
                            },
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            suggestedMin: 30,
                            suggestedMax: 100
                        }
                    },
                    animation: {
                        duration: 500,
                        easing: 'easeOutQuart'
                    }
                }
            });
            
            updateView();
        }
        
        async function updateChart() {
            allData = await loadData(currentFile);
            chart.data.labels = allData.timestamps;
            chart.data.datasets[0].data = allData.cpu_core0;
            chart.data.datasets[1].data = allData.cpu_core2;
            chart.update('none');
            updateStats();
            updateView();
        }
        
        async function changeFile() {
            realtimeEnabled = false;
            document.getElementById('toggleBtn').textContent = 'Live';
            document.getElementById('toggleBtn').classList.remove('active');
            clearInterval(updateInterval);
            
            currentFile = document.getElementById('fileSelect').value;
            allData = await loadData(currentFile);
            chart.data.labels = allData.timestamps;
            chart.data.datasets[0].data = allData.cpu_core0;
            chart.data.datasets[1].data = allData.cpu_core2;
            chart.update();
            updateStats();
            updateView();
        }
        
        function toggleRealtime() {
            realtimeEnabled = !realtimeEnabled;
            const btn = document.getElementById('toggleBtn');
            
            if (realtimeEnabled) {
                btn.textContent = 'Stop';
                btn.classList.add('active');
                updateInterval = setInterval(updateChart, 2000);
            } else {
                btn.textContent = 'Live';
                btn.classList.remove('active');
                clearInterval(updateInterval);
            }
        }
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'r' || e.key === 'R') {
                resetZoom();
            }
        });
        
        initChart();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    files = get_log_files()
    return render_template_string(HTML_TEMPLATE, files=files)

@app.route('/api/data')
def api_data():
    file = request.args.get('file')
    
    files = get_log_files()
    if not file and files:
        file = files[0]
    
    if not file:
        return jsonify({"timestamps": [], "cpu_core0": [], "cpu_core2": []})
    
    filepath = os.path.join(LOG_DIR, file)
    data = parse_log_file(filepath)
    
    return jsonify(data)

if __name__ == '__main__':
    port = config.get("app_port", 5002)
    app.run(host='0.0.0.0', port=port, debug=True)
