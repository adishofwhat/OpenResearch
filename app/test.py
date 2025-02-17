from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

def create_llm():
    try:
        # Load model and tokenizer
        model_name = "deepseek-ai/deepseek-coder-6.7b-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        
        # Create pipeline with imported pipeline function
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_length=2048,
            temperature=0.7,
        )
        
        return pipe

    except Exception as e:
        print(f"Error creating LLM: {str(e)}")
        return None

# Test the pipeline
try:
    llm = create_llm()
    if llm:
        response = llm("Write a simple function that adds two numbers")
        print(response)
except Exception as e:
    print(f"Error during testing: {str(e)}")