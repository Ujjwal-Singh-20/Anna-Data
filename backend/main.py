from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Dict, List, Optional, Any, Literal
from dotenv import load_dotenv
load_dotenv()
import os
import requests
from datetime import datetime, timedelta
import json
import string
from pymongo import MongoClient
from fastapi import FastAPI, Request, Response, status
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from twilio.rest import Client
from fastapi.responses import JSONResponse
from googletrans import Translator
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_desired_language = None
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

client = MongoClient(MONGODB_CONNECTION_STRING)
db = client['AgriUserInfo']
farmers = db['Info']

class AdvisoryState(TypedDict):
    workflow_type: Literal["user", "scheduled_run"]
    user_number: str
    user_input: Optional[Dict[str, str]]
    api_data: Dict[str, Any]
    advice: List[str]
    alert_message: str
    emergency_flag: bool
    language: str

def market_price_api(state: AdvisoryState):
    """
    Fetches and parses commodity data for a given state from e-NAM
    Returns a list of dictionaries with parsed commodity details
    """
    State = None
    if state.get("user_state"):
        State = state["user_state"]
    else:
        # fallback: try to get from DB if needed
        user = farmers.find_one({'_id': state["user_number"]})
        State = user.get("state") if user else None

    if not State:
        updated_api_data = dict(state["api_data"])
        updated_api_data["market"] = "Please set your state, just type in 'state' and your state name."
        return {"api_data": updated_api_data}
        # return {"error": "State not provided"}
    
    url = 'https://enam.gov.in/web/Ajax_ctrl/commodity_list'
    
    headers = {
        'authority': 'enam.gov.in',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://enam.gov.in',
        'referer': 'https://enam.gov.in/web/dashboard/trade-data',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Microsoft Edge";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
        'x-requested-with': 'XMLHttpRequest'
    }
    
    today = datetime.now().strftime('%Y-%m-%d')
    data = {
        'language': 'en',
        'stateName': State,
        'apmcName': '-- Select APMCs --',
        'fromDate': today,
        'toDate': today
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        json_data = response.json()

        formatted_data = json_data          #format_for_whatsapp(json_data)

        updated_api_data = dict(state["api_data"])
        updated_api_data["market"] = formatted_data
        return {"api_data": updated_api_data}

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error occurred: {e}")
        return []

def format_for_whatsapp(commodity_data):
    messages = []
    messages.append("Data sourced from e-NAM (enam.gov.in), a Government of India initiative.\n")
    for item in commodity_data['data']:
        msg = (
            f"APMC: {item['apmc']}\n"
            f"Commodity: {item['commodity']}\n"
            f"Arrival/Traded: {item['commodity_traded']} {item['Commodity_Uom']}\n"
            f"Min Price: ₹{item['min_price']}\n"
            f"Modal Price: ₹{item['modal_price']}\n"
            f"Max Price: ₹{item['max_price']}"
        )
        messages.append(msg)
    return messages


def weather_data_api(state: AdvisoryState, days=3):
    city = None
    if state.get("user_location"):
        city = state["user_location"]
    else:
        # fallback: try to get from DB if needed
        user = farmers.find_one({'_id': state["user_number"]})
        city = user.get("city") if user else None

    if not city.strip():
        updated_api_data = dict(state["api_data"])
        updated_api_data["weather"] = "Please set your city, just type in 'city' and your city name."
        return {"api_data": updated_api_data}
        # return {"error": "City not provided"}
    
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days={days}&aqi=no&alerts=yes"
    response = requests.get(url)
    res = response.json()

    if response.status_code == 200:
        location = res.get('location', {})
        city = location.get('name', '')
        region = location.get('region', '')
        country = location.get('country', '')
        localtime = location.get('localtime', '')

        # Current weather info
        current = res.get('current', {})
        temp_c = current.get('temp_c', None)
        condition = current.get('condition', {}).get('text', '')
        humidity = current.get('humidity', None)
        precip_mm = current.get('precip_mm', None)
        wind_kph = current.get('wind_kph', None)

        # Forecast info (for each day)
        forecast_days = []
        for day in res.get('forecast', {}).get('forecastday', []):
            date = day.get('date', '')
            day_info = day.get('day', {})
            max_temp = day_info.get('maxtemp_c', None)
            min_temp = day_info.get('mintemp_c', None)
            avg_temp = day_info.get('avgtemp_c', None)
            total_rain = day_info.get('totalprecip_mm', None)
            daily_condition = day_info.get('condition', {}).get('text', '')
            chance_of_rain = day_info.get('daily_chance_of_rain', None)

            forecast_days.append({
                'date': date,
                'max_temp_c': max_temp,
                'min_temp_c': min_temp,
                'avg_temp_c': avg_temp,
                'total_precip_mm': total_rain,
                'condition': daily_condition,
                'chance_of_rain': chance_of_rain
            })

        alerts = []
        if 'alerts' in res and 'alert' in res['alerts']:
            for alert in res['alerts']['alert']:
                alerts.append(alert.get('headline', ''))

        data = {
            'location': {
            'city': city,
            'region': region,
            'country': country,
            'localtime': localtime
            },
            'current_weather': {
            'temp_c': temp_c,
            'condition': condition,
            'humidity': humidity,
            'precip_mm': precip_mm,
            'wind_kph': wind_kph
            },
            'forecast': forecast_days,
            'alerts': alerts
        }

        # state["api_data"]["weather"] = data
        
        # return {"api_data": {"weather": data}}
        updated_api_data = dict(state["api_data"])
        updated_api_data["weather"] = data
        return {"api_data": updated_api_data}
    
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def pest_alert_api(state: AdvisoryState, days=7):
    """
    Fetches and parses weather data for pest risk analysis
    Returns structured data for last 7 days, or None on error
    """
    city = None
    if state.get("user_location"):
        city = state["user_location"]
    else:
        # fallback: try to get from DB if needed
        user = farmers.find_one({'_id': state["user_number"]})
        city = user.get("city") if user else None

    if not city.strip():
        updated_api_data = dict(state["api_data"])
        updated_api_data["pest_alert"] = "Please set your city, just type in 'city' and your city name."
        return {"api_data": updated_api_data}
        # return {"error": "City not provided"}
    
    api_key = os.getenv("WORLD_WEATHER_ONLINE_API")
    if not api_key:
        return None

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days-1)
    url = f"https://api.worldweatheronline.com/premium/v1/past-weather.ashx?key={api_key}&q={city}&date={start_date.strftime('%Y-%m-%d')}&enddate={end_date.strftime('%Y-%m-%d')}&format=json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
    except requests.exceptions.RequestException:
        return None

    if not weather_data or "data" not in weather_data or "weather" not in weather_data["data"]:
        return None

    parsed_data = []
    for day in weather_data["data"]["weather"]:
        # Basic daily metrics
        date = day["date"]
        max_temp = float(day["maxtempC"])
        min_temp = float(day["mintempC"])
        avg_temp = float(day["avgtempC"])
        
        hourly = day["hourly"]
        precip_mm = sum(float(h["precipMM"]) for h in hourly)
        humidities = [float(h["humidity"]) for h in hourly]
        avg_humidity = sum(humidities) / len(humidities) if humidities else 0
        wind_speeds = [float(h["windspeedKmph"]) for h in hourly]
        max_wind = max(wind_speeds) if wind_speeds else 0
        rain_hours = sum(1 for h in hourly if float(h["precipMM"]) > 0)
        high_humidity_hours = sum(1 for h in hourly if float(h["humidity"]) > 70)

        parsed_data.append({
            "date": date,
            "max_temp_c": max_temp,
            "min_temp_c": min_temp,
            "avg_temp_c": avg_temp,
            "total_precip_mm": precip_mm,
            "avg_humidity": avg_humidity,
            "max_wind_kph": max_wind,
            "rain_hours": rain_hours,
            "high_humidity_hours": high_humidity_hours
        })

    weather_str = json.dumps(parsed_data, indent=2)

    prompt = f"""
                Analyze this weather data for pest risk in crops:
                {weather_str}

                Consider:
                **Temperature Analysis:**
                1. Check if daily average temperature falls in 20-30°C range (ideal for pest activity)
                2. Identify consecutive days with optimal temperatures (accelerates pest reproduction)
                3. Note temperature fluctuations >5°C/day (stresses crops, increases vulnerability)

                **Humidity Analysis:**
                4. Days with average humidity >70% (promotes fungal growth)
                5. Hours with humidity >80% (high risk for disease development)
                6. Consecutive high-humidity days (compounding disease risk)

                **Precipitation Analysis:**
                7. Days with >5mm rainfall (creates pest breeding sites)
                8. >3 consecutive rainy days (sustained breeding conditions)
                9. Rainy hours during warm periods (ideal for pest emergence)

                **Wind Analysis:**
                10. Days with max wind >15km/h (spreads pests/spores)
                11. Windy days following rainy periods (disperses water-borne pathogens)

                **Temporal Patterns:**
                12. 3+ consecutive days with:
                    - Temp 20-30°C + humidity >70%
                    - Temp 20-30°C + rain >2mm
                13. Increasing humidity trend over 48 hours
                14. Temperature-humidity co-occurrence during crop flowering stage

                **Threshold Triggers:**
                15. Immediate alert if:
                    - Day with >8 rainy hours + temp >25°C
                    - 2+ days with humidity >85%
                    - Day with >10mm rain + avg temp >22°C
                16. Moderate alert if:
                    - 3+ days with 4+ high-humidity hours
                    - Steady temp 24-28°C with intermittent rain

                **Output Requirements:**
                - Return valid JSON format(nothing else): 
                {{
                "pest_alert_level": "none|low|medium|high",
                "primary_risk_factors": ["list", "of", "top", "factors"],
                "recommended_actions": ["action1", "action2"]
                }}
                
            """
    
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
        "Accept": "application/json"
    }
    
    payload = {
        "model": "meta/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,       #more deterministic output
        "top_p": 0.9,
        "response_format": {"type": "json_object"}  # Ensure JSON output
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        result = response.json()
        
        # Extract JSON content from response
        content = result['choices'][0]['message']['content']
        pest_alert = json.loads(content)
        # state["api_data"]["pest_alert"] = pest_alert
        
        # return {"api_data": {"pest_alert": pest_alert}}

        updated_api_data = dict(state["api_data"])
        updated_api_data["pest_alert"] = pest_alert
        return {"api_data": updated_api_data}
        
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"API Error: {e}")
        return {"error": "Prediction failed"}
    

