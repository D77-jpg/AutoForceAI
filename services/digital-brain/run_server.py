import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()
port = int(os.getenv("PORT", 8010))

if __name__ == "__main__":
    print(f"Starting server on port {port}...")
    # Using factory string is better for reload
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
