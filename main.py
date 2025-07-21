from fastapi import FastAPI, HTTPException, File, UploadFile, Response, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from pineconesoft import hmdceo
from googlenosoft import myGemini
import base64
import io
import datetime
import imghdr
from fastapi.staticfiles import StaticFiles
import os
import uuid


app = FastAPI(
    title="Org Chart Builder API",
    description="AI-powered organizational chart builder with RAG suggestions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001","http://localhost:3000", "http://127.0.0.1:3000", "https://org-chart-production.up.railway.app/", "https://org-chart-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize myGemini instance
gemini_ai = myGemini()

# Pydantic models
class NodeData(BaseModel):
    id: str
    # Node type: 'text' (default) or 'image'
    type: Optional[str] = "text"
    # For text nodes
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    position: Dict[str, float]
    # For image nodes
    src: Optional[str] = None  # data URI or URL
    title: Optional[str] = None
    description: Optional[str] = None
    # Optionally allow extra fields for compatibility
    class Config:
        extra = "allow"

class EdgeData(BaseModel):
    source: str
    target: str

class ChartData(BaseModel):
    nodes: List[NodeData]
    edges: List[EdgeData]

class ChangeData(BaseModel):
    employeeId: str
    action: str
    reason: str

class SuggestRequest(BaseModel):
    chart: ChartData

class SuggestResponse(BaseModel):
    modifiedChart: ChartData
    changes: List[ChangeData] = []

class AIGenerateRequest(BaseModel):
    mode: str  # 'text' or 'image_and_text'
    prompt: str
    image_data: Optional[str] = None  # base64 encoded image

class AIGenerateResponse(BaseModel):
    orgChart: ChartData

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return {"message": "Org Chart Builder API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "org-chart-builder"}

@app.post("/api/suggest", response_model=SuggestResponse)
async def suggest_changes(request: SuggestRequest):
    try:
        # Prepare chart JSON, including all node fields (text and image nodes)
        chart_json = json.dumps({
            "nodes": [node.dict() for node in request.chart.nodes],
            "edges": [edge.dict() for edge in request.chart.edges]
        }, indent=2)

        # Compose context for image nodes
        image_nodes = [n for n in request.chart.nodes if getattr(n, 'type', 'text') == 'image']
        image_context = ""
        if image_nodes:
            image_context = "\nThe org chart includes the following company logo/image nodes: "
            for img in image_nodes:
                image_context += f"\n- Title: {img.title or ''}, Description: {img.description or ''}"

        prompt = f"""
You are LegalSoft AI, an expert in virtual staffing and organizational design. Analyze the following org chart and recommend improvements, focusing on where LegalSoft virtual staff can replace or augment roles for greater efficiency, productivity, or cost savings.

Current org chart:
{chart_json}
Optional org data: 
{image_context}

Instructions:
- Use knowledge of Legalsoft and the organization structure and scale to suggest replacements or additions of virtual staff where appropriate.
- For each recommended replacement or new virtual staff member, include a clear, concise justification in natural language explaining why the change improves efficiency, productivity, or cost. Focus on LegalSoft's core strengths in virtual staffing.
- Return a JSON object with two keys:
  1. 'modifiedChart': the improved org chart (with 'nodes' and 'edges')
  2. 'changes': an array of objects, each with these keys: employeeId, action, reason,(in a pydandic dic) describing every replacement or addition and the reason for it.
- Use the same employeeId for any replaced or added node as in the chart, or a new unique id for new staff.
- Preserve any image/logo nodes (type: 'image') in the chart and do not remove or alter them unless explicitly instructed.
- Format your response as a clean JSON object, no extra text or explanation.
"""

        ai_raw_response = hmdceo.chat(prompt)
        if not ai_raw_response:
            raise HTTPException(status_code=500, detail="Failed to get AI response")
        try:
            ai_response = ai_raw_response.message.content 
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = ai_response[start_idx:end_idx]
                ai_json = json.loads(json_str)
                if 'modifiedChart' not in ai_json or 'changes' not in ai_json:
                    raise ValueError("AI response missing required keys.")
                # Validate chart
                chart = ai_json['modifiedChart']
                nodes = []
                for node in chart['nodes']:
                    # Validate image-node required fields
                    if node.get('type', 'text') == 'image':
                        if not node.get('src'):
                            raise ValueError(f"Image node {node.get('id')} missing 'src' field.")
                        if not node.get('position'):
                            raise ValueError(f"Image node {node.get('id')} missing 'position' field.")
                    nodes.append(NodeData(**node))
                edges = [EdgeData(**edge) for edge in chart['edges']]
                # Validate changes robustly
                changes = []
                for idx, chg in enumerate(ai_json['changes']):
                    if not isinstance(chg, dict):
                        print(f"Malformed change at index {idx}: not a dict: {chg}")
                        continue
                    missing = [k for k in ('employeeId', 'action', 'reason') if k not in chg]
                    if missing:
                        print(f"Malformed change at index {idx}: missing keys {missing}: {chg}")
                        continue
                    try:
                        changes.append(ChangeData(
                            employeeId=str(chg['employeeId']),
                            action=str(chg['action']),
                            reason=str(chg['reason'])
                        ))
                    except Exception as e:
                        print(f"Error constructing ChangeData at index {idx}: {e}, data: {chg}")
                return SuggestResponse(
                    modifiedChart=ChartData(nodes=nodes, edges=edges),
                    changes=changes
                )
            else:
                return SuggestResponse(modifiedChart=request.chart, changes=[])
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing AI response: {e}")
            print(f"AI Response: {ai_response}")
            return SuggestResponse(modifiedChart=request.chart, changes=[])
    except Exception as e:
        print(f"Error in suggest_changes: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/save")
async def save_org_chart(chart: ChartData):
    # Serialize chart to JSON (including image-nodes)
    chart_json = json.dumps(chart.dict(), indent=2)
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"orgchart_{timestamp}.json"
    # Create a streaming response for download
    return StreamingResponse(
        io.BytesIO(chart_json.encode("utf-8")),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@app.post("/api/load")
async def load_org_chart(file: UploadFile = File(None), json_data: Optional[Dict[str, Any]] = None):
    try:
        if file:
            # Read and parse uploaded file
            content = await file.read()
            data = json.loads(content)
        elif json_data:
            data = json_data
        else:
            raise HTTPException(status_code=400, detail="No file or JSON data provided.")
        # Validate with Pydantic (including image-nodes)
        chart = ChartData(**data)
        # Validate image-nodes
        for node in chart.nodes:
            if getattr(node, 'type', 'text') == 'image':
                if not getattr(node, 'src', None):
                    raise HTTPException(status_code=422, detail=f"Image node {node.id} missing 'src' field.")
                if not getattr(node, 'position', None):
                    raise HTTPException(status_code=422, detail=f"Image node {node.id} missing 'position' field.")
        return chart
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": f"Invalid org chart JSON: {str(e)}"}
        )

@app.post("/api/ai-generate-orgchart", response_model=AIGenerateResponse)
async def ai_generate_orgchart(request: AIGenerateRequest):
    try:
        user_prompt = request.prompt.strip()
        if not user_prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

        # If org chart is included, extract image-node context
        image_context = ""
        if hasattr(request, 'orgChart') and request.orgChart:
            image_nodes = [n for n in request.orgChart.nodes if getattr(n, 'type', 'text') == 'image']
            if image_nodes:
                image_context = "\nThe org chart includes the following company logo/image nodes: "
                for img in image_nodes:
                    image_context += f"\n- Title: {img.title or ''}, Description: {img.description or ''}"

        system_prompt = f'''
            You are LegalSoft AI, an expert in organizational design and virtual staffing. You can handle this type of request:

            1. **Org Chart Generation**: Create complete organizational charts from descriptions or images

            For **Org Chart Generation**, return a JSON object with this schema:
            {{
            "nodes": [
                {{
                "id": "string", // unique identifier
                "type": "text" or "image", // node type
                "src": "string", // for image nodes (data URI or URL)
                "title": "string", // for image nodes
                "description": "string", // for image nodes
                "name": "string", // for text nodes
                "role": "string", // for text nodes
                "department": "string", // for text nodes
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
            - If the org chart includes image/logo nodes (type: 'image'), preserve them and reference their title/description as company branding.
            - Return only a valid JSON object matching the appropriate schema, no extra text
            {image_context}

            User prompt : {user_prompt}
            '''
        
        if request.mode == "text":
            # Text-only mode using myGemini
            ai_response = await gemini_ai.chat(user_prompt)
            print(ai_response)
        elif request.mode == "image_and_text":
            # Image + text mode using myGemini
            if not request.image_data:
                raise HTTPException(status_code=400, detail="Image data is required for image_and_text mode.")
            try:
                image_bytes = base64.b64decode(request.image_data)
                #print(image_bytes)
                # Detect image type
                image_type = imghdr.what(None, h=image_bytes)
                mime_type = f"image/{image_type}"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
            ai_response = await gemini_ai.chat_image(user_prompt, image_bytes, mime_type)
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'text' or 'image_and_text'.")
        
        # Check for errors in AI response
        if isinstance(ai_response, str) and ai_response.startswith("Error:"):
            raise HTTPException(status_code=500, detail=ai_response)
        
        # Parse JSON from AI response
        try:
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = ai_response[start_idx:end_idx]
                ai_json = json.loads(json_str)
                # Validate chart (including image-nodes)
                nodes = []
                for node in ai_json['nodes']:
                    if node.get('type', 'text') == 'image':
                        if not node.get('src'):
                            raise ValueError(f"Image node {node.get('id')} missing 'src' field.")
                        if not node.get('position'):
                            raise ValueError(f"Image node {node.get('id')} missing 'position' field.")
                    nodes.append(NodeData(**node))
                chart = ChartData(nodes=nodes, edges=[EdgeData(**edge) for edge in ai_json['edges']])
                return AIGenerateResponse(orgChart=chart)
            else:
                raise ValueError("AI response did not contain a valid JSON object.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing AI response: {e}")
            print(f"AI Response: {ai_response}")
            raise HTTPException(status_code=500, detail="AI returned invalid org chart JSON.")
    except Exception as e:
        print(f"Error in ai_generate_orgchart: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only PNG, JPG, and SVG allowed.")
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB allowed.")
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.svg']:
        ext = '.png' if file.content_type == 'image/png' else '.jpg'
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    url = f"/uploads/{filename}"
    return {"id": unique_id, "url": url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 