def weather_alert_api(state:AdvisoryState, days=2):
    city = None
    if state.get("user_input") and state["user_input"].get("location"):
        city = state["user_input"]["location"]
    elif state.get("user_location"):
        city = state["user_location"]
    else:
        # fallback: try to get from DB if needed
        user = farmers.find_one({'_id': state["user_number"]})
        city = user.get("city") if user else None

    if not city.strip():
        updated_api_data = dict(state["api_data"])
        updated_api_data["weather_alert"] = "Please set your city, just type in 'city' and your city name."
        return {"api_data": updated_api_data}
        # return {"error": "City not provided"}
    
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        print("Error: WEATHER_API_KEY environment variable not set")
        return None

    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days={days}&aqi=no&alerts=yes"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        res = response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None

    # Parse location
    location_data = res.get('location', {})
    location = {
        'city': location_data.get('name', ''),
        'region': location_data.get('region', ''),
        'country': location_data.get('country', ''),
        'localtime': location_data.get('localtime', '')
    }

    # Parse current weather
    current_data = res.get('current', {})
    current_weather = {
        'temp_c': current_data.get('temp_c'),
        'condition': current_data.get('condition', {}).get('text', ''),
        'humidity': current_data.get('humidity'),
        'precip_mm': current_data.get('precip_mm'),
        'wind_kph': current_data.get('wind_kph'),
        'feelslike_c': current_data.get('feelslike_c'),
        'uv': current_data.get('uv')
    }

    # Parse daily forecast
    forecast_days = []
    for day in res.get('forecast', {}).get('forecastday', []):
        day_info = day.get('day', {})
        forecast_days.append({
            'date': day.get('date', ''),
            'max_temp_c': day_info.get('maxtemp_c'),
            'min_temp_c': day_info.get('mintemp_c'),
            'avg_temp_c': day_info.get('avgtemp_c'),
            'total_precip_mm': day_info.get('totalprecip_mm'),
            'condition': day_info.get('condition', {}).get('text', ''),
            'chance_of_rain': day_info.get('daily_chance_of_rain'),
            'uv': day_info.get('uv')
        })

    # Parse hourly forecast
    hourly_forecast = []
    for day in res.get('forecast', {}).get('forecastday', []):
        for hour in day.get('hour', []):
            hourly_forecast.append({
                'time': hour.get('time', ''),
                'temp_c': hour.get('temp_c'),
                'condition': hour.get('condition', {}).get('text', ''),
                'humidity': hour.get('humidity'),
                'precip_mm': hour.get('precip_mm'),
                'wind_kph': hour.get('wind_kph'),
                'chance_of_rain': hour.get('chance_of_rain'),
                'feelslike_c': hour.get('feelslike_c'),
                'uv': hour.get('uv')
            })

    # Parse alerts
    alerts = [alert.get('headline', '') for alert in res.get('alerts', {}).get('alert', [])]

    weather_str =  {
        'location': location,
        'current_weather': current_weather,
        'daily_forecast': forecast_days,
        'hourly_forecast': hourly_forecast,
        'alerts': alerts
    }

    prompt = f"""
            **Role**: Agricultural Weather Alert Analyst
            **Task**: Analyze hourly forecast for severe weather risks and generate alerts

            **Hourly Weather Data**:
            {weather_str}

            **Critical Alert Thresholds**:
            1. **Heavy Rain**:
            - >10mm/h → Flood risk
            - >20mm in 3h → Field inundation
            - >8 rainy hours/day → Saturated soil

            2. **Wind Damage**:
            - Sustained >30km/h → Crop lodging
            - Gusts >45km/h → Physical damage

            3. **Temperature Extremes**:
            - >40°C → Heat stress
            - <5°C → Frost risk (for sensitive crops)

            4. **Humidity Risks**:
            - >90% for 6+ consecutive hours → Fungal explosion
            - <30% + high winds → Desiccation

            5. **Compound Risks**:
            - Rain + wind → Erosion
            - High temp + high humidity → Heat index >45°C

            **Output Requirements**:
            - Return **strictly as JSON**:
            {{
            "weather_alert_level": "none|low|medium|high",
            "immediate_risks": ["top_3_risks"],
            "time_bound_actions": [
                "time_window": "0-6h", "action": "step1",
                "time_window": "6-24h", "action": "step2"
            ]
            }}
            - Prioritize risks occurring within next 12h
            - Recommend time-bound actions for farmers
            - Use 24-hour clock (IST) in responses
            - Never include explanations or markdown
            """
    
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
        "Accept": "application/json"
    }

    payload = {
        "model": "meta/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        result = response.json()
        
        # Extract JSON content from response
        content = result['choices'][0]['message']['content']
        # Parse the JSON content and add to state["api_data"]["weather_alert"]
        weather_alert = json.loads(content)
        # state["api_data"]["weather_alert"] = weather_alert
        
        # return {"api_data": {"weather_alert": weather_alert}}
        updated_api_data = dict(state["api_data"])
        updated_api_data["weather_alert"] =weather_alert
        return {"api_data": updated_api_data}
        
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"API Error: {e}")
        return {"error": "Prediction failed"}


