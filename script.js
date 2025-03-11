// Initialize DOM elements
const currentPriceEl = document.getElementById('current-price');
const priceCardEl = document.getElementById('price-card');
const carbonIntensityEl = document.getElementById('carbon-intensity');
const ghgCardEl = document.getElementById('ghg-card');
const lastUpdatedEl = document.getElementById('last-updated');
const apiStatusEl = document.getElementById('api-status');

// Initialize control buttons
const forceRefreshBtn = document.getElementById('force-refresh');
const testConnectionBtn = document.getElementById('test-connection');
const testDirectBtn = document.getElementById('test-direct');
const useSampleBtn = document.getElementById('use-sample');
const checkBackendBtn = document.getElementById('check-backend');
const hideLoginBtn = document.getElementById('hide-login');
const debugToggleBtn = document.getElementById('debug-toggle');

// Initialize chart objects
let generationMixChart = null;
let resourceMixChart = null;

// Chart colors for different fuel types
const fuelColors = {
    'natural_gas': '#ff6384',
    'nuclear': '#36a2eb',
    'hydro': '#4bc0c0',
    'solar': '#ffcd56',
    'wind': '#ff9f40',
    'coal': '#8c8c8c',
    'biomass': '#2ecc71',
    'oil': '#e67e22',
    'imports': '#9b59b6',
    'other': '#95a5a6'
};

// Function to check if data is from real-time API
function isRealData(data) {
    const price = data.api_info?.price_data_source === 'api';
    const fuelMix = data.api_info?.fuel_mix_source === 'api';
    return {
        price,
        fuelMix,
        anyReal: price || fuelMix
    };
}

// Function to update API status
function updateApiStatus(status, message) {
    if (!apiStatusEl) return;
    
    // Remove all existing status classes
    apiStatusEl.classList.remove('success', 'error', 'pending', 'trying');
    
    // Add the new status class
    apiStatusEl.classList.add(status);
    
    // Update the status text
    const statusTextEl = apiStatusEl.querySelector('.status-text');
    if (statusTextEl) {
        statusTextEl.textContent = `API Status: ${message}`;
    }
}

function updateDashboard(data) {
    try {
        console.log('Updating dashboard with data:', data);
        
        // Update price if available and valid
        if (data && data.price && typeof data.price.current === 'number' && !isNaN(data.price.current)) {
            currentPriceEl.textContent = `$${data.price.current.toFixed(2)}/MWh`;
            priceCardEl.classList.remove('error');
        } else {
            console.warn('Invalid price data:', data?.price);
            currentPriceEl.textContent = 'N/A';
            priceCardEl.classList.add('error');
        }
        
        // Update carbon intensity if available and valid
        if (data && data.carbonIntensity && typeof data.carbonIntensity.current === 'number' && !isNaN(data.carbonIntensity.current)) {
            carbonIntensityEl.textContent = `${data.carbonIntensity.current.toFixed(1)} kg CO₂eq/MWh`;
            ghgCardEl.classList.remove('error');
        } else {
            console.warn('Invalid carbon intensity data:', data?.carbonIntensity);
            carbonIntensityEl.textContent = 'N/A';
            ghgCardEl.classList.add('error');
        }
        
        // Update generation mix chart if data is available
        if (data && data.generationMix && typeof data.generationMix === 'object' && !Array.isArray(data.generationMix)) {
            console.log('Updating generation mix chart with data:', data.generationMix);
            updateGenerationMixChart(data.generationMix);
        } else {
            console.warn('Invalid generation mix data:', data?.generationMix);
        }
        
        // Update resource mix chart if data is available
        if (data && data.resourceMix && typeof data.resourceMix === 'object' && !Array.isArray(data.resourceMix)) {
            console.log('Updating resource mix chart with data:', data.resourceMix);
            updateResourceMixChart(data.resourceMix);
        } else {
            console.warn('Invalid resource mix data:', data?.resourceMix);
        }
        
        // Update last updated timestamp
        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = new Date().toLocaleString();
        }
        
        // Update API status based on data source
        if (data && data.api_info) {
            const status = isRealData(data);
            if (status.price && status.fuelMix) {
                updateApiStatus('success', 'Using real-time data from ISO-NE API');
            } else if (status.anyReal) {
                updateApiStatus('pending', 'Using partial real-time data from ISO-NE API');
            } else {
                updateApiStatus('error', 'Using simulated data');
            }
        } else {
            updateApiStatus('error', 'No API status information available');
        }
    } catch (error) {
        console.error('Error updating dashboard:', error);
        updateApiStatus('error', `Dashboard update error: ${error.message}`);
    }
}

