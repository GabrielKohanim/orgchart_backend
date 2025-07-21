# Quick Setup Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies

**Frontend:**
```bash
npm install
```

**Backend:**
```bash
pip install -r requirements.txt
```

### 2. Configure Environment

1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit `.env` and add your API keys:
```
PINECONE_API_KEY=your_actual_pinecone_api_key_here
GOOGLE_API_KEY=your_actual_google_api_key_here
```

### 3. Start the Servers

**Terminal 1 - Backend:**
```bash
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### 4. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔧 Troubleshooting

### Common Issues:

1. **"Module not found" errors**
   - Run `npm install` for frontend
   - Run `pip install -r requirements.txt` for backend

2. **CORS errors**
   - Ensure backend is running on port 8000
   - Check that frontend is on port 3000

3. **Pinecone connection errors**
   - Verify your API key is correct
   - Ensure the assistant "hamidceo" exists in your Pinecone account

4. **Port already in use**
   - Kill existing processes or change ports in the configuration files

### Getting API Keys:

**Pinecone API Key:**
1. Go to [Pinecone Console](https://app.pinecone.io/)
2. Create an account or sign in
3. Create a new project
4. Get your API key from the project settings
5. Add it to the `.env` file

**Google API Key:**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Get your API key from the API keys section
4. Add it to the `.env` file

## 🎯 Next Steps

1. **Explore the UI**: Try adding, editing, and moving nodes
2. **Test AI Features**: Click "Propose AI Changes" to see suggestions
3. **Customize**: Modify colors, departments, or add new features
4. **Deploy**: Follow the deployment instructions in README.md

## 📞 Need Help?

- Check the main README.md for detailed documentation
- Review the API documentation at http://localhost:8000/docs
- Check browser console and terminal logs for error messages 