const express = require('express');
const cors = require('cors');
const axios = require('axios');
const app = express();
const port = process.env.PORT || 3000;

// Enable CORS for frontend requests
app.use(cors());

// Serve static files from the 'public' directory
app.use(express.static('public'));

// ISO-NE API base URL
const ISO_NE_API_URL = 'https://webservices.iso-ne.com/api/v1.1';

// Route to fetch fuel mix data
app.get('/api/fuelmix', async (req, res) => {
    try {
        // Get API credentials from environment variables or config
        const username = process.env.ISO_USERNAME || 'your_username';
        const password = process.env.ISO_PASSWORD || 'your_password';
        
        // Create auth header
        const auth = {
            username: username,
            password: password
        };
        
        // Make request to ISO-NE API
        const response = await axios.get(`${ISO_NE_API_URL}/genfuelmix`, {
            auth: auth,
            headers: {
                'Accept': 'application/json'
            }
        });
        
        // Send data back to client
        res.json(response.data);
    } catch (error) {
        console.error('Error fetching fuel mix data:', error.message);
        res.status(500).json({ 
            error: 'Failed to fetch data from ISO-NE API',
            details: error.message
        });
    }
});

// Route to fetch price data
app.get('/api/prices', async (req, res) => {
    try {
        const username = process.env.ISO_USERNAME || 'your_username';
        const password = process.env.ISO_PASSWORD || 'your_password';
        
        const auth = {
            username: username,
            password: password
        };
        
        const response = await axios.get(`${ISO_NE_API_URL}/markets/da/lmp/da`, {
            auth: auth,
            headers: {
                'Accept': 'application/json'
            }
        });
        
        res.json(response.data);
    } catch (error) {
        console.error('Error fetching price data:', error.message);
        res.status(500).json({ 
            error: 'Failed to fetch price data from ISO-NE API',
            details: error.message
        });
    }
});

// Consolidated endpoint that returns all required data
app.get('/api/dashboard-data', async (req, res) => {
    try {
        const username = process.env.ISO_USERNAME || 'your_username';
        const password = process.env.ISO_PASSWORD || 'your_password';
        
        const auth = {
            username: username,
            password: password
        };
        
        // Make parallel requests for better performance
        const [fuelMixResponse, priceResponse] = await Promise.all([
            axios.get(`${ISO_NE_API_URL}/genfuelmix`, {
                auth: auth,
                headers: { 'Accept': 'application/json' }
            }),
            axios.get(`${ISO_NE_API_URL}/markets/da/lmp/da`, {
                auth: auth,
                headers: { 'Accept': 'application/json' }
            })
        ]);
        
        // Process the data into the format expected by your frontend
        const processedData = {
            price: {
                current: extractPrice(priceResponse.data),
                unit: '$/MWh'
            },
            fuelMix: extractFuelMix(fuelMixResponse.data),
            carbonIntensity: {
                current: calculateCarbonIntensity(extractFuelMix(fuelMixResponse.data)),
                unit: 'kg CO₂eq/MWh'
            },
            timestamp: new Date().toISOString()
        };
        
        res.json(processedData);
    } catch (error) {
        console.error('Error fetching dashboard data:', error.message);
        res.status(500).json({ 
            error: 'Failed to fetch dashboard data',
            details: error.message
        });
    }
});

// Helper functions to extract and process data
function extractPrice(priceData) {
    // Implementation depends on the actual API response structure
    // This is a placeholder - you'll need to adjust based on actual data
    if (priceData && priceData.Prices && priceData.Prices.length > 0) {
        return priceData.Prices[0].Price || 50;
    }
    return 50; // Default fallback
}

function extractFuelMix(fuelMixData) {
    // Implementation depends on the actual API response structure
    // This is a placeholder - you'll need to adjust based on actual data
    const defaultMix = {
        natural_gas: 40,
        nuclear: 30,
        renewables: 20,
        coal: 5,
        oil: 5
    };
    
    if (!fuelMixData || !fuelMixData.GenFuelMixes) {
        return defaultMix;
    }
    
    try {
        const mix = fuelMixData.GenFuelMixes[0];
        return {
            natural_gas: mix.NaturalGas || 0,
            nuclear: mix.Nuclear || 0,
            renewables: (mix.Solar || 0) + (mix.Wind || 0) + (mix.Hydro || 0),
            coal: mix.Coal || 0,
            oil: mix.Oil || 0
        };
    } catch (error) {
        console.error('Error processing fuel mix:', error);
        return defaultMix;
    }
}

function calculateCarbonIntensity(fuelMix) {
    // Same implementation as your frontend
    const emissionFactors = {
        natural_gas: 400,
        nuclear: 12,
        renewables: 25,
        coal: 820,
        oil: 650
    };
    
    let totalEmissions = 0;
    let totalPercentage = 0;
    
    for (const fuel in fuelMix) {
        if (fuelMix[fuel] > 0) {
            totalEmissions += fuelMix[fuel] * emissionFactors[fuel];
            totalPercentage += fuelMix[fuel];
        }
    }
    
    return totalPercentage > 0 ? totalEmissions / totalPercentage : 0;
}

// Start the server
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
}); 