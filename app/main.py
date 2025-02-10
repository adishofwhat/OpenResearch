import weaviate
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Connect to Weaviate
client = weaviate.connect_to_local(
    host="weaviate",
    port=8080,
    grpc_port=50051  # Default gRPC port if needed
)

@app.get("/")
def read_root():
    return {"status": "Deep Research System is running!"}

@app.get("/weaviate-status")
def weaviate_status():
    if client.is_ready():
        return {"weaviate": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Weaviate is not ready")

@app.post("/add-object/")
def add_object():
    data_object = {
        "name": "AI Research",
        "description": "Building an AI research system with open-source tools."
    }

    client.collections.get("Research").data.insert(data_object)
    return {"status": "Object added successfully!"}

@app.get("/get-objects/")
def get_objects():
    objects = client.collections.get("Research").query.fetch_objects()
    return {"objects": objects.objects}