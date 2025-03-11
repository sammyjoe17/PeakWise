from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
from requests.auth import HTTPBasicAuth
import os
import logging
import sys
from datetime import datetime, timedelta
import random
import math
from services.iso_ne_service import IsoNeService
from config import Config

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT
)
logger = logging.getLogger('iso-ne-api')

iso_service = IsoNeService()

@app.route('/')
def home():
    """Render the dashboard page."""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve the favicon.ico file."""
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)

@app.route('/api/fuel-mix')
def get_fuel_mix():
    """Get current fuel mix data."""
    return jsonify(iso_service.get_fuel_mix())

@app.route('/api/price')
def get_price():
    """Get current electricity price."""
    return jsonify({
        "price": iso_service.get_price(),
        "unit": "$/MWh"
    })

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get consolidated dashboard data."""
    return jsonify(iso_service.get_dashboard_data())

@app.route('/api/test')
def test_api_connection():
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Test multiple endpoints
    endpoints = [
        '/hourlylmp/da/final',     # Working price endpoint
        '/genfuelmix/current'      # Prioritize this fuel mix endpoint
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                f"{Config.ISO_NE_BASE_URL}{endpoint}",
                auth=HTTPBasicAuth(Config.ISO_NE_USERNAME, Config.ISO_NE_PASSWORD),
                headers={"Accept": "application/json"},
                timeout=10
            )
            
            test_result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "message": "OK" if response.status_code == 200 else ""
            }
            
        except Exception as e:
            test_result = {
                "endpoint": endpoint,
                "status_code": 0,
                "success": False,
                "message": str(e)
            }
            
        results["tests"].append(test_result)
    
    return jsonify(results)

@app.route('/api/sample-data')
def get_sample_data():
    """Return sample data for testing."""
    current_time = datetime.now()
    
    # Generate timestamps for the last 24 hours, one per minute
    timestamps = [
        (current_time - timedelta(minutes=i)).isoformat()
        for i in range(24 * 60)  # 24 hours * 60 minutes
    ]
    timestamps.reverse()  # Most recent last
    
    # Generate realistic load data
    base_load = 15000  # Base load in MW
    peak_variation = 3000  # Peak variation in MW
    daily_pattern = 2000  # Additional daily pattern variation
    forecast_error = 500  # Maximum forecast error in MW
    
    # Generate actual values with both daily and hourly patterns
    actual_values = []
    for i in range(24 * 60):
        hour = i / 60
        # Daily pattern: lowest at 3am, highest at 6pm
        daily_factor = math.sin((hour - 3) * math.pi / 24)
        # Add some random noise
        noise = random.uniform(-200, 200)
        
        load = (
            base_load +  # Base load
            peak_variation * math.sin(i * math.pi / (12 * 60)) +  # 12-hour pattern
            daily_pattern * daily_factor +  # Daily pattern
            noise  # Random variation
        )
        actual_values.append(load)
    
    # Generate forecast values with realistic errors
    forecast_values = [
        actual + random.uniform(-forecast_error, forecast_error)
        for actual in actual_values
    ]
    
    sample_mix = {
        "natural_gas": 42,
        "nuclear": 28,
        "hydro": 12,
        "solar": 5,
        "wind": 5,
        "coal": 3,
        "biomass": 3,
        "oil": 2
    }
    
    sample_data = {
        "price": {
            "current": 65.75,
            "unit": "$/MWh"
        },
        "generationMix": {
            "percentages": sample_mix,
            "megawatts": {k: v * 100 for k, v in sample_mix.items()}
        },
        "resourceMix": {
            "percentages": sample_mix,
            "megawatts": {k: v * 100 for k, v in sample_mix.items()}
        },
        "carbonIntensity": {
            "current": 230.5,
            "unit": "kg CO₂eq/MWh"
        },
        "systemLoad": {
            "timestamps": timestamps,
            "actual": actual_values,
            "forecast": forecast_values
        },
        "timestamp": current_time.isoformat(),
        "api_info": {
            "price_data_source": "sample",
            "fuel_mix_source": "sample",
            "system_load_source": "sample"
        }
    }
    return jsonify(sample_data)

