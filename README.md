# ExpenseFlow - AI-Powered Expense Claim System

An intelligent expense claim system that automates receipt parsing, duplicate detection, and multi-role approval workflows.

## 🎯 Problem Statement

Staff at companies spend their own money on travel, meals, supplies, and taxis, then claim it back. This process is painful - filing a claim takes longer than the coffee cost. ExpenseFlow solves this with AI-powered automation.

## ✨ Features

- **AI Receipt Parsing**: Paste text or upload images - AI extracts vendor, amount, date, and category automatically
- **Smart Duplicate Detection**: Two-tier system - exact match (auto-block) + fuzzy match (flag for review)
- **Role-Based Workflow**: Staff → Submit claims | Manager → Approve (cannot self-approve) | Finance → Pay
- **Monthly Reports**: Category and employee spending breakdowns with interactive charts
- **Realistic Demo Data**: Includes duplicates, close-to-limit users, and real-world scenarios
- **Claim History**: Track all your claims with status (Pending/Approved/Paid)
- **Dashboard Analytics**: Quick stats for pending, approved, and total paid amounts

## 🏗️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Streamlit |
| **Database** | SQLite (swappable with PostgreSQL) |
| **AI/LLM** | Groq API (qwen/qwen3.8-27b) |
| **OCR** | Tesseract |
| **ORM** | SQLAlchemy |
| **Language** | Python 3.12+ |

## 🚀 How to Run Locally

### Prerequisites
- Python 3.12+
- Tesseract OCR (for image uploads)
- Groq API Key (free at console.groq.com)

 1: Clone the Repository

git clone https://github.com/Dhayalramesh/ExpenseFlow.git
cd ExpenseFlow

 2: Create Virtual Environment

 python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3: Install Dependencies

pip install -r requirements.txt

4:Install Tesseract OCR (Optional - for image uploads)

Windows: Download from UB-Mannheim/tesseract
Mac: brew install tesseract
Linux: sudo apt-get install tesseract-ocr

5:Set Up Environment Variables

Create a .env file:
GROQ_API_KEY=gsk_YOUR_ACTUAL_GROQ_API_KEY

6:
streamlit run app.py

👤 Demo Users
Username	Role	Description
Alice Johnson	STAFF	Regular employee
Bob Smith	STAFF	Regular employee
Charlie Brown	STAFF	Close to monthly limit
Diana Prince	MANAGER	Team manager (cannot self-approve)
Frank Miller	FINANCE	Can pay claims
Eve Adams	STAFF	Regular employee
Grace Lee	STAFF	Regular employee
Henry Williams	STAFF	Regular employee

🔄 Workflow
Staff submits a claim (text or image) → AI parses receipt

System checks for duplicates (exact + fuzzy)

Manager reviews and approves (cannot approve their own claims)

Finance pays approved claims

Monthly reports show spending by category and employee

🤖 AI Tools Used
Groq API (qwen/qwen3.8-27b): Receipt parsing with JSON mode for structured output

Tesseract OCR: Image text extraction with preprocessing (grayscale, contrast, sharpen)

💡 Key Decisions & Assumptions
Authentication: Role dropdown for demo - server-side checks prevent self-approval

Database: SQLite for portability (SQLAlchemy makes it easy to switch to PostgreSQL)

Duplicate Detection: Two-tier system - exact (hard block) + fuzzy (soft flag for review)

Receipt Parsing: LLM first (with confidence score), OCR second (with manual fallback)

🐛 What Broke When I Tested
OCR Accuracy: Poor lighting caused errors → Added image preprocessing + manual correction

Fuzzy False Positives: Too many flags → Increased similarity threshold

Groq Model Deprecation: mixtral-8x7b was decommissioned → Switched to qwen/qwen3.8-27b

🔮 What I'd Do Next (Given Another Week)
Switch to PostgreSQL (Supabase) for production

Add real authentication with OAuth2/JWT

Email notifications for approvals/payments

Dockerize the application

Add spending limits and alerts

Improve OCR with advanced image preprocessing

📝 License
This project was built as a technical assessment for VSP Techverse.

👨‍💻 Author
Dhayal R

GitHub: Dhayalramesh

LinkedIn: dhayalsr

Email: dhayal1107@gmail.com


# ExpenseFlow - AI-Powered Expense Claim System

## 🌐 Live Demo
[expenseflow-k2zxjcjxjtfeoarpaaur23.streamlit.app](https://expenseflow-k2zxjcjxjtfeoarpaaur23.streamlit.app)

An intelligent expense claim system that automates receipt parsing, duplicate detection, and multi-role approval workflows.
