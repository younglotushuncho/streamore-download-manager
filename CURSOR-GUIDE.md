# 🎯 Cursor AI Build Guide

## How to Use This Project with Cursor AI

This guide shows you exactly how to use Cursor AI to build the YTS Movie Monitor application step-by-step.

---

## 📂 Project Files Overview

### Documentation Files (READ THESE FIRST!)
1. **`00-PROJECT-OVERVIEW.md`** - Complete project architecture
2. **`01-SETUP-GUIDE.md`** - Environment setup instructions
3. **`02-DEVELOPMENT-STEPS.md`** - ⭐ **Main build guide - use this!**
4. **`03-API-DOCUMENTATION.md`** - API reference
5. **`04-SCRAPER-GUIDE.md`** - Web scraping details
6. **`05-UI-DESIGN.md`** - UI specifications
7. **`06-DEPLOYMENT.md`** - Building executable

### Key File
**The most important file is `02-DEVELOPMENT-STEPS.md`** - it contains all the prompts you need to give Cursor AI!

---

## 🚀 Getting Started

### Step 1: Initial Setup (Do This Manually)

```bash
# 1. Create project directory
mkdir yts-movie-monitor
cd yts-movie-monitor

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Open in Cursor
cursor .
```

### Step 2: Copy Documentation

Copy all files from `docs/` folder into your project:
- 00-PROJECT-OVERVIEW.md
- 01-SETUP-GUIDE.md  
- 02-DEVELOPMENT-STEPS.md ⭐
- 03-API-DOCUMENTATION.md
- 04-SCRAPER-GUIDE.md
- 05-UI-DESIGN.md
- 06-DEPLOYMENT.md

---

## 📝 How to Use the Prompts

### Method 1: Copy & Paste (Recommended)

1. Open `02-DEVELOPMENT-STEPS.md`
2. Find the step you want to build (e.g., "STEP 1.1: Create Database Schema")
3. Copy the **entire text block** under "Cursor Prompt:"
4. Paste into Cursor AI chat
5. Review the generated code
6. Accept or modify as needed

**Example:**

```
You: [Paste this into Cursor chat]

Create a SQLite database module for a movie monitoring app with the following requirements:

File: backend/database.py

Requirements:
1. Create 4 tables:
   - movies: id (TEXT PRIMARY KEY), title, year, rating, genres (JSON), description, poster_url, poster_local, yts_url, scraped_at
   [... rest of prompt]
```

### Method 2: Use Cursor Composer (Even Better!)

1. Press `Ctrl+I` (or Cmd+I on Mac) to open Cursor Composer
2. Select multiple files you want Cursor to work with
3. Paste the prompt
4. Cursor will generate code across multiple files at once!

---

## 🎯 Build Order

Follow this exact order for best results:

### Phase 1: Foundation (Day 1)
```
✅ STEP 1.1 - Database Schema
✅ STEP 1.2 - Data Models  
✅ STEP 1.3 - Constants
```

**Test after Phase 1:**
```bash
python -c "from backend.database import init_db; init_db(); print('✓ Database works!')"
```

---

### Phase 2: Web Scraper (Day 1-2)
```
✅ STEP 2.1 - Base Scraper
✅ STEP 2.2 - Poster Caching
✅ STEP 2.3 - Scraper Tests
```

**Test after Phase 2:**
```python
from backend.scraper import YTSScraper
scraper = YTSScraper()
movies = scraper.scrape_browse_page(page=1)
print(f"✓ Found {len(movies)} movies!")
```

---

### Phase 3: Backend API (Day 2-3)
```
✅ STEP 3.1 - Flask API Server
✅ STEP 3.2 - Torrent Manager
✅ STEP 3.3 - API Integration
✅ STEP 3.4 - API Tests
```

**Test after Phase 3:**
```bash
# Terminal 1
python backend/app.py

# Terminal 2
curl http://localhost:5000/api/movies
```

---

### Phase 4: Desktop UI (Day 3-5)
```
✅ STEP 4.1 - Main Window
✅ STEP 4.2 - Movie Grid
✅ STEP 4.3 - Movie Details Dialog
✅ STEP 4.4 - Downloads Manager
✅ STEP 4.5 - Settings Dialog
✅ STEP 4.6 - API Client
✅ STEP 4.7 - Notifications
✅ STEP 4.8 - Main Entry Point
```

**Test after Phase 4:**
```bash
python frontend/main.py
```

---

### Phase 5: Polish (Day 5)
```
✅ STEP 5.1 - Dark Theme Stylesheet
✅ STEP 5.2 - Icons (download from internet)
✅ STEP 5.3 - Loading Widgets
```

---

### Phase 6: Testing (Day 6)
```
✅ STEP 6.1 - End-to-End Tests
✅ STEP 6.2 - Error Handling Review
✅ STEP 6.3 - Logging Setup
```

---

### Phase 7: Build & Deploy (Day 7)
```
✅ STEP 7.1 - Build Script
✅ STEP 7.2 - Installer
✅ STEP 7.3 - Release Checklist
```

---

## 💡 Cursor AI Tips

### 1. Be Specific with File Paths
Always include the full file path in prompts:
```
✅ Good: "Create backend/scraper.py with..."
❌ Bad: "Create a scraper with..."
```

### 2. Use Multi-File Context
When asking Cursor to modify code:
```
Select these files:
- backend/database.py
- backend/app.py
- shared/models.py

Then ask: "Update app.py to use the new Movie model from models.py"
```