async def advisory(state: AdvisoryState):
    """
    Generates detailed LLM-powered advisories for user requests,
    passes through preformatted alerts for scheduled runs
    """
    city = None
    commodity = None
    
    if state.get("user_location") and state.get("user_commodities"):
        city = state["user_location"]
        commodity = state.get("user_commodities")
    else:
        # fallback: try to get from DB if needed
        user = farmers.find_one({'_id': state["user_number"]})
        city = user.get("city") if user else None
        commodity = user.get("commodities") if user else None

    if (not city.strip()) or (not commodity):
        advice = "Please set your city(if not set) and what agricultural commodities you have(if not set), just type in 'city' and your city name or 'commodities' and your commodities seperated by ','."
        return {"advice": advice}
        # return {"error": "City/Commodity not provided"}
    
    if state["workflow_type"] == "user":
        # Extract data for user advisory
        weather = state["api_data"].get("weather")
        market = state["api_data"].get("market")
        
        prompt = f"""
        **Role**: Agricultural Advisory Expert
        **Task**: Create comprehensive farming advice for {city} ({commodity}), give answer in first person

        **Input Data**:
        Weather data: {weather},
        Market data: {market}

        **Output Requirements**:
        1. **Structure**:
        - Use markdown sections with emojis
        - Maintain this format:
            ```
            🌦️ Weather Advisory: 
                ...(support your answer with facts from given weather data)

            💰 Market Strategy: 
                ...(mention the site which is being used, and share the trends or any sharp trend)

            🌱 Cultivation Tips: 
                ...(if required)

            🛡️ Preventive Measures: 
                ...(based on weather data)
            ```
            

        2. **Detail Requirements**:
        - For every recommendation:
            * Reference specific data points (e.g., "Based on tomorrow's 85% humidity forecast...")
            * Include scientific rationale (e.g., "High humidity promotes fungal spores germination")
            * Add implementation tips (e.g., "Apply before 10 AM when temperatures are below 30°C")
        - Explain consequences of inaction (e.g., "Delaying harvest risks 20% yield loss due to forecasted rain")
        - Compare alternatives where applicable (e.g., "Neem oil vs. chemical fungicide: lower efficacy but organic")

        3. **Supporting Evidence**:
        - Cite thresholds used (e.g., "Threshold: >80% humidity for 4+ hours triggers fungal risk")
        - Reference agricultural best practices (e.g., "Per ICAR guidelines for {commodity}...")
        - Include localized knowledge (e.g., "Common in {city} during monsoon")

        RETURN ONLY NECESSARY INFO IN concise manner
        """
        
        
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
            "Accept": "application/json"
        }
        
        payload = {
            "model": "meta/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.7,        # more deterministic output
            "top_p": 0.9,
            "response_format": {"type": "json_object"}  # Ensure JSON output
        }

        try:
            response = requests.post(invoke_url, headers=headers, json=payload, timeout=40)
            response.raise_for_status()
            result = response.json()
            
            # Extract JSON content from response
            content = result['choices'][0]['message']['content']
            advisory_text = json.loads(content)
            
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"API Error: {e}")
            advisory_text = {"error": "Prediction failed"}

        # state["advice"] = [advisory_text]

        formatted_text = ""
        desired_language = user.get("last_message_language")
        if (desired_language=="en"):
            for key, value in advisory_text.items():
                if isinstance(value, str):
                    clean_value = value.replace(", ", "\n")
                else:
                    clean_value = str(value)
                formatted_text += f"{key}:\n{clean_value}\n\n"
        else:
            formatted_text = await multilingual_output(advisory_text, desired_language)
        
        # state["advice"] = [formatted_text]
        advice = formatted_text if isinstance(formatted_text, str) else formatted_text.get("advice", [""])[0]  # Extract first string from advice list

        
    else:
        # Scheduled alert path
        alert_data = state["api_data"].get("alert", {})
        # state["advice"] = [json.dumps(alert_data, indent=2)]
        advice = [json.dumps(alert_data, indent=2)]
    
    return {"advice": advice}              #state["advice"]}


