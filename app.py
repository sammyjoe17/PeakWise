from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
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
from functools import wraps

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///peakwise.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)  # For session management
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Create database tables
with app.app_context():
    db.create_all()

# Configure logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT
)
logger = logging.getLogger('iso-ne-api')

iso_service = IsoNeService()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('home'))
        
        flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    """Render the dashboard page."""
    return render_template('index.html')

@app.route('/education')
@login_required
def education():
    """Render the educational content page."""
    return render_template('education.html')

@app.route('/education/grid-basics')
def grid_basics():
    """Render the Grid Basics article."""
    return render_template('article.html',
        title="The Basics of the Electrical Grid",
        read_time=5,
        difficulty="Beginner",
        content="""
            <div class="article-image-container">
                <img src="{{ url_for('static', filename='images/grid-basics.jpg') }}" alt="Electrical Grid Components" class="article-image">
                <div class="image-caption">The electrical grid connects power plants to consumers through transmission and distribution networks.</div>
            </div>

            <h2><i class="fas fa-bolt"></i> What is the Electrical Grid?</h2>
            <p>The electrical grid is a complex network of power plants, transmission lines, substations, and distribution systems that work together to deliver electricity from where it's generated to where it's needed. Think of it as a vast, interconnected web that powers our modern world.</p>

            <h2><i class="fas fa-cogs"></i> Key Components</h2>
            <p>The grid consists of three main components:</p>
            <ul>
                <li><i class="fas fa-industry"></i> <strong>Generation:</strong> Power plants that create electricity from various sources (coal, natural gas, nuclear, renewables)</li>
                <li><i class="fas fa-tower-broadcast"></i> <strong>Transmission:</strong> High-voltage power lines that carry electricity over long distances</li>
                <li><i class="fas fa-home"></i> <strong>Distribution:</strong> Lower-voltage lines that deliver power to homes and businesses</li>
            </ul>

            <div class="infobox">
                <h3><i class="fas fa-lightbulb"></i> Did You Know?</h3>
                <p>The U.S. electrical grid is often called the "largest machine in the world" because it connects thousands of power plants to millions of consumers across the country.</p>
            </div>

            <h2><i class="fas fa-random"></i> How Power Flows</h2>
            <p>Electricity flows from power plants through transmission lines at high voltages (up to 765,000 volts) to reduce energy loss. At substations, transformers step down the voltage for distribution to homes and businesses, where it's typically used at 120/240 volts.</p>

            <h2><i class="fas fa-balance-scale"></i> Grid Balance</h2>
            <p>One of the most critical aspects of grid operation is maintaining balance between supply and demand. Grid operators must constantly adjust power generation to match consumer demand, as electricity cannot be stored in large quantities.</p>

            <h2><i class="fas fa-user"></i> Your Role in the Grid</h2>
            <p>As a consumer, your energy usage patterns directly impact the grid. During peak demand periods (like hot summer afternoons), the grid can become stressed, leading to higher prices and potential reliability issues. By understanding your energy usage and participating in demand response programs, you can help maintain grid stability.</p>
        """
    )