### 3. Ask for Explanations
```
You: "Explain what this code does:"
[paste code]

Cursor will explain it line by line
```

### 4. Iterate and Refine
```
You: "Add error handling to the scraper"
Cursor: [generates code]
You: "Also add retry logic with exponential backoff"
Cursor: [improves code]
```

### 5. Generate Tests
```
You: "Write pytest tests for backend/scraper.py"
Cursor: [generates comprehensive tests]
```

---

## 🔍 Example Workflow

### Building the Scraper (Detailed Example)

#### Step 1: Create the File
```
You in Cursor Chat:
"Create backend/scraper.py following the specification in docs/04-SCRAPER-GUIDE.md"
```

Cursor will generate the entire scraper file.

#### Step 2: Test It
```bash
# Create a test file
python -c "
from backend.scraper import YTSScraper
s = YTSScraper()
movies = s.scrape_browse_page(page=1)
for m in movies[:3]:
    print(f'{m['title']} ({m['year']})')
"
```

#### Step 3: Fix Issues (if any)
```
You: "The scraper is not finding the movie titles. The HTML might have changed. Can you update the selectors?"

Cursor: [analyzes and updates selectors]
```

#### Step 4: Add Features
```
You: "Add a method to download poster images with progress callback"

Cursor: [adds the feature]
```

---

## 🛠️ Common Cursor Commands

### Creating Files
```
You: "Create frontend/ui/main_window.py with a PyQt6 main window"
```

### Modifying Files
```
You: "In backend/app.py, add a new endpoint GET /api/stats"
```

### Debugging
```
You: "Why is this function failing? [paste code]"
You: "Add debug logging to this function"
```

### Refactoring
```
You: "Refactor this code to be more efficient"
You: "Split this large function into smaller helper functions"
```

### Documentation
```
You: "Add docstrings to all functions in backend/scraper.py"
```

---

## ⚡ Pro Tips

### 1. Use the Documentation
Cursor works best when it has context. Always reference the docs:
```
You: "Following the API design in docs/03-API-DOCUMENTATION.md, create the /api/downloads endpoint"
```

### 2. Build Incrementally
Don't try to build everything at once:
```
✅ Good: Build one component, test it, move to next
❌ Bad: Ask for entire app in one prompt
```

### 3. Leverage Auto-Complete
- Start typing and let Cursor suggest
- Tab to accept suggestions
- Great for repetitive code

### 4. Use Cursor's Inline Chat
- Select code
- Press `Ctrl+K`
- Ask Cursor to modify just that code

### 5. Ask for Multiple Variations
```
You: "Show me 3 different ways to implement this feature"
Cursor: [provides options]
You: "Use approach #2"
```

---

## 🐛 Troubleshooting Cursor

### Cursor Generates Wrong Code
1. Be more specific in your prompt
2. Reference the exact documentation section
3. Show Cursor an example of what you want

### Cursor Can't Find Files
1. Make sure files are in the workspace
2. Use full paths: `backend/scraper.py` not `scraper.py`
3. Refresh Cursor's index (Cmd+Shift+P → "Refresh")

### Cursor Doesn't Understand Context
1. Select relevant files before prompting
2. Copy documentation into the chat
3. Show Cursor existing code examples

---

## 📊 Progress Tracking

Create a checklist file: `PROGRESS.md`

```markdown
# Development Progress

## Phase 1: Database ✅
- [x] Database schema
- [x] Data models
- [x] Constants

## Phase 2: Scraper 🚧
- [x] Base scraper
- [ ] Poster caching
- [ ] Tests

## Phase 3: Backend API ⏳
- [ ] Flask server
- [ ] Torrent manager
- [ ] Integration
- [ ] Tests

[... continue for all phases]
```

Update this as you complete each step!

---

## 🎓 Learning Resources

### Cursor AI Docs
- https://docs.cursor.com/

### Project-Specific Help
- See `docs/00-PROJECT-OVERVIEW.md` for architecture
- See `docs/02-DEVELOPMENT-STEPS.md` for all prompts
- See individual guides for detailed specs

### Python/PyQt Resources
- PyQt6 Docs: https://doc.qt.io/qtforpython/
- Flask Docs: https://flask.palletsprojects.com/
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/

---

## ✅ Quick Start Checklist

Before you start building:

- [ ] Python 3.11+ installed
- [ ] Cursor AI installed and activated
- [ ] Virtual environment created
- [ ] All documentation copied to project
- [ ] Read `00-PROJECT-OVERVIEW.md`
- [ ] Reviewed `02-DEVELOPMENT-STEPS.md`
- [ ] Ready to start with Phase 1!

---

## 🚀 Ready to Build?

1. **Start with Phase 1** (Database)
2. **Copy prompts from `02-DEVELOPMENT-STEPS.md`**
3. **Paste into Cursor**
4. **Review & test each step**
5. **Move to next phase**

**Good luck! You've got this! 🎉**

---

## 💬 Need Help?

If you get stuck:
1. Re-read the relevant documentation section
2. Ask Cursor to explain the issue
3. Check if there are syntax errors
4. Make sure all dependencies are installed
5. Review the example code in the guides

---

**Cursor Build Guide Version**: 1.0  
**Last Updated**: February 2026  
**Estimated Build Time**: 5-7 days (following the guide)