# def multilingual_output(text, desired_language = "en"):
    
#     url = "https://translate-pa.googleapis.com/v1/translateHtml"
#     headers = {
#         "Content-Type": "application/json+protobuf",
#         "X-Goog-API-Key": "AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520"
#     }
#     payload = [[[f"{text}"], "auto", f"{desired_language}" ], "wt_lib"]

#     response = requests.post(url, headers=headers, json=payload)

#     if response.status_code == 200:
#         translated_text = response.json()[0][0]
#         # Removing non alphanumeric chars only from start and end
#         clean_text = translated_text.strip(string.punctuation + string.whitespace)

#         # global user_desired_language
#         # if user_desired_language is None:
#         user_desired_language = response.json()[1][0]
        
#         # return clean_text, user_desired_language
#         return {"advice": [clean_text], "language": user_desired_language}

#     else:
#         return (f"Error: {response.status_code} - {response.text}"), ""

async def multilingual_output(text, desired_language="en"):
    """
    Asynchronously translate text to the desired language using py-googletrans.
    Returns: {"advice": [translated_text], "language": detected_source_lang}
    """
    try:
        async with Translator() as translator:
            translation = await translator.translate(text, dest=desired_language)
            translated_text = translation.text
            # Remove non-alphanumeric chars only from start and end
            clean_text = translated_text.strip(string.punctuation + string.whitespace)
            detected_language = translation.src  # Detected source language
            return {"advice": [clean_text], "language": detected_language}
    except Exception as e:
        return {"advice": [f"Error: {str(e)}"], "language": desired_language}



