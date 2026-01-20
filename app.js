let allPredictions = [];
let activeFilter = 'All';

async function fetchPredictions() {
    const grid = document.getElementById('prediction-grid');
    const lastSyncSpan = document.getElementById('last-updated');
    
    try {
        const response = await fetch('predictions.json');
        const data = await response.json();
        
        allPredictions = data.predictions || [];
        if (lastSyncSpan) lastSyncSpan.textContent = data.last_updated || 'Unknown';

        renderFilters();
        renderGrid();

    } catch (err) {
        console.error('Beacon fetch error:', err);
        grid.innerHTML = '<div class="loading">Failed to sync with Beacon backend.</div>';
    }
}

function renderFilters() {
    const filterBar = document.getElementById('league-filters');
    if (!filterBar) return;

    const leagues = ['All', ...new Set(allPredictions.map(p => p.league))];
    filterBar.innerHTML = '';
    
    leagues.forEach(league => {
        const btn = document.createElement('button');
        btn.className = `filter-btn ${activeFilter === league ? 'active' : ''}`;
        btn.textContent = league;
        btn.onclick = () => {
            activeFilter = league;
            renderFilters();
            renderGrid();
        };
        filterBar.appendChild(btn);
    });
}

function renderGrid() {
    const grid = document.getElementById('prediction-grid');
    grid.innerHTML = '';

    const filtered = activeFilter === 'All' 
        ? allPredictions 
        : allPredictions.filter(p => p.league === activeFilter);

    if (filtered.length === 0) {
        grid.innerHTML = '<div class="loading">No active beacons for this sector.</div>';
        return;
    }

    filtered.forEach((p, index) => {
        const card = document.createElement('div');
        card.className = 'prediction-card';
        card.style.animationDelay = `${index * 0.1}s`;
        
        const confValue = parseInt(p.conf) || 50;

        card.innerHTML = `
            <div class="card-header">
                <span>${p.league}</span>
                <span>${p.fixture_id}</span>
            </div>
            <div class="teams">${p.home} <span>VS</span> ${p.away}</div>
            
            <div class="confidence-gauge-container">
                <div class="gauge-label">
                    <span>Precision Level</span>
                    <span>${p.conf}</span>
                </div>
                <div class="gauge-track">
                    <div class="gauge-fill" style="width: ${confValue}%"></div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Win/Draw</span>
                    <span class="stat-value">${p.dc}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Goal Forecast</span>
                    <span class="stat-value">${p.ou}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">HT Result</span>
                    <span class="stat-value">${p.ht}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Star Power</span>
                    <span class="stat-value">${p.stars}</span>
                </div>
            </div>
            <div class="main-outcome">
                🎯 ${p.main}
            </div>
        `;
        grid.appendChild(card);
    });
}

function setDynamicYear() {
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
}

// Fetch on load
document.addEventListener('DOMContentLoaded', () => {
    fetchPredictions();
    setDynamicYear();
});

// Refresh every 5 minutes
setInterval(fetchPredictions, 300000);
