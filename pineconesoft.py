
import os 
import pandas as pd
import time
from dotenv import load_dotenv 
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message

# Load env variables from .env file 
load_dotenv()

#pinecone_api_key = os.getenv('PINECONE_API_KEY')
pinecone_api_key = PINECONE_API_KEY

if not pinecone_api_key:
    raise ValueError("Where yo Pinecone API key at??")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)


ASSISTANT_NAME = "hamidceo"  


class PineconeAssistantChat:
    def __init__(self, assistant_name):
        self.assistant_name = assistant_name
        self.pc = pc
        self.chat_history = []
        
        # Get the assistant
        try:
            self.assistant = self.pc.assistant.Assistant(assistant_name)
            print(f"Connected to assistant: {self.assistant.name}")
            print(f"Assistant status: {self.assistant.status}")
        except Exception as e:
            print(f"Error connecting to assistant: {e}")
            print("Available assistants:")
            self.list_assistants()
            raise
    
    def chat(self, message, include_citations=True):
        try:
            # Create message object
            user_message = Message(role="user", content=message)
            
            # Send message to assistant
            response = self.assistant.chat(
                messages=[user_message]
            )
            
            
            # Store in chat history
            self.chat_history.append(user_message)
            print(response.message.content)
            return response
            
        except Exception as e:
            print(f"Error chatting with assistant: {e}")
            return None
    
    def chat_with_context():
        try:
            # Create message object
            user_message = Message(role="user", content=message)

            self.chat_history.append(user_message)
            
            # Send message to assistant
            response = self.assistant.chat(
                messages=chat_history
            )

            return response
            
        except Exception as e:
            print(f"Error chatting with assistant: {e}")
            return None

    def get_chat_history(self):
        """Get the chat history"""
        return self.chat_history
    
    def clear_chat_history(self):
        """Clear the chat history"""
        self.chat_history = []
        print("Chat history cleared")
    
    def get_assistant_info(self):
        """Get information about the assistant"""
        try:
            info = self.pc.assistant.describe_assistant(self.assistant_name)
            return info
        except Exception as e:
            print(f"Error getting assistant info: {e}")
            return None


# Function to upload documents to your assistant (if needed)
def upload_documents_to_assistant(assistant_name, csv_file_path):
    """
    Upload documents from CSV to your Pinecone assistant
    
    Args:
        assistant_name (str): Name of your assistant
        csv_file_path (str): Path to your CSV file
    """
    try:
        # Read CSV
        df = pd.read_csv(csv_file_path)
        
        # Convert each row to a document format
        documents = []
        for i, row in df.iterrows():
            doc_content = f"Title: {row['title']}\nSource: {row['source']}\nContent: {row['text']}"
            documents.append({
                "id": f"doc_{i}",
                "content": doc_content,
                "metadata": {
                    "title": row['title'],
                    "source": row['source'],
                    "page_id": str(row.get('page_id', i))
                }
            })
        
        # Upload documents to assistant
        response = pc.assistant.upload_documents(
            assistant_name=assistant_name,
            documents=documents
        )
        
        print(f"Successfully uploaded {len(documents)} documents to {assistant_name}")
        return response
        
    except Exception as e:
        print(f"Error uploading documents: {e}")
        return None


hmdceo = PineconeAssistantChat(ASSISTANT_NAME)

context_mode = False
'''
while True: 
    print("--------------------------------------------------")
    question = input("LegalSoft Ai at your service: \n")

    if question.lower() == "exit":
        break 
    elif question.lower() == 'context':
        context_mode = not context_mode
        print(f"Context Mode changed to {context_mode}")
        continue

    if context_mode:
        response = hmdceo.chat_with_context(question)
    else:    
        response = hmdceo.chat(question)

    print(response.message.content)
'''


