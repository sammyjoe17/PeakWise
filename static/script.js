// Initialize DOM elements
const currentPriceEl = document.getElementById('current-price');
const priceCardEl = document.getElementById('price-card');
const carbonIntensityEl = document.getElementById('carbon-intensity');
const ghgCardEl = document.getElementById('ghg-card');
const apiStatusEl = document.getElementById('api-status');

// Initialize control buttons
const forceRefreshBtn = document.getElementById('forceRefreshBtn');
const testConnectionBtn = document.getElementById('testConnectionBtn');
const useSampleBtn = document.getElementById('useSampleBtn');

// Initialize chart objects
let generationMixChart = null;
let systemLoadChart = null;

const chartConfig = {
    type: 'pie',
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    font: {
                        family: 'DM Sans',
                        size: 12
                    },
                    color: '#000000'
                }
            },
            tooltip: {
                titleFont: {
                    family: 'DM Sans',
                    size: 14,
                    weight: 'bold'
                },
                bodyFont: {
                    family: 'DM Sans',
                    size: 12
                },
                backgroundColor: '#000000',
                titleColor: '#fceb00',
                bodyColor: '#ffffff',
                borderColor: '#fceb00',
                borderWidth: 1,
                padding: 10
            }
        }
    }
};

// Update fuel colors to use a palette that complements the brand colors
const fuelColors = {
    'Nuclear': '#1a1a1a',
    'Hydro': '#3498db',
    'Natural Gas': '#fceb00',
    'Oil': '#e67e22',
    'Coal': '#7f8c8d',
    'Solar': '#f1c40f',
    'Wind': '#2ecc71',
    'Refuse': '#95a5a6',
    'Wood': '#d35400',
    'Landfill Gas': '#27ae60',
    'Other': '#bdc3c7'
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

function initCharts() {
    try {
        // Clean up existing charts if they exist
        if (generationMixChart) {
            generationMixChart.destroy();
        }
        if (systemLoadChart) {
            systemLoadChart.destroy();
        }

        // Common chart options
        const commonOptions = {
            type: 'doughnut',
            data: {
                labels: ['Loading...'],
                datasets: [{
                    data: [100],
                    backgroundColor: ['#e2e8f0'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: true
                }
            }
        };

        // Initialize Generation Mix Chart
        const genCtx = document.getElementById('generation-mix-chart').getContext('2d');
        generationMixChart = new Chart(genCtx, {
            ...commonOptions,
            options: {
                ...commonOptions.options,
                plugins: {
                    ...commonOptions.options.plugins,
                    title: {
                        display: true,
                        text: 'Generation Mix',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    layout: {
                        padding: {
                            top: 10,
                            right: 20,
                            bottom: 10,
                            left: 10
                        }
                    }
                }
            }
        });

        // Initialize System Load Chart
        const loadCtx = document.getElementById('system-load-chart').getContext('2d');
        systemLoadChart = new Chart(loadCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Forecast',
                        data: [],
                        borderColor: '#fceb00',
                        backgroundColor: 'rgba(252, 235, 0, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Actual',
                        data: [],
                        borderColor: '#000000',
                        backgroundColor: 'rgba(0, 0, 0, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 10,
                        right: 20,
                        bottom: 10,
                        left: 10
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y || 0;
                                return `${label}: ${value.toFixed(0)} MW`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            stepSize: 1,
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            source: 'auto',
                            maxRotation: 0,
                            autoSkip: true,
                            padding: 8,
                            callback: function(value) {
                                // Format as HH:mm
                                return moment(value).format('HH:mm');
                            }
                        },
                        min: moment().subtract(24, 'hours').toDate(),
                        max: moment().toDate()
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Load (MW)',
                            padding: {
                                top: 0,
                                bottom: 10
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            padding: 8,
                            callback: function(value) {
                                return value.toLocaleString() + ' MW';
                            }
                        }
                    }
                }
            }
        });

        // Update Generation Mix Chart options
        generationMixChart.options.layout = {
            padding: {
                top: 10,
                right: 20,
                bottom: 10,
                left: 10
            }
        };
        generationMixChart.update();

        console.log('Charts initialized successfully');
    } catch (error) {
        console.error('Error initializing charts:', error);
    }
}

