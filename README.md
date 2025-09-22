# 🏛️ Landover Hills Budget Assistant

A sophisticated municipal budget analysis chatbot that provides real-time financial insights through natural language queries. Built with FastAPI, Supabase, and advanced LLM integration.

## ✨ Features

### 📊 **Comprehensive Budget Analysis**
- **Year-over-year comparisons** - Track budget changes across fiscal years
- **Category rankings** - Identify top-funded departments and programs
- **Percentage breakdowns** - Understand budget distribution and shares
- **Line-item details** - Drill down into specific budget allocations

### 🤖 **Advanced Natural Language Processing**
- **Intent recognition** - Converts natural language to structured queries
- **Mathematical accuracy** - All calculations based on database views, not LLM hallucinations
- **Context-aware responses** - Understands fiscal years, departments, and budget terminology
- **Error handling** - Graceful fallbacks for unclear or complex queries

### 🔮 **Scenario Planning & Forecasting**
- **What-if analysis** - Model budget changes and their impacts
- **Percentage-based scenarios** - "If police funding increases by 10%..."
- **Across-the-board cuts** - Analyze department-wide budget reductions
- **Impact calculations** - Precise dollar amounts and percentage changes

### 📈 **Real-time Data Integration**
- **Supabase integration** - Live connection to municipal budget database
- **PostgreSQL views** - Optimized queries for fast responses
- **FY26 partial data handling** - Transparent reporting of incomplete data

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ShishirPoreddy/Landover_Hills_Dashboard.git
   cd Landover_Hills_Dashboard
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase and OpenAI credentials
   ```

5. **Set up database**
   ```bash
   # Run the SQL views in your Supabase SQL editor
   cat supabase_views.sql
   ```

6. **Start the server**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

7. **Access the application**
   - Dashboard: http://127.0.0.1:8000/
   - API Docs: http://127.0.0.1:8000/docs

## 💬 Example Queries

### Basic Budget Questions
- "What is the total budget for FY25?"
- "Which category received the most funding in FY25?"
- "What percentage of the budget goes to taxes?"

### Year-over-Year Analysis
- "What is the budget difference between FY24 and FY26?"
- "How did police department funding change from FY24 to FY25?"
- "What is the percent change from FY25 to FY26 in taxes?"

### Scenario Planning
- "If we need to cut 15% from all departments, what would the outcome be?"
- "Cut 10% from police in FY25"
- "What if administration increases by 20% in FY26?"

### Line-Item Details
- "How much did Administration spend on Payroll Taxes in FY24?"
- "Show me all line items for Police Department in FY25"

## 🏗️ Architecture

### Backend (FastAPI)
- **Intent Recognition** - LLM-based natural language understanding
- **Deterministic Queries** - Database-driven calculations for accuracy
- **CORS-enabled** - Cross-origin support for web interfaces
- **Static file serving** - Integrated frontend hosting

### Database (Supabase/PostgreSQL)
- **Normalized views** - Clean data structure for consistent queries
- **Optimized aggregations** - Pre-computed totals and percentages
- **Year-over-year calculations** - Built-in trend analysis

### Frontend (Vanilla JS + Tailwind)
- **Responsive design** - Mobile-friendly budget dashboard
- **Interactive charts** - Visual budget representations
- **Real-time chat** - Seamless conversation interface

## 📊 Database Schema

The application uses PostgreSQL views for optimal performance:

- `v_year_totals` - Annual budget totals
- `v_category_totals` - Department/category aggregations
- `v_year_yoy` - Year-over-year change calculations
- `v_category_shares` - Percentage breakdowns
- `v_line_items` - Detailed line-item data

## 🔧 API Endpoints

### Core Endpoints
- `POST /ask` - Main chat interface
- `GET /budget-facts` - Raw budget data
- `POST /insights` - Detailed analysis

### Budget API Routes
- `GET /api/budget/year-totals` - Annual totals
- `GET /api/budget/yoy` - Year-over-year data
- `GET /api/budget/category` - Category rankings
- `GET /api/budget/shares` - Percentage breakdowns
- `GET /api/budget/line-item` - Specific line items

## 🧪 Testing

### Unit Tests
```bash
npm test  # Run TypeScript tests
```

### API Testing
```bash
# Test with curl
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total budget for FY25?"}'
```

### Interactive Testing
Visit http://127.0.0.1:8000/docs for the interactive API documentation.

## 📁 Project Structure

```
landover-budget-assistant/
├── app/                    # FastAPI backend
│   ├── main.py            # Main application
│   ├── llm.py             # LLM integration
│   ├── qa.py              # Question answering
│   ├── rag.py             # Retrieval augmented generation
│   └── db.py              # Database connection
├── public/                # Frontend files
│   ├── index.html         # Main dashboard
│   ├── assistant.js       # Chat interface
│   └── tailwind.min.css   # Styling
├── src/                   # TypeScript SDK
│   ├── bot/               # Intent handling
│   └── lib/               # Budget utilities
├── tests/                 # Test suite
├── supabase_views.sql     # Database schema
└── requirements.txt       # Python dependencies
```

## 🔒 Environment Variables

Create a `.env` file with the following variables:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_DATABASE_URL=your_database_url
OPENAI_API_KEY=your_openai_key
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Town of Landover Hills** - For providing the budget data
- **Supabase** - For the database infrastructure
- **OpenAI** - For the language model capabilities
- **FastAPI** - For the robust web framework

## 📞 Support

For questions or support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for transparent municipal budgeting**
