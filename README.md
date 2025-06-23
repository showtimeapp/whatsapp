**# Dharavi WhatsApp Bot**

A WhatsApp chatbot **for** the Dharavi Redevelopment Project that answers queries using AI **and** stores media files securely**.**

**## Features**

**-** WhatsApp integration via Twilio
**-** AI**-**powered responses using OpenAI GPT
**-** Media **file** storage **in** AWS S3
**-** Conversation logging **in** MongoDB
**-** Simple RAG **(**Retrieval Augmented Generation**)**for project**-**specific knowledge

**## Quick Start**

**1.****Clone **and** Setup******

```bash
   git clone **<**repository**>**
   cd dharavi**-**whatsapp**-**bot
   pip install **-**r requirements**.**txt
```

**2.****Environment Variables******
   Copy `**.**env**.**example` to `**.**env` **and** fill **in** your credentials

**3.****Run the Bot******

```bash
   python run**.**py
```

**4.****Access******
**-** Bot API**:** http**:**//localhost**:**8000
**-** Webhook**:** http**:**//localhost**:**8000**/**webhook
**-** Stats**:** http**:**//localhost**:**8000**/**stats

**## WhatsApp Integration**

Use this link to start chatting**:**

```
https**:**//wa**.**me**/**YOUR_TWILIO_NUMBER?text**=**Hi**%**20I**%**20have**%**20a**%**20query**%**20about**%**20Dharavi**%**20Redevelopment

## Project Structure

```

dharavi-whatsapp-bot/
├── main.py              # Main FastAPI application
├── models.py            # Data models
├── config.py            # Configuration
├── run.py               # Application runner
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
└── README.md           # This file

```

```
