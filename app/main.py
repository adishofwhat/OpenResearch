from fastapi import FastAPI
import weaviate

app = FastAPI()

client = weaviate.Client("http://weaviate:8000")

@app.get("/")
def read_root():
    if client.is_ready():
        return {"status": "Deep Research System is running with Weaviate!"}
    else:
        return {"status": "Weaviate is not ready. Please check the connection."}
