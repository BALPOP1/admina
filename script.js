// Quina Results Display Script
const DATA_URL = 'data/results.json';
const SHEET_URL = 'https://docs.google.com/spreadsheets/d/1OttNYHiecAuGG6IRX7lW6lkG5ciEcL8gp3g6lNrN9H8/export?format=csv&gid=300277644';
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutos

// DOM Elements
const updateTimeEl = document.getElementById('updateTime');
const refreshBtn = document.getElementById('refreshBtn');
const latestResultEl = document.getElementById('latestResult');
const previousResultsEl = document.getElementById('previousResults');

// Fetch and display results
async function fetchResults() {
    try {
        refreshBtn.disabled = true;
        refreshBtn.textContent = '⏳ Carregando...';

        // Fetch local JSON
        const localResponse = await fetch(`${DATA_URL}?t=${Date.now()}`);
        let localData = { results: [] };
        if (localResponse.ok) {
            localData = await localResponse.json();
        }

        // Fetch Google Sheet for latest live data
        let sheetResults = [];
        try {
            const sheetResponse = await fetch(SHEET_URL);
            if (sheetResponse.ok) {
                const csvText = await sheetResponse.text();
                sheetResults = parseCSV(csvText);
            }
        } catch (e) {
            console.warn('Failed to fetch from Google Sheet, using local data only');
        }

        // Merge results, removing duplicates based on drawNumber
        const allResults = [...localData.results];
        sheetResults.forEach(sr => {
            if (!allResults.find(r => r.drawNumber == sr.drawNumber)) {
                allResults.push(sr);
            }
        });

        displayResults({ results: allResults, lastUpdated: new Date().toISOString() });
        updateTimeEl.textContent = new Date().toLocaleString('pt-BR');

    } catch (error) {
        console.error('Error fetching results:', error);
        latestResultEl.innerHTML = `
            <div class="error">
                <strong>⚠️ Não foi possível carregar os resultados ⚠️</strong>
                <p>Por favor, tente atualizar a página.</p>
            </div>
        `;
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = '🔄 Atualizar';
    }
}

// Parse CSV from Google Sheet
function parseCSV(csvText) {
    const lines = csvText.split('\n').filter(Boolean);
    const results = [];
    
    // Skip header (Concurso, Data, N1, N2, N3, N4, N5, ...)
    for (let i = 1; i < lines.length; i++) {
        const row = parseCSVLine(lines[i]);
        if (row.length < 7) continue;

        const drawNumber = parseInt(row[0].replace(/\D/g, ''), 10);
        const dateStr = row[1].trim();
        const numbers = row.slice(2, 7).map(v => parseInt(v, 10)).filter(n => !Number.isNaN(n));

        if (!Number.isNaN(drawNumber) && numbers.length === 5) {
            // Convert dd/mm/yyyy to yyyy-mm-dd
            let isoDate = dateStr;
            if (dateStr.includes('/')) {
                const [d, m, y] = dateStr.split('/');
                isoDate = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
            }

            results.push({
                drawNumber,
                date: isoDate,
                numbers
            });
        }
    }
    return results;
}

// Simple CSV line parser
function parseCSVLine(line) {
    const values = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (ch === '"') inQuotes = !inQuotes;
        else if (ch === ',' && !inQuotes) {
            values.push(current.trim());
            current = '';
        } else current += ch;
    }
    values.push(current.trim());
    return values;
}

// Display the results
function displayResults(data) {
    if (!data.results || data.results.length === 0) {
        latestResultEl.innerHTML = '<div class="error">Ainda não há resultados disponíveis.</div>';
        previousResultsEl.innerHTML = '';
        return;
    }

    // Sort results by draw number (newest first)
    const sortedResults = [...data.results].sort((a, b) => b.drawNumber - a.drawNumber);

    // Display latest result
    const latest = sortedResults[0];
    latestResultEl.innerHTML = createLatestResultHTML(latest);

    // Display previous results (skip the first one)
    const previousResults = sortedResults.slice(1);
    if (previousResults.length > 0) {
        previousResultsEl.innerHTML = `
            <div class="results-grid">
                ${previousResults.map(result => createPreviousResultHTML(result)).join('')}
            </div>
        `;
    } else {
        previousResultsEl.innerHTML = '<p style="text-align: center; color: #888;">Ainda não há resultados anteriores.</p>';
    }

    // Update the last fetched time from data
    if (data.lastUpdated) {
        const lastUpdate = new Date(data.lastUpdated);
        updateTimeEl.textContent = lastUpdate.toLocaleString('pt-BR');
    }
}

// Create HTML for latest result
function createLatestResultHTML(result) {
    return `
        <div class="latest-result-card">
            <div class="result-header">
                <div class="draw-info">
                    <span class="label">CONCURSO</span>
                    <span class="value">#${result.drawNumber}</span>
                </div>
                <div class="draw-info">
                    <span class="label">DATA</span>
                    <span class="value">${formatDate(result.date)}</span>
                </div>
            </div>
            <div class="numbers">
                ${result.numbers.map(num => `<div class="number-ball">${num}</div>`).join('')}
            </div>
        </div>
    `;
}

// Create HTML for previous result card
function createPreviousResultHTML(result) {
    return `
        <div class="previous-card">
            <div class="result-header" style="margin-bottom: 12px;">
                <div class="draw-info">
                    <span class="label">CONCURSO #${result.drawNumber}</span>
                    <span class="value" style="font-size: 0.9em;">${formatDate(result.date)}</span>
                </div>
            </div>
            <div class="numbers">
                ${result.numbers.map(num => `<div class="number-ball">${num}</div>`).join('')}
            </div>
        </div>
    `;
}

// Format date string to pt-BR
function formatDate(dateStr) {
    if (!dateStr) return 'Desconhecida';

    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    } catch {
        return dateStr;
    }
}

// Event listeners
refreshBtn.addEventListener('click', fetchResults);

// Initial load
fetchResults();

// Auto-refresh
setInterval(fetchResults, REFRESH_INTERVAL);

console.log('🎰 Resultados da Quina carregados! Atualização automática a cada 5 minutos.');