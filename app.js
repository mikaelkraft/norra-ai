async function fetchPredictions() {
    const grid = document.getElementById('prediction-grid');
    try {
        // Fetch from the flat JSON file (GitHub Pages style)
        const response = await fetch('predictions.json');
        const data = await response.json();

        if (data.length === 0) {
            grid.innerHTML = '<div class="loading">No active beacons detected for today.</div>';
            return;
        }

        grid.innerHTML = ''; // Clear loading

        data.forEach(p => {
            const card = document.createElement('div');
            card.className = 'prediction-card';
            card.innerHTML = `
                <div class="card-header">
                    <span>${p.league}</span>
                    <span>${p.date}</span>
                </div>
                <div class="teams">${p.home} <span>VS</span> ${p.away}</div>
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
                    🎯 ${p.main} (${p.conf})
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (err) {
        console.error('Beacon fetch error:', err);
        grid.innerHTML = '<div class="loading">Failed to sync with Beacon backend.</div>';
    }
}

// Fetch on load
document.addEventListener('DOMContentLoaded', fetchPredictions);

// Refresh every 5 minutes
setInterval(fetchPredictions, 300000);
