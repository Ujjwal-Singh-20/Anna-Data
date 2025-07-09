# Anna-Data: Annadata ke liye Anna-Data

Empowering Indian farmers with actionable, AI-powered agri-advisory and weather/market/pest alerts, accessible via SMS.
---
## About:
Anna-Data is a full stack, multilingual agri-advisory platform designed for Indian farmers("Annadata").

It provides:
- Personalized weather, market advice based on user's State,City,Commodities.
- It is also designed to provide scheduled alerts(pest and weather alerts) on specific intervals, if the user needs to be notified.
- All advice and alerts are AI powered. The AI is provided with required data, and is prompted with required knowledge to make a decision.
- Currently the project features a MOCKUP SMS UI.

### Why a Mockup SMS UI?
Due to the lack of a suitable, free SMS API with high message length limits and webhook support, a mockup frontend was built that simulates SMS delivery and user experience.
This allows to demonstrate the full advisory workflow and UI/UX, while keeping the project accessible and free for demo and hackathon use. 

Although a specific endpoint is present which sends a small message to the real(not made up) numbers present in DB, to show that the specific SMS functionality works, but that will only be used during demonstration to avoid maxing out the credits.
---
## Tech Stack:
- Backend: FastAPI(Python), MongoDB, Langgraph, Google Cloud Run(Deployment).
- Frontend: React, Tailwind CSS.
- LLM: meta/llama-4-scout-17b-16e-instruct model used by invoking NVIDIA chat completion url.
---
## Project Demo:
Frontend hosted at: https://anna-data-ghl33wm4x-ujjwal-singhs-projects-4476a310.vercel.app/

Backend hosted at: https://anna-data-452522242685.europe-west1.run.app

### Endpoints:
`/mockup-webhook`
- Made for the mockup SMS showcase
- Accepts POST request with JSON body { "phone": "...", "message": "..." }
- Returns message as JSON body { "advice": "...", "db_operations": "..." }

`/mockup-scheduled-run`
- Made for the mockup SMS scheduled run showcase
- Makes a GET request
- Simulate scheduled alerts, show what messages would be sent to which numbers(present in db). No real sms is sent.
- Returns a JSON body { "processed_users": int, "messages": "..." }

There are more endpoints, but the above specified endpoints will be used in frontend and during showcase.
---
## Screenshots:
You can just start with a "Hello", \
![Starting conversation](<Screenshot 2025-07-04 230827.png>)

Entering the required details, \
![Entering the required details](<Screenshot 2025-07-04 231321.png>)

Changing language with a simple message,(output comes out in desired language) \
![desired language output](<Screenshot 2025-07-04 231348.png>)

Changes reflected in MongoDB, \
![MongoDB](<Screenshot 2025-07-04 231508.png>)

Simulating scheduled-run, \
![scheduled-run](<Screenshot 2025-07-04 231442.png>)

---
## Setup and Installation:
Backend:
```
git clone https://github.com/yourusername/Anna-Data.git
cd Anna-Data/backend
pip install -r requirements.txt
python main.py
```

Frontend:
```
cd Anna-Data/frontend
npm install
npm run dev
```

- Set environment variables as described in .env.example (for API keys, DB, etc.). 
- Otherwise directly start using the frontend, as the backend hosted API url is already set in react.
---
## Acknowledgements:
- Code for Bharat season-2.
- NVIDIA, Google Cloud, WeatherAPI, eNAM, and all open data/API providers.
---
## Notes:
- SMS sending is simulated via the mockup UI due to API pricing constraints.
- All backend logic, database, and AI workflows are production-ready and can be connected to a real SMS gateway with minimal changes.
---