def fetch_all_users():
    """Retrieve all users from MongoDB"""
    return list(farmers.find({}))


def invoke_nvidia_llm(prompt: str) -> dict:
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }
    
    payload = {
        "model": "meta/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        result = response.json()
        
        # Extract and parse JSON content
        content = result['choices'][0]['message']['content']
        return json.loads(content)
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"API Error: {e}")
        return {"error": "LLM processing failed"}


def llm_command_generator(english_input: str, phone: str) -> Dict[str, Any]:
    """Generates DB commands using NVIDIA API"""
    prompt = f"""
    Convert this user command into JSON for MongoDB operations:(if command does not require MongoDB database update, set operation as none)
    {{
        "operation": "insert|update|delete|none",
        "_id": "{phone}",
        "name": "value", 
        "city": "value", 
        "state": "value",
        "commodities": {{
            "add": ["item1", "item2"],
            "remove": ["item3"]
        }}
        "last_message_language": "value"    (dont update unless a language is mentioned in User command)(also use "en" in place of "english", and "hi" in place of "hindi" and as such)
    }}
    
    User command: {english_input}
    
    Important:
    - Return only valid JSON
    - Use null for missing fields, but always keep the _id non-null
    - if state is set, always capitalize it, for example WEST BENGAL, HARYANA, ODISHA ...
    - Keep arrays empty if no items
    """
    return invoke_nvidia_llm(prompt)

