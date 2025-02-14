import weaviate
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
import requests
import os

from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import HuggingFaceHub  # FIXED

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

class ResearchQuery(BaseModel):
    query: str

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
                  operator: Equal,
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
            properties={
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
        client.collections.get("Research").data.delete_by_id(uuid=object_id)
        return {"status": "Object deleted successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting object: {str(e)}")
    
llm = HuggingFaceHub(repo_id="deepseek-ai/DeepSeek-R1-Distill-Llama-70B", model_kwargs={"temperature": 0.5})

decomposition_template = """
You are an advanced research assistant. Your job is to break down a complex research question into four detailed sub-questions.

Research Query: {query}

Sub-questions:
1.
2.
3.
4.
"""
prompt_template = PromptTemplate(input_variables=["query"], template=decomposition_template)
decomposition_chain = LLMChain(llm=llm, prompt=prompt_template)

# Web Search Function (SearxNG)
def search_online(query: str) -> List[str]:
    try:
        response = requests.get(f"http://localhost:8888/search?q={query}&format=json")
        results = response.json()["results"]
        return [result["title"] + " - " + result["url"] for result in results[:3]]
    except Exception as e:
        return [f"Error retrieving search results: {str(e)}"]

# AI Research Orchestration Functions
def decompose_query(query: str) -> List[str]:
    result = decomposition_chain.run(query=query)
    sub_questions = [line.split(".", 1)[1].strip() for line in result.split("\n") if line.strip() and line[0].isdigit()]
    return sub_questions

def retrieve_data(sub_question: str) -> List[str]:
    web_results = search_online(sub_question)
    return web_results

def summarize_data(retrieved_data: List[str]) -> List[str]:
    return [f"Summary: {data}" for data in retrieved_data]

def synthesize_report(summaries: List[str]) -> str:
    return "Final Research Report:\n" + "\n".join(summaries)

@app.post("/research/")
def perform_research(research_query: ResearchQuery):
    try:
        sub_questions = decompose_query(research_query.query)
        retrieved = [retrieve_data(q) for q in sub_questions]
        summaries = summarize_data([item for sublist in retrieved for item in sublist])
        final_report = synthesize_report(summaries)

        return {
            "original_query": research_query.query,
            "sub_questions": sub_questions,
            "summaries": summaries,
            "final_report": final_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during research orchestration: {str(e)}")
