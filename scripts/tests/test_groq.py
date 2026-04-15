import time
from app.core.config import settings
from app.core.llm import GroqClient

def test_groq():
    print(f"--- Groq Cloud Connectivity Test ---")
    print(f"Model: {settings.groq_model}")
    print(f"Provider: {settings.llm_provider}")
    
    client = GroqClient()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! Can you introduce yourself briefly and tell me a joke?"}
    ]
    
    print("\nSending request to Groq...")
    start_time = time.time()
    
    try:
        response = client.chat_completion(
            messages=messages,
            temperature=0.5
        )
        end_time = time.time()
        
        content = response.choices[0].message.content
        print(f"\nResponse Received in {end_time - start_time:.2f} seconds:")
        print("-" * 40)
        print(content)
        print("-" * 40)
        
        # Check token usage if available
        if hasattr(response, 'usage'):
            print(f"\nUsage Stats:")
            print(f"Prompt Tokens: {response.usage.prompt_tokens}")
            print(f"Completion Tokens: {response.usage.completion_tokens}")
            print(f"Total Tokens: {response.usage.total_tokens}")
            
    except Exception as e:
        print(f"\n❌ Error during Groq request: {e}")

if __name__ == "__main__":
    if not settings.groq_api_key:
        print("❌ GROQ_API_KEY is not set in .env")
    else:
        test_groq()
