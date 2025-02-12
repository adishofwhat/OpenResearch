import weaviate
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi import Query
import requests

app = FastAPI()

# Connect to Weaviate
client = weaviate.connect_to_local(
    host="weaviate",
    port=8080,
    grpc_port=50051
)

# Pydantic model for incoming data
class ResearchObject(BaseModel):
    name: str
    description: str
    tags: List[str] = []

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
def add_object(research_object: ResearchObject):
    data_object = {
        "name": research_object.name,
        "description": research_object.description,
        "tags": research_object.tags
    }

    try:
        client.collections.get("Research").data.insert(data_object)
        return {"status": "Object added successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding object: {str(e)}")

@app.get("/get-objects/")
def get_objects():
    try:
        objects = client.collections.get("Research").query.fetch_objects()
        return {"objects": objects.objects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching objects: {str(e)}")

@app.get("/search/")
def search_objects(name: str = Query(None), tag: str = Query(None)):
    try:
        if name:
            query_str = f"""
            {{
              Get {{
                Research(where: {{
                  operator: Equal,
                  path: ["name"],
                  valueText: "{name}"
                }}) {{
                  name
                  description
                  tags
                }}
              }}
            }}
            """
        elif tag:
            query_str = f"""
            {{
              Get {{
                Research(where: {{
                  operator: Contains,
                  path: ["tags"],
                  valueText: "{tag}"
                }}) {{
                  name
                  description
                  tags
                }}
              }}
            }}
            """
        else:
            raise HTTPException(status_code=400, detail="Provide either 'name' or 'tag' to search.")

        query = {"query": query_str}
        r = requests.post("http://weaviate:8080/v1/graphql", json=query)
        if r.status_code != 200:
            raise Exception(f"GraphQL query failed with status code {r.status_code}: {r.text}")

        response_json = r.json()
        if "data" not in response_json:
            raise Exception(f"GraphQL query returned no 'data' key: {response_json}")

        results = response_json["data"]["Get"]["Research"]
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching objects: {str(e)}")

@app.put("/update-object/{object_id}")
def update_object(object_id: str, updated_object: ResearchObject):
    try:
        client.collections.get("Research").data.update(
            uuid=object_id,
            data_object={
                "name": updated_object.name,
                "description": updated_object.description,
                "tags": updated_object.tags
            }
        )
        return {"status": "Object updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating object: {str(e)}")

# Delete object endpoint
@app.delete("/delete-object/{object_id}")
def delete_object(object_id: str):
    try:
        client.collections.get("Research").data.delete(uuid=object_id)
        return {"status": "Object deleted successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting object: {str(e)}")