@app.route('/education/demand-response')
def demand_response():
    """Render the Demand Response article."""
    return render_template('article.html',
        title="Understanding Demand Response",
        read_time=7,
        difficulty="Intermediate",
        content="""
            <div class="article-image-container">
                <img src="{{ url_for('static', filename='images/demand-response.jpg') }}" alt="Demand Response Concept" class="article-image">
                <div class="image-caption">Smart meters and automated systems help manage electricity demand during peak periods.</div>
            </div>

            <h2><i class="fas fa-chart-line"></i> What is Demand Response?</h2>
            <p>Demand response is a strategy used by grid operators to manage electricity consumption during peak periods. It involves adjusting power usage in response to signals about grid conditions, helping to maintain balance between supply and demand.</p>

            <h2><i class="fas fa-cogs"></i> How Demand Response Works</h2>
            <p>When the grid is stressed (during peak demand), grid operators can:</p>
            <ul>
                <li><i class="fas fa-bell"></i> Send signals to participating consumers to reduce their energy use</li>
                <li><i class="fas fa-dollar-sign"></i> Offer financial incentives for reducing consumption</li>
                <li><i class="fas fa-clock"></i> Implement time-of-use pricing to encourage off-peak usage</li>
            </ul>

            <div class="infobox">
                <h3><i class="fas fa-chart-bar"></i> Real-World Impact</h3>
                <p>During a major heat wave, demand response programs can reduce peak demand by 5-15%, helping to prevent blackouts and reduce electricity costs for everyone.</p>
            </div>

            <h2><i class="fas fa-tags"></i> Types of Demand Response</h2>
            <p>There are several types of demand response programs:</p>
            <ul>
                <li><i class="fas fa-tag"></i> <strong>Price-based:</strong> Consumers respond to varying electricity prices</li>
                <li><i class="fas fa-gift"></i> <strong>Incentive-based:</strong> Consumers receive payments for reducing usage</li>
                <li><i class="fas fa-exclamation-triangle"></i> <strong>Emergency:</strong> Voluntary or mandatory reductions during grid emergencies</li>
            </ul>

            <h2><i class="fas fa-star"></i> Benefits of Participation</h2>
            <p>Participating in demand response programs can:</p>
            <ul>
                <li><i class="fas fa-piggy-bank"></i> Reduce your electricity bills</li>
                <li><i class="fas fa-shield-alt"></i> Help prevent blackouts</li>
                <li><i class="fas fa-leaf"></i> Support the integration of renewable energy</li>
                <li><i class="fas fa-globe"></i> Contribute to a more sustainable energy future</li>
            </ul>

            <h2><i class="fas fa-user-plus"></i> How to Participate</h2>
            <p>Many utilities offer demand response programs. You can:</p>
            <ul>
                <li><i class="fas fa-phone"></i> Contact your utility to learn about available programs</li>
                <li><i class="fas fa-thermometer-half"></i> Install smart thermostats and other automated devices</li>
                <li><i class="fas fa-clock"></i> Sign up for time-of-use pricing plans</li>
                <li><i class="fas fa-users"></i> Join community-based demand response initiatives</li>
            </ul>
        """
    )

@app.route('/education/renewable-energy')
def renewable_energy():
    """Render the Renewable Energy Integration article."""
    return render_template('article.html',
        title="Renewable Energy Integration",
        read_time=6,
        difficulty="Intermediate",
        content="""
            <div class="article-image-container">
                <img src="{{ url_for('static', filename='images/renewable-energy.jpg') }}" alt="Renewable Energy Sources" class="article-image">
                <div class="image-caption">Solar panels and wind turbines are becoming increasingly common sights in our energy landscape.</div>
            </div>

            <h2><i class="fas fa-sun"></i> The Rise of Renewable Energy</h2>
            <p>Renewable energy sources like solar and wind are playing an increasingly important role in our electrical grid. However, integrating these variable resources presents unique challenges and opportunities.</p>

            <h2><i class="fas fa-list"></i> Types of Renewable Energy</h2>
            <p>The main renewable energy sources integrated into the grid include:</p>
            <ul>
                <li><i class="fas fa-solar-panel"></i> <strong>Solar Power:</strong> Photovoltaic panels and concentrated solar power</li>
                <li><i class="fas fa-wind"></i> <strong>Wind Power:</strong> Onshore and offshore wind turbines</li>
                <li><i class="fas fa-water"></i> <strong>Hydropower:</strong> Traditional dams and run-of-river systems</li>
                <li><i class="fas fa-tree"></i> <strong>Biomass:</strong> Organic materials converted to energy</li>
            </ul>

            <div class="infobox">
                <h3><i class="fas fa-sync"></i> Grid Flexibility</h3>
                <p>To accommodate variable renewable energy, the grid needs to be more flexible. This means having the ability to quickly adjust power generation and consumption to match the changing output of renewable sources.</p>
            </div>

            <h2><i class="fas fa-exclamation-circle"></i> Challenges of Integration</h2>
            <p>Integrating renewable energy presents several challenges:</p>
            <ul>
                <li><i class="fas fa-cloud-sun"></i> <strong>Variability:</strong> Solar and wind power output changes with weather conditions</li>
                <li><i class="fas fa-chart-line"></i> <strong>Predictability:</strong> Accurate forecasting is essential for grid planning</li>
                <li><i class="fas fa-balance-scale"></i> <strong>Grid Stability:</strong> Maintaining frequency and voltage within acceptable ranges</li>
                <li><i class="fas fa-battery-full"></i> <strong>Storage:</strong> Need for energy storage to balance supply and demand</li>
            </ul>

            <h2><i class="fas fa-lightbulb"></i> Solutions and Innovations</h2>
            <p>Grid operators and technology providers are developing various solutions:</p>
            <ul>
                <li><i class="fas fa-robot"></i> Advanced forecasting systems</li>
                <li><i class="fas fa-battery-three-quarters"></i> Grid-scale energy storage</li>
                <li><i class="fas fa-microchip"></i> Smart grid technologies</li>
                <li><i class="fas fa-users"></i> Demand response programs</li>
                <li><i class="fas fa-solar-panel"></i> Microgrids and distributed generation</li>
            </ul>

            <h2><i class="fas fa-rocket"></i> The Future of Renewable Integration</h2>
            <p>As technology advances and costs decrease, renewable energy will play an even larger role in our grid. This transition requires:</p>
            <ul>
                <li><i class="fas fa-tools"></i> Continued investment in grid infrastructure</li>
                <li><i class="fas fa-flask"></i> Development of new storage technologies</li>
                <li><i class="fas fa-desktop"></i> Enhanced grid management systems</li>
                <li><i class="fas fa-file-contract"></i> Supportive policies and regulations</li>
            </ul>
        """
    )