def execute_mongodb_command(command: Dict[str, Any], phone, received_msg_lang):
    if "error" in command:
        raise ValueError(f"Invalid command: {command['error']}")
    
    # phone = command['_id']

    if not farmers.find_one({'_id': phone}):
        # Insert a new document with only _id and empty fields
        farmers.insert_one({
            '_id': phone,
            'name': '',
            'city': '',
            'state': '',
            'commodities': [],
            'last_message_language': received_msg_lang
        }) 

    
    if command['operation'] == 'insert':
        document = {
            '_id': phone,
            'name': command.get('name', ''),
            'city': command.get('city', ''),
            'state': command.get('state', ''),
            'commodities': command.get('commodities', {}).get('add', []),
            'last_message_language': received_msg_lang
        }
        farmers.insert_one(document)
    
    elif command['operation'] == 'update':
        # Field updates
        update_data = {k: v for k in ['name', 'city', 'state'] if (v := command.get(k)) is not None}
        
        #language update
        if 'last_message_language' in command:
            update_data["last_message_language"] = command.get("last_message_language", "en")
        
        # Commodity operations
        if 'commodities' in command:
            if add_items := command['commodities'].get('add'):
                farmers.update_one(
                    {'_id': phone},
                    {'$addToSet': {'commodities': {'$each': add_items}}}
                )
            if remove_items := command['commodities'].get('remove'):
                farmers.update_one(
                    {'_id': phone},
                    {'$pull': {'commodities': {'$in': remove_items}}}
                )
        
        # Update other fields
        if update_data:
            farmers.update_one({'_id': phone}, {'$set': update_data})
    
    elif command['operation'] == 'delete':
        farmers.delete_one({'_id': phone})

    elif command['operation'] == 'none':
        pass

async def process_user_request(user_input: str, phone: str, language: str = "en"):
    """end to end, request processing"""
    translation_result = await multilingual_output(user_input)
    english_input = translation_result["advice"][0]
    received_message_language = translation_result["language"]
    
    command = llm_command_generator(english_input, phone)
    
    execute_mongodb_command(command, phone, received_msg_lang=received_message_language)
    return {"status": "success", "operation": command.get('operation')}




def db_operation_node(state: AdvisoryState):
    if state["workflow_type"] == "user":
        process_user_request(
            user_input = state["user_input"],
            phone = state["user_number"]
        )
    return state



#Building the graph

builder = StateGraph(AdvisoryState)

builder.add_node("weather_api_node", weather_data_api)
builder.add_node("market_api_node", market_price_api)
builder.add_node("pest_alert_node", pest_alert_api)
builder.add_node("weather_alert_node", weather_alert_api)
# builder.add_node("alert_api_node", weather_alert_api)
builder.add_node("advisory_node", advisory)
builder.add_node("multilingual_output_node", multilingual_output)

# Conditional routing after weather_api_node
def route_after_weather(state: AdvisoryState) -> str:
    if (state["workflow_type"] == "user"):
        return "weather_api_node"
    else:
        return "pest_alert_node"

builder.add_conditional_edges(
    START,
    route_after_weather,
    {
        "weather_api_node": "weather_api_node",
        "pest_alert_node": "pest_alert_node"
    }
)