@app.route('/api/test-connection')
def test_connection():
    """Test the connection to the ISO-NE API."""
    try:
        # Get a small amount of data to test the connection
        data = iso_service.get_dashboard_data()
        return jsonify({
            "status": "success",
            "message": "Successfully connected to ISO-NE API",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to ISO-NE API: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

def extract_price(price_data):
    """Extract price from various response formats."""
    logger.info(f"Attempting to extract price from data: {str(price_data)[:200]}...")
    
    # Handle default case
    if isinstance(price_data, dict) and price_data.get('default', False):
        return price_data.get('price', 50.0)
    
    try:
        # Format 1: Prices array
        if price_data and 'Prices' in price_data and len(price_data['Prices']) > 0:
            price = price_data['Prices'][0].get('Price', 0)
            if price: return price
        
        # Format 2: LmpData array
        if price_data and 'LmpData' in price_data and len(price_data['LmpData']) > 0:
            price = price_data['LmpData'][0].get('LmpTotal', 0)
            if price: return price
        
        # Format 3: Direct price property
        if price_data and 'Price' in price_data:
            price = price_data['Price']
            if price: return price
            
        # Format 4: SystemPrice
        if price_data and 'SystemPrice' in price_data:
            price = price_data['SystemPrice']
            if price: return price
        
        # Format 5: FiveMinPrices
        if price_data and 'FiveMinPrices' in price_data and len(price_data['FiveMinPrices']) > 0:
            price = price_data['FiveMinPrices'][0].get('Price', 0)
            if price: return price
        
        # Format 6: HourlyLmps
        if price_data and 'HourlyLmps' in price_data and len(price_data['HourlyLmps']) > 0:
            price = price_data['HourlyLmps'][0].get('LmpTotal', 0)
            if price: return price
        
        # Format 7: FiveMinuteLmp
        if price_data and 'FiveMinuteLmps' in price_data and len(price_data['FiveMinuteLmps']) > 0:
            # Try to extract LMP price from first location
            if 'Location' in price_data['FiveMinuteLmps'][0]:
                location_data = price_data['FiveMinuteLmps'][0].get('Location', {})
                price = location_data.get('LmpTotal', 0)
                if price:
                    logger.info(f"Found FiveMinuteLmp price: {price}")
                    return price
            
            # If no specific Location or LmpTotal, try other potential price values
            for field in ['TotalPrice', 'Price', 'Value', 'LmpTotal']:
                price = price_data['FiveMinuteLmps'][0].get(field, 0)
                if price:
                    logger.info(f"Found FiveMinuteLmp {field}: {price}")
                    return price
        
        # Format 8: HourlyLmp
        if price_data and 'HourlyLmps' in price_data and len(price_data['HourlyLmps']) > 0:
            hourly_lmp = price_data['HourlyLmps'][0]
            
            # Try Location object first
            if 'Location' in hourly_lmp:
                location = hourly_lmp.get('Location', {})
                price = location.get('LmpTotal', 0)
                if price:
                    logger.info(f"Found hourly LMP price: {price}")
                    return price
            
            # Try directly on the HourlyLmp object
            for field in ['LmpTotal', 'TotalPrice', 'Price', 'Value']:
                price = hourly_lmp.get(field, 0)
                if price:
                    logger.info(f"Found hourly LMP {field}: {price}")
                    return price
        
        # Deeper search - first level
        for key, value in price_data.items():
            if isinstance(value, list) and len(value) > 0:
                # Try to find a price field in the first item of the list
                if isinstance(value[0], dict):
                    for possible_price_key in ['Price', 'LmpTotal', 'price', 'value', 'Amount']:
                        if possible_price_key in value[0]:
                            price = value[0][possible_price_key]
                            if isinstance(price, (int, float)) and price > 0:
                                logger.info(f"Found price {price} in {key}[0].{possible_price_key}")
                                return price
        
        # Log the full data structure to help diagnosis
        logger.warning(f"Could not extract price from data: {price_data}")
        return 50  # Default fallback
    except Exception as e:
        logger.error(f"Error extracting price: {e}", exc_info=True)
        return 50

def extract_fuel_mix(fuel_mix_data):
    # Placeholder - adjust based on actual API response structure
    default_mix = {
        "natural_gas": 40,
        "nuclear": 30,
        "renewables": 20,
        "coal": 5,
        "oil": 5
    }
    
    if not fuel_mix_data or 'GenFuelMixes' not in fuel_mix_data:
        return default_mix
    
    try:
        mix = fuel_mix_data['GenFuelMixes'][0]
        return {
            "natural_gas": mix.get('NaturalGas', 0),
            "nuclear": mix.get('Nuclear', 0),
            "renewables": mix.get('Solar', 0) + mix.get('Wind', 0) + mix.get('Hydro', 0),
            "coal": mix.get('Coal', 0),
            "oil": mix.get('Oil', 0)
        }
    except Exception:
        return default_mix

def calculate_carbon_intensity(fuel_mix):
    emission_factors = {
        "natural_gas": 400,
        "nuclear": 12,
        "renewables": 25,
        "coal": 820,
        "oil": 650
    }
    
    total_emissions = 0
    total_percentage = 0
    
    for fuel, percentage in fuel_mix.items():
        if percentage > 0:
            total_emissions += percentage * emission_factors.get(fuel, 0)
            total_percentage += percentage
    
    return total_emissions / total_percentage if total_percentage > 0 else 0

def calculate_estimated_price(fuel_mix):
    """Calculate an estimated price based on the fuel mix."""
    # Base costs per fuel type ($/MWh)
    fuel_costs = {
        "natural_gas": 60,
        "nuclear": 30,
        "renewables": 15,
        "coal": 65,
        "oil": 120
    }
    
    # Calculate weighted average
    total_percentage = sum(fuel_mix.values())
    if total_percentage <= 0:
        return 55.0  # Default fallback
        
    weighted_price = 0
    for fuel, percentage in fuel_mix.items():
        weighted_price += (percentage / total_percentage) * fuel_costs.get(fuel, 50)
    
    # Add market variability (±20%)
    variability = random.uniform(0.8, 1.2)
    
    return round(weighted_price * variability, 2)

# Add a dedicated function to try different fuel mix endpoints
def try_fetch_fuel_mix():
    """Try multiple endpoints to get fuel mix data."""
    # Try endpoints in priority order
    fuel_mix_endpoints = [
        '/genfuelmix/current',  # Try this first - might be faster
        '/genfuelmix',          # The standard endpoint that's been timing out
        '/genforecast',         # Alternative that might have fuel mix info
        '/fuelmix'              # Another alternative name
    ]
    
    for endpoint in fuel_mix_endpoints:
        try:
            logger.info(f"Trying fuel mix endpoint: {endpoint}")
            response = requests.get(
                f"{ISO_NE_API_URL}{endpoint}",
                auth=HTTPBasicAuth(ISO_USERNAME, ISO_PASSWORD),
                headers={'Accept': 'application/json'},
                timeout=10  # Use a reasonable timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Success with fuel mix endpoint: {endpoint}")
                data = response.json()
                
                # Try to extract fuel mix data
                fuel_mix = None
                if endpoint == '/genfuelmix/current':
                    fuel_mix = extract_fuel_mix_current(data)
                else:
                    fuel_mix = extract_fuel_mix(data)
                
                if fuel_mix:
                    return fuel_mix, endpoint
                else:
                    logger.warning(f"Could not extract fuel mix from {endpoint} response")
            else:
                logger.warning(f"Endpoint {endpoint} returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Request to {endpoint} timed out")
        except Exception as e:
            logger.error(f"Error with endpoint {endpoint}: {e}")
    
    # If we got here, none of the endpoints worked
    return None, None

def extract_fuel_mix_current(data):
    """Extract fuel mix from the /genfuelmix/current endpoint response."""
    try:
        logger.info(f"Extracting fuel mix from /genfuelmix/current data: {str(data)[:200]}...")
        
        # Check for different possible formats based on the API documentation
        if 'GenFuelMixes' in data and len(data['GenFuelMixes']) > 0:
            mix = data['GenFuelMixes'][0]
        elif 'CurrentMixes' in data and len(data['CurrentMixes']) > 0:
            mix = data['CurrentMixes'][0]
        elif 'FuelMix' in data:
            mix = data['FuelMix']
        else:
            # No known format found
            logger.warning("Could not find fuel mix data in expected format")
            return None
        
        # Extract values with multiple possible field names
        result = {
            "natural_gas": get_first_value(mix, ['NaturalGas', 'Gas', 'Natural_Gas']),
            "nuclear": get_first_value(mix, ['Nuclear']),
            "renewables": sum([
                get_first_value(mix, ['Solar', 'Photovoltaic']), 
                get_first_value(mix, ['Wind']),
                get_first_value(mix, ['Hydro', 'HydroElectric'])
            ]),
            "coal": get_first_value(mix, ['Coal']),
            "oil": get_first_value(mix, ['Oil', 'Petroleum'])
        }
        
        # Check if we got any meaningful data
        if sum(result.values()) < 10:  # If total is less than 10%, probably bad data
            logger.warning(f"Fuel mix data appears invalid: {result}")
            return None
            
        logger.info(f"Successfully extracted fuel mix: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting fuel mix from current data: {e}")
        return None

def get_first_value(data_dict, possible_keys, default=0):
    """Helper to get the first available value from multiple possible keys."""
    for key in possible_keys:
        if key in data_dict and isinstance(data_dict[key], (int, float)):
            return data_dict[key]
    return default

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG) 