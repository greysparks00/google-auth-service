from fastapi import FastAPI
from api.routes import router

app = FastAPI(
	title="Junction Google Auth",
	version="0.1.0"
)

# standard Junction service health endpoint
@app.get("/health", include_in_schema=False)
async def health():
	return {
		"status": "healthy"
	}

# register application endpoints
app.include_router(router)