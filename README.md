# ISO New England Energy Dashboard

A simple dashboard that displays real-time electricity prices and generation mix data from the ISO New England API.

## Quick Start

1. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your ISO-NE API credentials:
```bash
set ISO_USERNAME=your_username
set ISO_PASSWORD=your_password
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and visit: http://localhost:5000

The dashboard will show:
- Current electricity prices
- Real-time generation mix
- Carbon intensity calculations
- API status information 