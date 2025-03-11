import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime
import logging
from functools import wraps
from config import Config

logger = logging.getLogger(__name__)

def with_retry_and_circuit_breaker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=Config.RETRY_BACKOFF_FACTOR,
            status_forcelist=Config.RETRY_STATUS_FORCELIST
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        with requests.Session() as session:
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            return func(*args, session=session, **kwargs)
    return wrapper

class IsoNeService:
    def __init__(self):
        self.base_url = Config.ISO_NE_API_URL
        self.auth = (Config.ISO_USERNAME, Config.ISO_PASSWORD)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Host': 'webservices.iso-ne.com'
        }
        self._last_successful_fuel_mix = None
        self._last_successful_price = None
    
    @with_retry_and_circuit_breaker
    def get_fuel_mix(self, session=None):
        """Get current fuel mix data with retries and circuit breaker."""
        try:
            # Get generation mix data
            gen_mix_data = None
            try:
                response = session.get(
                    f"{self.base_url}/genfuelmix/current",
                    auth=self.auth,
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    gen_mix_data = response.json()
                    logger.info(f"Generation mix API response: {gen_mix_data}")
            except Exception as e:
                logger.error(f"Error fetching generation mix: {str(e)}")

            # Get resource mix data
            resource_mix_data = None
            try:
                response = session.get(
                    f"{self.base_url}/fuelmix/current",
                    auth=self.auth,
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    resource_mix_data = response.json()
                    logger.info(f"Resource mix API response: {resource_mix_data}")
            except Exception as e:
                logger.error(f"Error fetching resource mix: {str(e)}")

            # Process both datasets
            gen_mix = self._process_generation_mix(gen_mix_data) if gen_mix_data else Config.DEFAULT_FUEL_MIX
            resource_mix = self._process_resource_mix(resource_mix_data) if resource_mix_data else Config.DEFAULT_FUEL_MIX

            # Store the resource mix as last successful
            if resource_mix != Config.DEFAULT_FUEL_MIX:
                self._last_successful_fuel_mix = resource_mix

            return gen_mix, resource_mix

        except Exception as e:
            logger.error(f"Error in get_fuel_mix: {str(e)}")
            return Config.DEFAULT_FUEL_MIX, Config.DEFAULT_FUEL_MIX
    
    @with_retry_and_circuit_breaker
    def get_price(self, session=None):
        """Get current price data with retries and circuit breaker."""
        try:
            # Try the five-minute LMP endpoint first
            response = session.get(
                f"{self.base_url}/fiveminutelmp/current/location/4000",  # Hub location
                auth=self.auth,
                headers=self.headers,
                timeout=10
            )
            
            response.raise_for_status()  # Raise error for non-200 status
            data = response.json()
            logger.info(f"Price API response: {data}")
            
            # Process the price data
            price = self._process_price(data)
            if price is not None:  # Any number, including negative, is valid
                self._last_successful_price = price
                logger.info(f"Using current price from API: {price}")
                return price
                
            # If first endpoint failed, try hourly
            response = session.get(
                f"{self.base_url}/hourlylmp/current/location/4000",
                auth=self.auth,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                price = self._process_price(data)
                if price is not None:
                    self._last_successful_price = price
                    logger.info(f"Using current hourly price: {price}")
                    return price
            
            # If we have a last successful price, use it
            if self._last_successful_price is not None:
                logger.info(f"Using last successful price: {self._last_successful_price}")
                return self._last_successful_price
            
            # Only use default as last resort
            logger.warning(f"No valid price found, using default: {Config.DEFAULT_PRICE}")
            return Config.DEFAULT_PRICE
            
        except Exception as e:
            logger.error(f"Error fetching price: {str(e)}")
            if self._last_successful_price is not None:
                logger.info(f"Using last successful price after error: {self._last_successful_price}")
                return self._last_successful_price
            return Config.DEFAULT_PRICE
    
    @with_retry_and_circuit_breaker
    def get_system_load(self, session=None):
        """Get system load data with retries and circuit breaker."""
        try:
            # Get current system load data
            response = session.get(
                f"{self.base_url}/fiveminutesystemload",
                auth=self.auth,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully fetched system load data")
                return self._process_system_load(data)
            else:
                logger.error(f"Failed to fetch system load data: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching system load: {str(e)}")
            return None

    def _process_system_load(self, data):
        """Process system load data into time series format."""
        try:
            if not data or 'SystemLoads' not in data or 'SystemLoad' not in data['SystemLoads']:
                return None

            loads = data['SystemLoads']['SystemLoad']
            timestamps = []
            actual_values = []
            forecast_values = []

            for entry in loads:
                try:
                    timestamp = datetime.fromisoformat(entry['BeginDate'].replace('Z', '+00:00'))
                    actual = float(entry['LoadMw'])
                    forecast = float(entry['LoadMwForecasted'])
                    
                    timestamps.append(timestamp.isoformat())
                    actual_values.append(actual)
                    forecast_values.append(forecast)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error processing load entry: {e}")
                    continue

            if not timestamps:
                return None

            return {
                'timestamps': timestamps,
                'actual': actual_values,
                'forecast': forecast_values
            }

        except Exception as e:
            logger.error(f"Error processing system load data: {str(e)}")
            return None

    def get_dashboard_data(self):
        """Get all dashboard data with proper error handling."""
        try:
            gen_mix, resource_mix = self.get_fuel_mix()
            price = self.get_price()
            system_load = self.get_system_load()
            
            # Calculate carbon intensity using resource mix percentages
            carbon_intensity = self._calculate_carbon_intensity(
                resource_mix['percentages'] if isinstance(resource_mix, dict) and 'percentages' in resource_mix
                else Config.DEFAULT_FUEL_MIX
            )
            
            # Check if we're using API data
            is_api_price = price != Config.DEFAULT_PRICE
            
            # Prepare the response data
            data = {
                "price": {
                    "current": price,
                    "unit": "$/MWh"
                },
                "generationMix": gen_mix or {
                    'percentages': Config.DEFAULT_FUEL_MIX,
                    'megawatts': {k: 0 for k in Config.DEFAULT_FUEL_MIX.keys()}
                },
                "resourceMix": resource_mix or {
                    'percentages': Config.DEFAULT_FUEL_MIX,
                    'megawatts': {k: 0 for k in Config.DEFAULT_FUEL_MIX.keys()}
                },
                "carbonIntensity": {
                    "current": carbon_intensity,
                    "unit": "kg CO₂eq/MWh"
                },
                "systemLoad": system_load,  # Add system load data
                "timestamp": datetime.now().isoformat(),
                "api_info": {
                    "price_data_source": "api" if is_api_price else "fallback",
                    "fuel_mix_source": "api" if gen_mix and resource_mix else "fallback",
                    "system_load_source": "api" if system_load else "fallback"
                }
            }
            
            logger.info(f"Returning dashboard data with price: {price}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}", exc_info=True)
            # Return fallback data
            default_mix = {
                'percentages': Config.DEFAULT_FUEL_MIX,
                'megawatts': {k: 0 for k in Config.DEFAULT_FUEL_MIX.keys()}
            }
            return {
                "price": {
                    "current": Config.DEFAULT_PRICE,
                    "unit": "$/MWh"
                },
                "generationMix": default_mix,
                "resourceMix": default_mix,
                "carbonIntensity": {
                    "current": self._calculate_carbon_intensity(Config.DEFAULT_FUEL_MIX),
                    "unit": "kg CO₂eq/MWh"
                },
                "systemLoad": None,  # Add empty system load data
                "timestamp": datetime.now().isoformat(),
                "api_info": {
                    "price_data_source": "fallback",
                    "fuel_mix_source": "fallback",
                    "system_load_source": "fallback"
                }
            }
    
    def _process_generation_mix(self, gen_mix_data):
        """Process generation mix data."""
        try:
            # Initialize totals with expanded categories
            total_mw = {
                "natural_gas": 0,
                "nuclear": 0,
                "hydro": 0,
                "solar": 0,
                "wind": 0,
                "coal": 0,
                "oil": 0,
                "biomass": 0,  # Wood, Refuse, Landfill Gas
                "other": 0
            }
            
            if gen_mix_data and 'GenFuelMixes' in gen_mix_data and 'GenFuelMix' in gen_mix_data['GenFuelMixes']:
                for entry in gen_mix_data['GenFuelMixes']['GenFuelMix']:
                    category = entry['FuelCategory']
                    mw = float(entry['GenMw'])
                    
                    if category == 'Natural Gas':
                        total_mw['natural_gas'] += mw
                    elif category == 'Nuclear':
                        total_mw['nuclear'] += mw
                    elif category == 'Coal':
                        total_mw['coal'] += mw
                    elif category == 'Oil':
                        total_mw['oil'] += mw
                    elif category == 'Hydro':
                        total_mw['hydro'] += mw
                    elif category == 'Solar':
                        total_mw['solar'] += mw
                    elif category == 'Wind':
                        total_mw['wind'] += mw
                    elif category in ['Wood', 'Refuse', 'Landfill Gas']:
                        total_mw['biomass'] += mw
                    elif category == 'Other':
                        total_mw['other'] += mw

                # Calculate percentages
                total = sum(total_mw.values())
                if total > 0:
                    percentages = {
                        key: round((value / total) * 100, 2)
                        for key, value in total_mw.items()
                        if value > 0
                    }
                    
                    # Return both MW values and percentages
                    result = {
                        'percentages': percentages,
                        'megawatts': {k: round(v, 2) for k, v in total_mw.items() if v > 0}
                    }
                    
                    logger.info(f"Processed generation mix: {result}")
                    return result

            return {
                'percentages': Config.DEFAULT_FUEL_MIX,
                'megawatts': {k: 0 for k in Config.DEFAULT_FUEL_MIX.keys()}
            }
        except Exception as e:
            logger.error(f"Error processing generation mix: {str(e)}")
            return {
                'percentages': Config.DEFAULT_FUEL_MIX,
                'megawatts': {k: 0 for k in Config.DEFAULT_FUEL_MIX.keys()}
            }

    def _process_resource_mix(self, resource_mix_data):
        """Process resource mix data."""
        try:
            # Initialize totals with expanded categories
            total_mw = {
                "natural_gas": 0,
                "nuclear": 0,
                "hydro": 0,
                "solar": 0,
                "wind": 0,
                "coal": 0,
                "oil": 0,
                "biomass": 0,
                "imports": 0,
                "other": 0
            }
            
            # Process the GenFuelMixes format
            if resource_mix_data and 'GenFuelMixes' in resource_mix_data and 'GenFuelMix' in resource_mix_data['GenFuelMixes']:
                for entry in resource_mix_data['GenFuelMixes']['GenFuelMix']:
                    category = entry['FuelCategory']
                    mw = float(entry['GenMw'])
                    
                    if 'Natural Gas' in category:
                        total_mw['natural_gas'] += mw
                    elif 'Nuclear' in category:
                        total_mw['nuclear'] += mw
                    elif 'Coal' in category:
                        total_mw['coal'] += mw
                    elif 'Oil' in category:
                        total_mw['oil'] += mw
                    elif 'Hydro' in category:
                        total_mw['hydro'] += mw
                    elif 'Solar' in category:
                        total_mw['solar'] += mw
                    elif 'Wind' in category:
                        total_mw['wind'] += mw
                    elif any(x in category for x in ['Wood', 'Refuse', 'Landfill']):
                        total_mw['biomass'] += mw
                    else:
                        total_mw['other'] += mw

                # Calculate percentages
                total = sum(total_mw.values())
                if total > 0:
                    percentages = {
                        key: round((value / total) * 100, 2)
                        for key, value in total_mw.items()
                        if value > 0
                    }
                    
                    # Return both MW values and percentages
                    result = {
                        'percentages': percentages,
                        'megawatts': {k: round(v, 2) for k, v in total_mw.items() if v > 0}
                    }
                    
                    logger.info(f"Processed resource mix: {result}")
                    return result

            # If we get here, either there was no data or processing failed
            logger.warning("Could not process resource mix data, using generation mix data instead")
            return self._process_generation_mix(resource_mix_data)

        except Exception as e:
            logger.error(f"Error processing resource mix: {str(e)}")
            return {
                'percentages': Config.DEFAULT_FUEL_MIX,
                'megawatts': {k: 0 for k in Config.DEFAULT_FUEL_MIX.keys()}
            }
    
    def _process_price(self, data):
        """Process raw price data into standardized format."""
        try:
            logger.info(f"Processing price data: {data}")
            
            # Try to extract price from FiveMinLmp format
            if 'FiveMinLmp' in data:
                try:
                    # The price is directly in the LmpTotal field
                    price = float(data['FiveMinLmp']['LmpTotal'])
                    logger.info(f"Found price in FiveMinLmp: {price}")
                    return price  # Return the price directly, whether positive or negative
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error extracting FiveMinLmp price: {e}")
                    
                    # Try alternate structure where price might be nested in Location
                    try:
                        if 'Location' in data['FiveMinLmp']:
                            price = float(data['FiveMinLmp']['Location'].get('LmpTotal', 0))
                            logger.info(f"Found price in FiveMinLmp Location: {price}")
                            return price
                    except (KeyError, ValueError, TypeError) as e:
                        logger.error(f"Error extracting nested FiveMinLmp price: {e}")
                
            # Try to extract from HourlyLmps format
            if 'HourlyLmps' in data and len(data['HourlyLmps']) > 0:
                try:
                    price = float(data['HourlyLmps'][0]['LmpTotal'])
                    logger.info(f"Found price in HourlyLmps: {price}")
                    return price
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error extracting HourlyLmps price: {e}")
                
            # Try to extract from DaLmps format
            if 'DaLmps' in data and len(data['DaLmps']) > 0:
                try:
                    price = float(data['DaLmps'][0]['LmpTotal'])
                    logger.info(f"Found price in DaLmps: {price}")
                    return price
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error extracting DaLmps price: {e}")
            
            logger.error("No recognized price data format found")
            return None
            
        except Exception as e:
            logger.error(f"Error processing price data: {str(e)}")
            return None
    
    def _calculate_carbon_intensity(self, fuel_mix):
        """Calculate carbon intensity from fuel mix."""
        try:
            total_emissions = sum(
                percentage * Config.CARBON_INTENSITY_FACTORS[fuel]
                for fuel, percentage in fuel_mix.items()
            )
            total_percentage = sum(fuel_mix.values())
            return total_emissions / total_percentage if total_percentage > 0 else 0
        except Exception as e:
            logger.error(f"Error calculating carbon intensity: {str(e)}")
            return 0 