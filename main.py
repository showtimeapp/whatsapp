from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import Response
import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import openai
from pymongo import MongoClient
import boto3
from datetime import datetime
import requests
import logging
from typing import Optional
import uuid
from urllib.parse import unquote

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dharavi WhatsApp Bot")

# Initialize services
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
openai.api_key = os.getenv("OPENAI_API_KEY")
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client.Drp_project
messages_collection = db.messages

# AWS S3 setup
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

# Simple RAG knowledge base (in production, use vector database)
DHARAVI_KNOWLEDGE = """
Dharavi Redevelopment Project Information:

1. Overview:
- Dharavi is one of Asia's largest slums located in Mumbai, India
- The redevelopment project aims to transform the area into a modern urban space
- The project involves rehabilitation of existing residents and commercial establishments

2. Key Features:
- Free housing for eligible residents
- Modern infrastructure including water, electricity, and sewage systems
- Educational and healthcare facilities
- Commercial spaces and employment opportunities
- Green spaces and recreational areas

3. Eligibility Criteria:
- Must be a resident of Dharavi before year 2000
- Valid documentation proving residency
- Cooperation with the redevelopment process

4. Timeline:
- Project is being implemented in phases
- Initial surveys and planning completed
- Construction of temporary accommodation ongoing
- Full completion expected in several years

5. Benefits:
- Improved living conditions
- Better healthcare and education access
- Economic opportunities
- Modern amenities
- Secure tenure

6. Concerns and Support:
- Dedicated helpline for resident queries
- Regular community meetings
- Grievance redressal mechanism
- Support for temporary relocation
"""

def get_ai_response(user_message: str) -> str:
    """Get AI response using OpenAI with RAG context"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"You are a helpful assistant for the Dharavi Redevelopment Project. Use the following information to answer user questions: {DHARAVI_KNOWLEDGE}. If the question is not related to Dharavi redevelopment, politely redirect the conversation back to the project."
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "I'm sorry, I'm having trouble processing your request right now. Please try again later."

def upload_to_s3(file_content: bytes, filename: str, content_type: str) -> str:
    """Upload file to S3 and return URL"""
    try:
        # Generate unique filename
        unique_filename = f"{datetime.now().strftime('%Y/%m/%d')}/{uuid.uuid4()}_{filename}"
        
        s3_client.put_object(
            Bucket=os.getenv("S3_BUCKET_NAME"),
            Key=unique_filename,
            Body=file_content,
            ContentType=content_type
        )
        
        # Generate S3 URL
        s3_url = f"https://{os.getenv('S3_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{unique_filename}"
        return s3_url
    except Exception as e:
        logger.error(f"S3 upload error: {e}")
        return None

def log_message(phone_number: str, message: str, message_type: str, media_url: str = None, response: str = None):
    """Log message to MongoDB"""
    try:
        document = {
            "user": {"wa_number": phone_number},
            "message": message,
            "type": message_type,
            "media_url": media_url,
            "timestamp": datetime.now(),
            "response": response
        }
        messages_collection.insert_one(document)
    except Exception as e:
        logger.error(f"MongoDB logging error: {e}")

# Add this debug function to main.py
def debug_media_download(media_url: str):
    """Debug media download"""
    print(f"Media URL: {media_url}")
    print(f"Account SID: {os.getenv('TWILIO_ACCOUNT_SID')[:10]}...")
    print(f"Auth Token: {os.getenv('TWILIO_AUTH_TOKEN')[:10]}...")
    
    auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    
    try:
        response = requests.get(media_url, auth=auth, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        print(f"Content Length: {len(response.content)}")
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None
    
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages"""
    try:
        form_data = await request.form()
        
        # Extract message data
        from_number = form_data.get("From", "")
        message_body = form_data.get("Body", "")
        media_url = form_data.get("MediaUrl0", "")
        media_content_type = form_data.get("MediaContentType0", "")
        
        logger.info(f"Received message from {from_number}: {message_body}")
        
        # Create Twilio response
        resp = MessagingResponse()
        msg = resp.message()
        
        # Handle media files
        if media_url:
            try:
                # Download media from Twilio with authentication
                auth = (os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
                media_response = requests.get(media_url, auth=auth)
                
                logger.info(f"Media download status: {media_response.status_code}")
                logger.info(f"Media URL: {media_url}")
                
                if media_response.status_code == 200:
                    # Determine filename
                    if "image" in media_content_type:
                        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    elif "pdf" in media_content_type:
                        filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    else:
                        filename = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # Upload to S3
                    s3_url = upload_to_s3(media_response.content, filename, media_content_type)
                    
                    if s3_url:
                        response_text = "✅ Your file has been received and securely stored. Thank you for sharing!"
                        log_message(from_number, "Media file", "media", s3_url, response_text)
                    else:
                        response_text = "❌ Sorry, there was an error storing your file. Please try again."
                        log_message(from_number, "Media file", "media", None, response_text)
                else:
                    response_text = "❌ Sorry, I couldn't download your file. Please try again."
                    log_message(from_number, "Media file", "media", None, response_text)
            except Exception as e:
                logger.error(f"Media handling error: {e}")
                response_text = "❌ Sorry, there was an error processing your file."
                log_message(from_number, "Media file", "media", None, response_text)
        
        # Handle text messages
        elif message_body:
            # Check if it's a new user (welcome message)
            if "hi" in message_body.lower() and "query" in message_body.lower():
                response_text = """🏠 Welcome to Dharavi Redevelopment Project Information Bot!

I can help you with:
• Project overview and timeline
• Eligibility criteria
• Benefits and features
• Documentation requirements
• Support and grievances

Please ask me any question about the Dharavi Redevelopment Project. You can also send documents or images for secure storage."""
            else:
                # Get AI response
                response_text = get_ai_response(message_body)
            
            log_message(from_number, message_body, "text", None, response_text)
        
        else:
            response_text = "Hello! Please send me a text message or share a document about the Dharavi Redevelopment Project."
            log_message(from_number, "Empty message", "text", None, response_text)
        
        msg.body(response_text)
        
        return Response(content=str(resp), media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        resp = MessagingResponse()
        msg = resp.message()
        msg.body("Sorry, there was an error processing your message. Please try again.")
        return Response(content=str(resp), media_type="application/xml")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Dharavi WhatsApp Bot is running!"}

@app.get("/stats")
async def get_stats():
    """Get bot statistics"""
    try:
        total_messages = messages_collection.count_documents({})
        text_messages = messages_collection.count_documents({"type": "text"})
        media_messages = messages_collection.count_documents({"type": "media"})
        
        return {
            "total_messages": total_messages,
            "text_messages": text_messages,
            "media_messages": media_messages,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": "Could not retrieve stats"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)