# user advisory path
builder.add_edge("weather_api_node", "market_api_node")
builder.add_edge("market_api_node", "advisory_node")
builder.add_edge("advisory_node", "multilingual_output_node")

# scheduled run path
builder.add_edge("pest_alert_node", "weather_alert_node")
builder.add_edge("weather_alert_node", "multilingual_output_node")

# Common output
builder.add_edge("multilingual_output_node", END)


graph = builder.compile()



def send_whatsapp_message(phone: str, message: str):
    """Send message via WhatsApp API"""
    url = "https://graph.facebook.com/v22.0/746570235196802/messages"  # Your WhatsApp number ID
    headers = {
        "Authorization": f"Bearer {os.environ['WHATSAPP_API_TOKEN']}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=payload)



def send_sms_message(phone: str, message: str):
    """
    Send an SMS via Twilio API.
    """
    # Load credentials from environment variables
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")  # Your Twilio number

    if not all([account_sid, auth_token, from_number]):
        raise ValueError("Twilio credentials are not set in environment variables.")

    client = Client(account_sid, auth_token)
    msg = client.messages.create(
        body="This is a sample response for your pest/weather ALERT",        #message,
        from_=from_number,
        to=phone
    )
    # print(f"Twilio SMS sent: SID={msg.sid}, Body={msg.body}")
    return msg.sid


async def summarize_alerts_and_notify(state, pest_alert, weather_alert, lang="en"):
    prompt = f"""
                You are an agricultural advisory assistant. Summarize the following pest and weather alerts for a farmer in a clear, actionable, and concise WhatsApp message. Use bullet points, emojis, and simple language. If both alerts are 'none', say 'No urgent alerts today.'

                ---
                Pest Alert:
                {json.dumps(pest_alert, indent=2)}

                Weather Alert:
                {json.dumps(weather_alert, indent=2)}
                ---

                Format:
                - summarize the risks and recommended actions for each (pest first, then weather).
                - Return only the summary message as a JSON object: {{"alert_message": "..."}}
            """
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
        "Accept": "application/json"
    }
    payload = {
        "model": "meta/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        advisory = json.loads(content)
        alert_message = advisory.get('alert_message', '')
        # Optionally translate
        # if user_desired_language != "en":
        alert_message_final = await multilingual_output(alert_message, lang)

        # state["alert_message"] = alert_message_final
        # return state
        return alert_message_final.get("advice", [""])[0]  # Extract first string from advice list
    

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"API Error: {e}")
        return "Prediction failed"



VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secret_token")
# Specifying api endpoints
@app.get("/whatsapp-webhook")
async def verify_webhook(request: Request):
    """
    WhatsApp/Facebook webhook verification endpoint.
    Responds to GET with the challenge if the verify token matches.
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Verification failed", status_code=status.HTTP_403_FORBIDDEN)

@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages"""
    data = await request.json()
    phone = data['entry'][0]['changes'][0]['value']['messages'][0]['from']
    message = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
    
    # Process user request
    result = await process_user_request(message, phone)      #, language="hi")  # Auto-detect language
    
    # Generate advisory
    state = AdvisoryState(
        workflow_type="user",
        user_input={"text": message, "phone": phone},
        user_number= str(phone),
        api_data={},
        advice=[],
        alert_message="",
        emergency_flag=False
    )
    advisory_state = await graph.ainvoke(state)
    
    # Send response
    # send_whatsapp_message(phone, advisory_state["advice"][0] if advisory_state["advice"] else "")   #advisory_state["advice"])
    send_sms_message(phone, advisory_state["advice"][0] if advisory_state["advice"] else "")
    return {"status": "success", "db_operations": result}


#--------------------------------------------ENDPOINTS FOR MOCKUP WEBPAGE-------------------------------------------------------------------