function updateGenerationMixChart(mixData) {
    try {
        if (!mixData || typeof mixData !== 'object') {
            console.warn('Invalid generation mix data:', mixData);
            return;
        }

        const percentages = mixData.percentages || {};
        const megawatts = mixData.megawatts || {};
        
        const labels = Object.keys(percentages).map(key => key.replace(/_/g, ' ').toUpperCase());
        const data = Object.values(percentages);
        const colors = labels.map(label => fuelColors[label.toLowerCase().replace(/ /g, '_')] || '#95a5a6');

        generationMixChart.data = {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: '#fff'
            }]
        };

        generationMixChart.options.plugins.tooltip = {
            callbacks: {
                label: function(context) {
                    const label = context.label || '';
                    const value = context.parsed || 0;
                    const mw = megawatts[label.toLowerCase().replace(/ /g, '_')] || 0;
                    return `${label}: ${value.toFixed(1)}% (${mw.toFixed(0)} MW)`;
                }
            }
        };

        generationMixChart.update();
    } catch (error) {
        console.error('Error updating generation mix chart:', error);
    }
}

function updateSystemLoadChart(loadData) {
    try {
        console.log('Attempting to update system load chart with data:', loadData);
        
        if (!systemLoadChart) {
            console.error('System load chart not initialized');
            return;
        }

        if (!loadData || !Array.isArray(loadData.forecast) || !Array.isArray(loadData.actual)) {
            console.warn('Invalid system load data:', loadData);
            return;
        }

        console.log('Updating chart with timestamps:', loadData.timestamps.length);
        console.log('Forecast data points:', loadData.forecast.length);
        console.log('Actual data points:', loadData.actual.length);

        // Update the chart data
        systemLoadChart.data.labels = loadData.timestamps;
        systemLoadChart.data.datasets[0].data = loadData.forecast;
        systemLoadChart.data.datasets[1].data = loadData.actual;

        // Force a full render
        systemLoadChart.options.animation = false;
        systemLoadChart.update('none');
        console.log('Chart update completed');
    } catch (error) {
        console.error('Error updating system load chart:', error);
    }
}

function updateDashboard(data) {
    try {
        console.log('Raw dashboard data:', JSON.stringify(data, null, 2));
        
        // Update price if available and valid
        if (data && data.price && typeof data.price.current === 'number') {
            const price = data.price.current;
            console.log('Processing price value:', price, 'Type:', typeof price);
            
            // Format price with negative numbers handled appropriately
            const formattedPrice = `${price < 0 ? '-$' : '$'}${Math.abs(price).toFixed(2)}/MWh`;
            console.log('Formatted price:', formattedPrice);
            
            currentPriceEl.textContent = formattedPrice;
            priceCardEl.classList.remove('error');
            
            // Add visual indicator for negative prices
            if (price < 0) {
                priceCardEl.classList.add('negative-price');
            } else {
                priceCardEl.classList.remove('negative-price');
            }
        } else {
            console.warn('Invalid price data structure:', {
                hasData: !!data,
                hasPrice: !!(data && data.price),
                priceValue: data?.price?.current,
                priceType: data?.price ? typeof data.price.current : 'undefined'
            });
            currentPriceEl.textContent = 'N/A';
            priceCardEl.classList.add('error');
        }
        
        // Update carbon intensity if available and valid
        if (data && data.carbonIntensity && typeof data.carbonIntensity.current === 'number') {
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

        // Update system load chart if data is available
        if (data && data.systemLoad) {
            console.log('Updating system load chart with data:', data.systemLoad);
            updateSystemLoadChart(data.systemLoad);
        } else {
            console.warn('Invalid system load data:', data?.systemLoad);
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
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Backend error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Raw data received from backend:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching data from backend:', error);
        throw error;
    }
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

// Initialize dashboard updates
async function initDashboard() {
    try {
        // Initialize charts first
        initCharts();
        
        // Initial update
        updateApiStatus('pending', 'Initializing dashboard...');
        
        // Set up button event listeners
        if (forceRefreshBtn) {
            forceRefreshBtn.addEventListener('click', async () => {
                try {
                    updateApiStatus('trying', 'Refreshing data...');
                    const data = await fetchRealISOData();
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
            const data = await fetchRealISOData();
            console.log('Initial data:', data);
            updateDashboard(data);
        } catch (error) {
            console.error('Error fetching initial data:', error);
            updateApiStatus('error', `Initial data fetch failed: ${error.message}`);
        }
        
        // Set up periodic updates every 5 minutes
        setInterval(async () => {
            try {
                const data = await fetchRealISOData();
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

// Start the dashboard when the page loads
document.addEventListener('DOMContentLoaded', initDashboard); 