// Function to fetch real data from ISO-NE API
async function fetchRealISOData() {
    try {
        const url = '/api/dashboard-data';
        console.log('Fetching real data from backend:', url);
        
        // Get data from our backend
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Backend error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Raw data received from backend:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // The data is already in the correct format, no need to transform
        return data;
    } catch (error) {
        console.error('Error fetching data from backend:', error);
        throw error;
    }
}

// Initialize dashboard updates
async function initDashboard() {
    try {
        // Initial update
        updateApiStatus('pending', 'Initializing dashboard...');
        
        // Set up button event listeners
        if (forceRefreshBtn) {
            forceRefreshBtn.addEventListener('click', async () => {
                try {
                    updateApiStatus('trying', 'Refreshing data...');
                    const response = await fetch('/api/dashboard-data');
                    const data = await response.json();
                    updateDashboard(data);
                } catch (error) {
                    console.error('Error refreshing data:', error);
                    updateApiStatus('error', `Refresh failed: ${error.message}`);
                }
            });
        }

        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', async () => {
                try {
                    updateApiStatus('trying', 'Testing API connection...');
                    const response = await fetch('/api/test-connection');
                    const result = await response.json();
                    updateApiStatus('success', `Connection test: ${result.message}`);
                } catch (error) {
                    console.error('Connection test failed:', error);
                    updateApiStatus('error', `Connection test failed: ${error.message}`);
                }
            });
        }

        if (useSampleBtn) {
            useSampleBtn.addEventListener('click', async () => {
                try {
                    updateApiStatus('trying', 'Loading sample data...');
                    const response = await fetch('/api/sample-data');
                    const data = await response.json();
                    updateDashboard(data);
                } catch (error) {
                    console.error('Error loading sample data:', error);
                    updateApiStatus('error', `Sample data failed: ${error.message}`);
                }
            });
        }

        // Initial data fetch
        try {
            const response = await fetch('/api/dashboard-data');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Initial data:', data);
            updateDashboard(data);
        } catch (error) {
            console.error('Error fetching initial data:', error);
            updateApiStatus('error', `Initial data fetch failed: ${error.message}`);
        }
        
        // Set up periodic updates every 5 minutes
        setInterval(async () => {
            try {
                const response = await fetch('/api/dashboard-data');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error in periodic update:', error);
                updateApiStatus('error', `Update failed: ${error.message}`);
            }
        }, 5 * 60 * 1000);
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        updateApiStatus('error', `Dashboard initialization error: ${error.message}`);
    }
}

function updateGenerationMixChart(mixData) {
    const ctx = document.getElementById('generation-mix-chart');
    if (!ctx) {
        console.warn('Generation mix chart canvas not found');
        return;
    }

    if (generationMixChart) {
        generationMixChart.destroy();
    }

    const labels = Object.keys(mixData).map(key => key.replace(/_/g, ' ').toUpperCase());
    const data = Object.values(mixData);
    const colors = labels.map(label => fuelColors[label.toLowerCase().replace(/ /g, '_')] || '#95a5a6');

    generationMixChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        font: {
                            size: 10
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

function updateResourceMixChart(mixData) {
    const ctx = document.getElementById('resource-mix-chart');
    if (!ctx) {
        console.warn('Resource mix chart canvas not found');
        return;
    }

    if (resourceMixChart) {
        resourceMixChart.destroy();
    }

    const labels = Object.keys(mixData).map(key => key.replace(/_/g, ' ').toUpperCase());
    const data = Object.values(mixData);
    const colors = labels.map(label => fuelColors[label.toLowerCase().replace(/ /g, '_')] || '#95a5a6');

    resourceMixChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        font: {
                            size: 10
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

// Start the dashboard when the page loads
document.addEventListener('DOMContentLoaded', initDashboard);