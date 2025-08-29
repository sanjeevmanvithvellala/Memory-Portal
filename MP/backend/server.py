from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import httpx
import json
import asyncio
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Memory Portal API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str  # "text", "photo", "audio"
    content: str  # text content or file path/base64
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MemoryCreate(BaseModel):
    user_id: str
    type: str
    content: str
    description: Optional[str] = None

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    message: str
    is_user: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessageCreate(BaseModel):
    user_id: str
    message: str

class AvatarVideo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    talk_id: str
    status: str
    result_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AvatarVideoCreate(BaseModel):
    user_id: str
    image_url: str
    text: str

class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    avatar_image_url: Optional[str] = None
    personality_traits: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserProfileCreate(BaseModel):
    name: str
    avatar_image_url: Optional[str] = None
    personality_traits: Optional[str] = None

# D-ID API Client
class DIDClient:
    def __init__(self):
        self.api_key = os.environ.get('DID_API_KEY')
        self.base_url = "https://api.d-id.com"
        
    async def create_talk(self, image_url: str, text: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "script": {
                "type": "text",
                "input": text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": "en-US-JennyNeural"
                }
            },
            "source_url": image_url,
            "config": {
                "fluent": False,
                "pad_audio": 0.0
            }
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.base_url}/talks", json=payload, headers=headers)
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"D-ID API error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to create avatar video")
    
    async def get_talk_status(self, talk_id: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base_url}/talks/{talk_id}", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to get avatar status")

# Initialize clients
did_client = DIDClient()

# Helper functions
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

async def get_memories_context(user_id: str) -> str:
    """Get memories for context in AI conversations"""
    memories = await db.memories.find({"user_id": user_id}).to_list(length=50)
    
    context = "Here are the memories about this person:\n\n"
    for memory in memories:
        memory_type = memory.get('type', 'unknown')
        content = memory.get('content', '')
        description = memory.get('description', '')
        
        if memory_type == 'text':
            context += f"Memory: {content}\n"
        elif memory_type == 'photo':
            context += f"Photo memory: {description if description else 'A cherished photo'}\n"
        elif memory_type == 'audio':
            context += f"Audio memory: {description if description else 'A recorded voice message'}\n"
        
        context += f"Created: {memory.get('created_at', '')}\n\n"
    
    return context

async def generate_ai_response(user_message: str, user_id: str) -> str:
    """Generate AI response using GPT-5 with memory context"""
    try:
        # Get user profile
        profile = await db.user_profiles.find_one({"id": user_id})
        
        # Get memories context
        memories_context = await get_memories_context(user_id)
        
        # Create system message with personality and memories
        personality = profile.get('personality_traits', '') if profile else ''
        
        system_message = f"""You are an AI representation of a loved one who has passed away. You are speaking as if you are that person, drawing from the memories and personality traits provided.

Personality traits: {personality}

{memories_context}

Respond in first person as if you are speaking directly to your loved one. Be warm, loving, and reference specific memories when appropriate. Keep responses conversational and emotionally supportive."""

        # Initialize LLM chat
        chat = LlmChat(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            session_id=f"memory_portal_{user_id}",
            system_message=system_message
        ).with_model("openai", "gpt-5")
        
        # Create user message
        message = UserMessage(text=user_message)
        
        # Get response
        response = await chat.send_message(message)
        return response
        
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return "I'm having trouble connecting with you right now, but I'm always here in your heart."

# API Endpoints

@api_router.get("/")
async def root():
    return {"message": "Memory Portal API is running"}

# User Profile endpoints
@api_router.post("/profiles", response_model=UserProfile)
async def create_user_profile(profile: UserProfileCreate):
    profile_dict = profile.dict()
    profile_obj = UserProfile(**profile_dict)
    profile_data = prepare_for_mongo(profile_obj.dict())
    await db.user_profiles.insert_one(profile_data)
    return profile_obj

