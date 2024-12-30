import asyncio
from src.generators.model_integration import ModelIntegration, GenerationContext
from src.core.base_models import ModelConfig

async def generate_fastapi_endpoint():
    """Example: Generate a FastAPI endpoint with database integration"""
    model = ModelIntegration()
    
    context = GenerationContext(
        language="python",
        framework="fastapi",
        component_type="endpoint",
        requirements={
            "method": "POST",
            "path": "/users",
            "database": True,
            "validation": True,
            "auth": True
        }
    )
    
    suggestions = await model.generate_code(context)
    if suggestions:
        print("Generated FastAPI Endpoint:")
        print(suggestions[0].code_snippet)
        print("\nExplanation:", suggestions[0].explanation)

async def enhance_existing_component():
    """Example: Enhance an existing component with async support"""
    model = ModelIntegration()
    
    existing_code = """
    class DataService:
        def __init__(self):
            self.db = Database()
            
        def get_data(self, query: str):
            return self.db.execute(query)
            
        def save_data(self, data: Dict[str, Any]):
            return self.db.insert(data)
    """
    
    context = GenerationContext(
        language="python",
        framework="asyncio",
        component_type="class",
        existing_code=existing_code,
        requirements={"async": True}
    )
    
    enhanced = await model.enhance_code(existing_code, context)
    print("Enhanced Component:")
    print(enhanced.code_snippet)
    print("\nChanges Explained:", enhanced.explanation)

async def generate_react_component():
    """Example: Generate a React component with TypeScript"""
    model = ModelIntegration()
    
    context = GenerationContext(
        language="typescript",
        framework="react",
        component_type="component",
        requirements={
            "name": "UserProfile",
            "props": {
                "user": "User",
                "onUpdate": "(user: User) => void"
            },
            "state": True,
            "styling": "styled-components"
        }
    )
    
    suggestions = await model.generate_code(context)
    if suggestions:
        print("Generated React Component:")
        print(suggestions[0].code_snippet)
        print("\nMetadata:", suggestions[0].metadata)

async def main():
    """Run all examples"""
    print("1. Generating FastAPI Endpoint...")
    await generate_fastapi_endpoint()
    
    print("\n2. Enhancing Existing Component...")
    await enhance_existing_component()
    
    print("\n3. Generating React Component...")
    await generate_react_component()

if __name__ == "__main__":
    asyncio.run(main()) 