@app.route('/education/smart-grid')
def smart_grid():
    """Render the Smart Grid article."""
    return render_template('article.html',
        title="The Smart Grid Revolution",
        read_time=8,
        difficulty="Advanced",
        content="""
            <div class="article-image-container">
                <img src="{{ url_for('static', filename='images/smart-grid.jpg') }}" alt="Smart Grid Technology" class="article-image">
                <div class="image-caption">The smart grid uses digital technology to improve efficiency and reliability.</div>
            </div>

            <h2><i class="fas fa-microchip"></i> What is the Smart Grid?</h2>
            <p>The smart grid is a modernized electrical grid that uses digital technology to improve efficiency, reliability, and sustainability. It represents a fundamental transformation in how we generate, distribute, and consume electricity.</p>

            <h2><i class="fas fa-list-check"></i> Key Features of the Smart Grid</h2>
            <p>The smart grid incorporates several advanced technologies:</p>
            <ul>
                <li><i class="fas fa-tachometer-alt"></i> <strong>Advanced Metering Infrastructure (AMI):</strong> Smart meters that provide real-time usage data</li>
                <li><i class="fas fa-robot"></i> <strong>Distribution Automation:</strong> Self-healing systems that detect and respond to problems</li>
                <li><i class="fas fa-battery-full"></i> <strong>Grid Storage:</strong> Advanced batteries and other storage solutions</li>
                <li><i class="fas fa-network-wired"></i> <strong>Microgrids:</strong> Localized grids that can operate independently</li>
                <li><i class="fas fa-sliders-h"></i> <strong>Demand Response:</strong> Automated systems for managing peak demand</li>
            </ul>

            <div class="infobox">
                <h3><i class="fas fa-digital-tachograph"></i> Digital Transformation</h3>
                <p>The smart grid uses digital communication technology to detect and react to local changes in usage, similar to how the internet routes data around problems.</p>
            </div>

            <h2><i class="fas fa-star"></i> Benefits of the Smart Grid</h2>
            <p>The smart grid offers numerous advantages:</p>
            <ul>
                <li><i class="fas fa-shield-alt"></i> <strong>Improved Reliability:</strong> Faster detection and response to problems</li>
                <li><i class="fas fa-bolt"></i> <strong>Better Efficiency:</strong> Reduced energy losses and optimized power flow</li>
                <li><i class="fas fa-lock"></i> <strong>Enhanced Security:</strong> Better protection against cyber threats</li>
                <li><i class="fas fa-user-shield"></i> <strong>Consumer Empowerment:</strong> More control over energy usage and costs</li>
                <li><i class="fas fa-leaf"></i> <strong>Environmental Benefits:</strong> Better integration of renewable energy</li>
            </ul>

            <h2><i class="fas fa-tools"></i> Smart Grid Technologies</h2>
            <p>Key technologies enabling the smart grid include:</p>
            <ul>
                <li><i class="fas fa-wave-square"></i> Phasor Measurement Units (PMUs)</li>
                <li><i class="fas fa-desktop"></i> Advanced Distribution Management Systems (ADMS)</li>
                <li><i class="fas fa-cogs"></i> Energy Management Systems (EMS)</li>
                <li><i class="fas fa-battery-three-quarters"></i> Grid-scale Energy Storage</li>
                <li><i class="fas fa-car"></i> Electric Vehicle Integration</li>
            </ul>

            <h2><i class="fas fa-rocket"></i> The Future of the Smart Grid</h2>
            <p>The smart grid continues to evolve with new technologies and applications:</p>
            <ul>
                <li><i class="fas fa-brain"></i> Artificial Intelligence and Machine Learning</li>
                <li><i class="fas fa-link"></i> Blockchain for Energy Trading</li>
                <li><i class="fas fa-battery-full"></i> Advanced Energy Storage Solutions</li>
                <li><i class="fas fa-car-battery"></i> Vehicle-to-Grid (V2G) Integration</li>
                <li><i class="fas fa-building"></i> Grid-Interactive Efficient Buildings</li>
            </ul>

            <h2><i class="fas fa-user"></i> Your Role in the Smart Grid</h2>
            <p>As a consumer, you can participate in the smart grid through:</p>
            <ul>
                <li><i class="fas fa-tachometer-alt"></i> Installing smart meters and devices</li>
                <li><i class="fas fa-sliders-h"></i> Participating in demand response programs</li>
                <li><i class="fas fa-home"></i> Using smart home technology</li>
                <li><i class="fas fa-car"></i> Considering electric vehicles</li>
                <li><i class="fas fa-solar-panel"></i> Installing solar panels or other distributed generation</li>
            </ul>
        """
    )

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