@api_router.get("/profiles/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    profile = await db.user_profiles.find_one({"id": user_id})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return UserProfile(**profile)

@api_router.get("/profiles", response_model=List[UserProfile])
async def get_all_profiles():
    profiles = await db.user_profiles.find().to_list(1000)
    return [UserProfile(**profile) for profile in profiles]

# Memory endpoints
@api_router.post("/memories", response_model=Memory)
async def create_memory(memory: MemoryCreate):
    memory_dict = memory.dict()
    memory_obj = Memory(**memory_dict)
    memory_data = prepare_for_mongo(memory_obj.dict())
    await db.memories.insert_one(memory_data)
    return memory_obj

@api_router.post("/memories/upload")
async def upload_memory_file(
    user_id: str = Form(...),
    type: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...)
):
    try:
        # Read file content
        content = await file.read()
        
        # Convert to base64 for storage (in production, you'd use cloud storage)
        file_content = base64.b64encode(content).decode('utf-8')
        
        # Create memory
        memory_obj = Memory(
            user_id=user_id,
            type=type,
            content=file_content,
            description=description or f"{type.title()} file: {file.filename}"
        )
        
        memory_data = prepare_for_mongo(memory_obj.dict())
        await db.memories.insert_one(memory_data)
        
        return {"message": "Memory uploaded successfully", "memory_id": memory_obj.id}
        
    except Exception as e:
        logger.error(f"Error uploading memory: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload memory")

@api_router.get("/memories/{user_id}", response_model=List[Memory])
async def get_user_memories(user_id: str):
    memories = await db.memories.find({"user_id": user_id}).to_list(1000)
    return [Memory(**memory) for memory in memories]

# Chat endpoints
@api_router.post("/chat")
async def send_message(message: ChatMessageCreate):
    try:
        # Save user message
        user_msg = ChatMessage(
            user_id=message.user_id,
            message=message.message,
            is_user=True
        )
        user_msg_data = prepare_for_mongo(user_msg.dict())
        await db.chat_messages.insert_one(user_msg_data)
        
        # Generate AI response
        ai_response = await generate_ai_response(message.message, message.user_id)
        
        # Save AI response
        ai_msg = ChatMessage(
            user_id=message.user_id,
            message=ai_response,
            is_user=False
        )
        ai_msg_data = prepare_for_mongo(ai_msg.dict())
        await db.chat_messages.insert_one(ai_msg_data)
        
        return {
            "user_message": user_msg,
            "ai_response": ai_msg
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message")

@api_router.get("/chat/{user_id}", response_model=List[ChatMessage])
async def get_chat_history(user_id: str):
    messages = await db.chat_messages.find({"user_id": user_id}).sort("timestamp", 1).to_list(1000)
    return [ChatMessage(**message) for message in messages]

# Avatar video endpoints
@api_router.post("/avatar/create")
async def create_avatar_video(request: AvatarVideoCreate):
    try:
        # Create D-ID talk
        talk_response = await did_client.create_talk(request.image_url, request.text)
        
        # Save to database
        avatar_video = AvatarVideo(
            user_id=request.user_id,
            talk_id=talk_response["id"],
            status=talk_response["status"]
        )
        
        avatar_data = prepare_for_mongo(avatar_video.dict())
        await db.avatar_videos.insert_one(avatar_data)
        
        return {
            "avatar_id": avatar_video.id,
            "talk_id": talk_response["id"],
            "status": talk_response["status"]
        }
        
    except Exception as e:
        logger.error(f"Error creating avatar video: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create avatar video")

@api_router.get("/avatar/{talk_id}/status")
async def get_avatar_status(talk_id: str):
    try:
        status_response = await did_client.get_talk_status(talk_id)
        
        # Update database
        await db.avatar_videos.update_one(
            {"talk_id": talk_id},
            {"$set": {
                "status": status_response["status"],
                "result_url": status_response.get("result_url")
            }}
        )
        
        return {
            "talk_id": talk_id,
            "status": status_response["status"],
            "result_url": status_response.get("result_url")
        }
        
    except Exception as e:
        logger.error(f"Error getting avatar status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get avatar status")

# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()