@app.post("/mockup-webhook")
async def mockup_webhook(request: Request):
    """
    Response for the mockup site (POST).
    Expects JSON body: { "phone": "...", "message": "..." }
    """
    data = await request.json()
    phone = data.get("phone")
    message = data.get("message")

    if not phone or not message:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing 'phone' or 'message' in request body"}
        )

    # Process user request (DB, etc.)
    result = await process_user_request(message, phone)

    # Generate advisory (same as whatsapp_webhook)
    state = AdvisoryState(
        workflow_type="user",
        user_input=message,
        user_number=str(phone),
        api_data={},
        advice=[],
        alert_message="",
        emergency_flag=False,
        language="en"
    )
    # advisory_state = graph.invoke(state)
    advisory_state = await graph.ainvoke(state)


    # Prepare advice text (always a list)
    advice_text = advisory_state.get("advice", [""])[0] if advisory_state.get("advice") else ""

    # return JSONResponse(content={
    #     "advice": advice_text,
    #     "db_operations": result
    # })
    return {
        "advice": advice_text,
        "db_operations": result
    }

@app.get("/mockup-scheduled-run")
async def mockup_scheduled_run():
    """
    Simulate scheduled alerts, show what messages would be sent to which numbers(present in db).
    No real sms or WhatsApp is sent.
    """
    users = farmers.find({})
    processed = 0
    sent_messages = []  # Collect all "sent" messages here

    for user in users:
        state = AdvisoryState(
            workflow_type="scheduled_run",
            user_number=user["_id"],
            user_input=None,
            api_data={},
            advice=[],
            alert_message="",
            emergency_flag=True,
            language=user.get("last_message_language", "en")
        )
        result = await graph.ainvoke({
            **state,
            "user_location": user.get("city"),
            "user_commodities": user.get("commodities"),
            "user_state": user.get("state")
        })

        pest_alert = result["api_data"].get("pest_alert", {})
        weather_alert = result["api_data"].get("weather_alert", {})

        if isinstance(pest_alert, dict):
            pest_level = pest_alert.get("pest_alert_level", "none").lower()
        elif isinstance(pest_alert, str):
            pest_level = pest_alert.lower()

        if isinstance(weather_alert, dict):
            weather_level = weather_alert.get("weather_alert_level", "none").lower()
        elif isinstance(weather_alert, str):
            weather_level = weather_alert.lower()
        

        if isinstance(pest_alert, str) and isinstance(weather_alert, str):
            message = "Please set your city, just type in 'city' and your city name."
            sent_messages.append({
                "to": user["_id"],
                "message": message
            })
            processed += 1
        elif pest_level != "none" or weather_level != "none":
            state_with_alert_message = await summarize_alerts_and_notify(
                state, pest_alert, weather_alert, user.get("last_message_language", "en")
            )
            sent_messages.append({
                "to": user["_id"],
                "message": state_with_alert_message
            })
            processed += 1

    return {
        "processed_users": processed,
        "messages": sent_messages
    }


#------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/scheduled-run")
async def scheduled_run():
    """Trigger scheduled alerts"""
    users = farmers.find({})
    processed = 0
    for user in users:
        state = AdvisoryState(
            workflow_type="scheduled_run",
            user_number= user["_id"],
            user_input=None,
            api_data={},
            advice=[],
            alert_message="",
            emergency_flag=True,
            language= user["last_message_language"]
        )
        result = await graph.ainvoke({
            **state,
            "user_location": user["city"],
            "user_commodities": user["commodities"],
            "user_state": user["state"]
        })

        # Fetch alert levels from both pest and weather alert
        pest_alert = result["api_data"].get("pest_alert", {})
        weather_alert = result["api_data"].get("weather_alert", {})

        if isinstance(pest_alert, dict):
            pest_level = pest_alert.get("pest_alert_level", "none").lower()
        elif isinstance(pest_alert, str):
            pest_level = pest_alert.lower()

        if isinstance(weather_alert, dict):
            weather_level = weather_alert.get("weather_alert_level", "none").lower()
        elif isinstance(weather_alert, str):
            weather_level = weather_alert.lower()
        
        
        if isinstance(pest_alert, str) and isinstance(weather_alert, str):         # if both alerts are raw strings
            message = "Please set your city, just type in 'city' and your city name."
            # send_whatsapp_message(user["_id"], message)
            send_sms_message(user["_id"], message)
            processed += 1
        elif pest_level != "none" or weather_level != "none":
            state_with_alert_message = summarize_alerts_and_notify(state, pest_alert, weather_alert, user["last_message_language"])#result["language"])
            # send_whatsapp_message(user["_id"], state_with_alert_message)
            send_sms_message(user["_id"], state_with_alert_message)
            processed += 1

    return {"processed_users": processed}



if __name__=="__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)