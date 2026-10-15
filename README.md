# LateralEntryBot — Maharashtra DSY Admission Helper

An AI-powered chatbot that answers questions about **Direct Second Year (Lateral Entry) Engineering Admission** in Maharashtra. It extracts information from official admission PDFs you upload and uses OpenAI to generate grounded answers.

> **Disclaimer:** This bot answers only from documents you upload. Always verify admission information at the official [CET Cell website](https://cetcell.mahacet.org/).

---

## Project Structure

```
LateralEntryBot/
├── app.py                  # Flask app — routes, chat API, upload API
├── rag.py                  # PDF extraction, TF-IDF retrieval, AI answers
├── requirements.txt        # Python dependencies
├── .env.example            # Template for your API key
├── .gitignore              # Excludes secrets and virtual environments
├── README.md               # This file
├── templates/
│   └── index.html          # Chatbot HTML page
├── static/
│   ├── style.css           # Blue-and-white responsive design
│   └── script.js           # Chat UI, FAQ buttons, PDF upload logic
└── data/
    └── documents/          # Drop official admission PDFs here
```

---

## Prerequisites

- Python 3.10 or newer
- An [OpenAI API key](https://platform.openai.com/api-keys)

---

## Windows PowerShell Setup

### 1. Open PowerShell in the project folder

```powershell
cd C:\Users\Komal\Desktop\LateralEntryBot
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> If you get a script execution error, run this first (once per machine):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create your `.env` file

```powershell
Copy-Item .env.example .env
```

Open `.env` in Notepad and replace `sk-your-api-key-here` with your real OpenAI API key:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

### 5. (Optional) Add admission PDFs

Download official brochures from [cetcell.mahacet.org](https://cetcell.mahacet.org/) and place them in `data/documents/`. They will be indexed automatically on startup, or you can upload them through the web interface.

### 6. Start the server

```powershell
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## Usage

1. **Upload a PDF** using the sidebar panel (max 10 MB).
2. **Ask a question** in the chat box or click a FAQ button.
3. The bot retrieves relevant passages and generates an answer.
4. **Sources** (filename + page number) are shown below each answer.
5. If the answer is not in the documents, the bot says so and links to the official site.

---

## FAQ Topics (quick buttons)

| Button | Question asked |
|--------|---------------|
| Eligibility | Eligibility criteria for DSY lateral entry |
| Documents | Required documents for admission |
| CAP Rounds | How the CAP round process works |
| Option Form | How to fill the option form |
| Admission Process | Step-by-step admission process |
| Important Dates | Admission schedule and deadlines |

---

## How It Works

```
User question
     │
     ▼
TF-IDF retrieval ──→ Top-5 relevant chunks from uploaded PDFs
     │
     ▼
OpenAI API  ──→  Answer grounded in retrieved excerpts
     │
     ▼
Response + source references (filename, page number)
```

---

## Security Notes

- The OpenAI API key is stored only in `.env` on the server — it is never sent to the browser.
- `.env` is listed in `.gitignore` and will not be committed to version control.
- Uploaded PDFs are saved to `data/documents/` (also excluded from git).
- Do not upload private student documents or sensitive personal information.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OPENAI_API_KEY is not set` error | Add your key to `.env` and restart the server |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the virtual environment |
| PDF gives 0 chunks | The PDF may be scanned (image-only). Use text-based PDFs from the official site |
| Port 5000 already in use | Change the port: `python app.py` → edit `app.run(port=5001)` in `app.py` |
| File too large | Maximum upload size is 10 MB |

---

## Important Links

- Official CET Cell: https://cetcell.mahacet.org/
- OpenAI Platform: https://platform.openai.com/
