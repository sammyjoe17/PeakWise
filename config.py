import os
from datetime import timedelta

class Config:
    # Server Configuration
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True

    # API Configuration
    ISO_NE_API_URL = 'https://webservices.iso-ne.com/api/v1.1'
    ISO_USERNAME = 'samhall@mit.edu'  # Direct credential
    ISO_PASSWORD = 'Wk8jEnvnqHHd4ej'  # Direct credential
    
    # Cache Configuration
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # API Rate Limits
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Retry Configuration
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 0.5
    RETRY_STATUS_FORCELIST = [500, 502, 503, 504]
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Default Values
    DEFAULT_FUEL_MIX = {
        "natural_gas": 35,
        "nuclear": 25,
        "hydro": 8,
        "solar": 5,
        "wind": 5,
        "coal": 5,
        "oil": 2,
        "biomass": 5,
        "imports": 8,
        "other": 2
    }
    
    DEFAULT_PRICE = 55.0
    
    # Carbon Intensity Factors (kg CO2/MWh)
    CARBON_INTENSITY_FACTORS = {
        "natural_gas": 400,
        "nuclear": 12,
        "hydro": 24,
        "solar": 45,
        "wind": 11,
        "coal": 820,
        "oil": 650,
        "biomass": 230,  # Average for wood, refuse, landfill gas
        "imports": 350,  # Estimated average based on regional mix
        "other": 400    # Conservative estimate
    } 