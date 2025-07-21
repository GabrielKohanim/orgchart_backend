import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import asyncio


load_dotenv()

google_api_key = os.getenv('GOOGLE_API_KEY')

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

class myGemini:
    def __init__(self, system_instruction=None):
        self.system_instructions = system_instruction or (
            f'''
            You are LegalSoft AI, an expert in organizational design and virtual staffing. You can handle this type of request:

            **Org Chart Generation**: Create complete organizational charts from descriptions or images
    
            For **Org Chart Generation**, return a JSON object with this schema:
            {{
            "nodes": [
                {{
                "id": "string", // unique identifier
                "name": "string", // employee name
                "role": "string", // job title
                "department": "string", // department name
                "position": {{"x": number, "y": number}} // layout position
                }}
            ],
            "edges": [
                {{"source": "string", "target": "string"}} // reporting relationships
            ]
            }}


            Instructions:
            - Infer missing roles, hierarchy, or structure if the request is vague or incomplete
            - Use logical, realistic org chart structures
            - Assign unique IDs to each node
            - Assign reasonable x/y positions for layout (e.g., root at y=50, children at y=200, etc.)
            - For improvements, focus on LegalSoft's virtual staffing capabilities
            - Return only a valid JSON object matching the appropriate schema, no extra text
            - Do not assign random names when asked to make an org chart, however if there are names on an org chart image that is submitted include those 
            - If arrows or hierarchy are extremely ambigious for a position just create the nodes without edges 

            '''
        )

        self.client = genai.Client(api_key=google_api_key)

    async def chat(self, question):
        try:
            # Combine system instructions with user question
            full_prompt = f"{self.system_instructions}\n\nUser Request: {question}"
            
            response = await self.client.aio.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instructions
                )
            )
            return response.text
        except Exception as e:
            print(f"Error: {str(e)}")
            return f"Error: {str(e)}"
            
    async def chat_image(self, question, image, mime_type):
        try:
            # Create image part for multimodal input
            image_part = types.Part.from_bytes(data=image, mime_type=mime_type)
            text_part = types.Part.text =f"{self.system_instructions}\n\nUser Request: {question}"

            # Create the multimodal content
            content = [
                text_part,
                image_part
            ]
            
            # Generate content with image       
            response = await self.client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=content,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instructions
                )
            )
            
    
            return response.text
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return f"Error: {str(e)}"

    def test(self):
        """Test method to verify the AI connection"""
        try:
            response = self.client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents="Hello, this is a test message.",
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful assistant."
                )
            )
            return response
        except Exception as e:
            return f"Test Error: {str(e)}"

# Create a global instance for use in the application
#gemini_ai = myGemini()


#res = asyncio.run(gemini_ai.test())
#print(res)