@app.route('/insights')
@login_required
def insights():
    """Render the personalized insights page."""
    # Generate sample data for the last 24 hours
    current_time = datetime.now()
    hours = [(current_time - timedelta(hours=i)).strftime('%H:%M') for i in range(24)]
    hours.reverse()

    # Generate sample usage data (kWh per hour)
    base_usage = 2.0  # Base usage in kWh
    peak_hours = [18, 19, 20]  # Peak hours (6-8 PM)
    usage_values = []
    for i in range(24):
        if i in peak_hours:
            # Higher usage during peak hours
            usage = base_usage * 2 + random.uniform(0.5, 1.5)
        else:
            # Lower usage during off-peak hours
            usage = base_usage * 0.5 + random.uniform(0.2, 0.8)
        usage_values.append(round(usage, 2))

    # Generate sample carbon intensity data (kg CO₂/kWh)
    base_carbon = 0.5  # Base carbon intensity
    carbon_intensity = []
    for i in range(24):
        if i in peak_hours:
            # Higher carbon intensity during peak hours
            carbon = base_carbon * 1.5 + random.uniform(0.1, 0.3)
        else:
            # Lower carbon intensity during off-peak hours
            carbon = base_carbon * 0.8 + random.uniform(0.05, 0.15)
        carbon_intensity.append(round(carbon, 2))

    # Calculate peak impact percentage
    total_usage = sum(usage_values)
    peak_usage = sum(usage_values[i] for i in peak_hours)
    peak_impact = round((peak_usage / total_usage) * 100, 1)

    # Calculate daily carbon impact
    daily_carbon = sum(usage * carbon for usage, carbon in zip(usage_values, carbon_intensity))
    daily_carbon = round(daily_carbon, 1)

    # Calculate cost impact (assuming higher rates during peak hours)
    base_rate = 0.15  # Base rate per kWh
    peak_rate = 0.30  # Peak rate per kWh
    daily_cost = sum(
        usage * (peak_rate if i in peak_hours else base_rate)
        for i, usage in enumerate(usage_values)
    )
    daily_cost = round(daily_cost, 2)

    # Generate trends (sample data)
    peak_trend = random.uniform(-5, 5)
    carbon_trend = random.uniform(-3, 3)
    cost_trend = random.uniform(-2, 2)

    # Generate personalized recommendations
    recommendations = [
        {
            'icon': 'fa-clock',
            'title': 'Shift Peak Usage',
            'description': 'Your energy usage during peak hours (6-8 PM) is 2.5x higher than off-peak hours. Consider shifting some activities to off-peak times.',
            'savings': '$0.45 per day'
        },
        {
            'icon': 'fa-thermometer-half',
            'title': 'Optimize HVAC',
            'description': 'Your heating/cooling system contributes significantly to peak load. Consider adjusting your thermostat schedule.',
            'savings': '$0.30 per day'
        },
        {
            'icon': 'fa-washing-machine',
            'title': 'Laundry Timing',
            'description': 'Running laundry during peak hours increases your carbon footprint. Try running loads during off-peak hours.',
            'savings': '0.8 kg CO₂ per week'
        }
    ]

    return render_template('insights.html',
        usage_labels=hours,
        usage_values=usage_values,
        carbon_intensity=carbon_intensity,
        peak_impact=peak_impact,
        peak_trend=peak_trend,
        carbon_impact=daily_carbon,
        carbon_trend=carbon_trend,
        cost_impact=daily_cost,
        cost_trend=cost_trend,
        recommendations=recommendations
    )

@app.route('/rewards')
@login_required
def rewards():
    """Render the rewards page."""
    user = User.query.get(session['user_id'])
    # Sample data - in a real app, this would come from a database
    points_balance = user.points
    
    # Sample points history
    points_history = [
        {
            'icon': 'fa-bolt',
            'title': 'Peak Load Reduction',
            'description': 'Reduced energy usage during peak hours (6-8 PM)',
            'points': 100
        },
        {
            'icon': 'fa-leaf',
            'title': 'Carbon Reduction',
            'description': 'Shifted usage to low-carbon intensity hours',
            'points': 75
        },
        {
            'icon': 'fa-clock',
            'title': 'Load Shifting',
            'description': 'Moved laundry to off-peak hours',
            'points': 50
        }
    ]
    
    # Sample available rewards
    available_rewards = [
        {
            'id': 'amazon-10',
            'name': 'Amazon Gift Card',
            'description': '$10 Amazon gift card',
            'points_cost': 1000,
            'image': 'amazon.png'
        },
        {
            'id': 'nike-25',
            'name': 'Nike Gift Card',
            'description': '$25 Nike gift card',
            'points_cost': 2500,
            'image': 'nike.png'
        },
        {
            'id': 'target-15',
            'name': 'Target Gift Card',
            'description': '$15 Target gift card',
            'points_cost': 1500,
            'image': 'target.png'
        }
    ]
    
    return render_template('rewards.html',
        points_balance=points_balance,
        points_history=points_history,
        available_rewards=available_rewards
    )

@app.route('/api/redeem-reward', methods=['POST'])
@login_required
def redeem_reward():
    """Handle reward redemption."""
    try:
        data = request.get_json()
        reward_id = data.get('reward_id')
        user = User.query.get(session['user_id'])
        
        # In a real app, this would:
        # 1. Verify the user has enough points
        # 2. Deduct points from user's balance
        # 3. Generate and send the gift card
        # 4. Record the transaction
        
        return jsonify({
            'success': True,
            'message': 'Reward redeemed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/calculate-points', methods=['POST'])
def calculate_points():
    """Calculate points earned for energy-saving actions."""
    try:
        data = request.get_json()
        action_type = data.get('action_type')
        amount = data.get('amount', 0)
        
        # Points calculation logic
        points = 0
        if action_type == 'peak_reduction':
            # Points for reducing peak usage
            points = int(amount * 10)  # 10 points per kWh reduced during peak
        elif action_type == 'carbon_reduction':
            # Points for reducing carbon impact
            points = int(amount * 5)  # 5 points per kg CO₂ reduced
        elif action_type == 'load_shift':
            # Points for shifting load to off-peak
            points = int(amount * 8)  # 8 points per kWh shifted
        
        return jsonify({
            'success': True,
            'points': points
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.context_processor
def inject_api_status():
    return dict(show_api_status=True)

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG) 