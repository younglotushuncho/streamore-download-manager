# 🎬 START HERE - YTS Movie Monitor Project

## Welcome! 👋

This is your complete guide to building the YTS Movie Monitor desktop application using Cursor AI.

---

## 📖 What Is This Project?

A **Windows desktop application** that:
- Monitors YTS (yts-official.cc) for new movie releases
- Displays movies in a beautiful grid interface
- Filters by genre, year, and quality
- Downloads movies using an integrated torrent engine
- Sends notifications when downloads complete

**Technology**: Python + PyQt6 + Flask + libtorrent

---

## 🗂️ Documentation Structure

### 1️⃣ **CURSOR-GUIDE.md** ⭐ START HERE!
**Read this first!** Shows you exactly how to use Cursor AI to build this project.

### 2️⃣ **README.md**
Project overview, features, and quick start guide.

### 3️⃣ **docs/** folder - Detailed Documentation

#### Planning & Architecture
- **`00-PROJECT-OVERVIEW.md`**
  - Complete project architecture
  - Technology stack
  - Database schema
  - Development phases
  - Success criteria

#### Setup & Development  
- **`01-SETUP-GUIDE.md`**
  - Development environment setup
  - Installing Python, Git, dependencies
  - Project structure creation
  - Verification scripts

- **`02-DEVELOPMENT-STEPS.md`** ⭐ **MOST IMPORTANT!**
  - Step-by-step build instructions for Cursor AI
  - Complete prompts for every component
  - Organized by phase (Database → Scraper → API → UI → Deploy)
  - Copy these prompts directly into Cursor!

#### Technical Specifications
- **`03-API-DOCUMENTATION.md`**
  - Backend API endpoints
  - Request/response formats
  - Example code in Python & JavaScript

- **`04-SCRAPER-GUIDE.md`**
  - YTS website structure analysis
  - Complete scraper implementation
  - CSS selectors reference
  - Error handling strategies

- **`05-UI-DESIGN.md`**
  - Complete UI wireframes
  - Color palette & typography
  - Component specifications
  - Responsive layouts

#### Building & Deployment
- **`06-DEPLOYMENT.md`**
  - Building Windows executable with PyInstaller
  - Creating installer with Inno Setup
  - Code signing (optional)
  - Release process

---

## 🚀 Quick Start (3 Steps)

### Step 1: Read the Guides (30 min)
1. Open `CURSOR-GUIDE.md` - Learn how to use Cursor AI
2. Skim `00-PROJECT-OVERVIEW.md` - Understand the architecture
3. Open `02-DEVELOPMENT-STEPS.md` - See all the build prompts

### Step 2: Setup Environment (30 min)
Follow `01-SETUP-GUIDE.md`:
1. Install Python 3.11+
2. Create virtual environment
3. Install dependencies
4. Verify setup

### Step 3: Start Building! (5-7 days)
Use `02-DEVELOPMENT-STEPS.md`:
1. Copy prompts into Cursor AI
2. Build phase by phase
3. Test after each phase
4. Deploy when complete

---

## 📅 Development Timeline

### Week 1: Core Features
- **Day 1**: Database + Models
- **Day 2**: Web Scraper
- **Day 3**: Backend API + Torrent Manager
- **Day 4-5**: Desktop UI (PyQt6)
- **Day 6**: Testing & Bug Fixes
- **Day 7**: Build & Deploy

### Total Time
- **Experienced Developer**: 5-7 days
- **Beginner**: 10-14 days (with learning)

---

## 🎯 Your Requirements Checklist

Based on your specifications:

- [x] Target website: YTS (yts-official.cc)
- [x] Platform: Windows desktop (future: mobile)
- [x] Auto-refresh every 30 minutes
- [x] Local drive storage
- [x] User chooses quality
- [x] Download notifications
- [x] Filter by genre and year

**Everything you asked for is documented and ready to build!**

---

## 📁 Project File Structure

Once built, your project will look like this:

```
yts-movie-monitor/
│
├── CURSOR-GUIDE.md          ← How to use Cursor AI
├── README.md                 ← Project overview
│
├── docs/                     ← All documentation
│   ├── 00-PROJECT-OVERVIEW.md
│   ├── 01-SETUP-GUIDE.md
│   ├── 02-DEVELOPMENT-STEPS.md  ⭐ Main build guide
│   ├── 03-API-DOCUMENTATION.md
│   ├── 04-SCRAPER-GUIDE.md
│   ├── 05-UI-DESIGN.md
│   └── 06-DEPLOYMENT.md
│
├── backend/                  ← Flask API server
│   ├── app.py
│   ├── scraper.py
│   ├── torrent_manager.py
│   ├── database.py
│   └── config.py
│
├── frontend/                 ← PyQt6 desktop app
│   ├── main.py
│   ├── ui/                   ← UI components
│   ├── assets/               ← Icons, styles
│   └── utils/                ← Helpers
│
├── shared/                   ← Shared code
│   ├── models.py
│   └── constants.py
│
├── tests/                    ← Unit tests
├── data/                     ← Database & cache
└── downloads/                ← Downloaded movies
```

---

## 🎓 How to Use This Project

### For Building with Cursor AI

1. **Read** `CURSOR-GUIDE.md`
2. **Setup** environment using `01-SETUP-GUIDE.md`
3. **Build** using prompts from `02-DEVELOPMENT-STEPS.md`
4. **Reference** other docs as needed
5. **Deploy** using `06-DEPLOYMENT.md`

### For Understanding the Architecture

1. Start with `00-PROJECT-OVERVIEW.md`
2. Review `03-API-DOCUMENTATION.md`
3. Study `04-SCRAPER-GUIDE.md`
4. Check `05-UI-DESIGN.md`

### For Deployment

1. Build the app (following dev steps)
2. Test thoroughly
3. Follow `06-DEPLOYMENT.md`
4. Create installer
5. Distribute!

---

## 💡 Key Features of This Documentation

### ✅ Complete & Detailed
- Every component specified
- No guesswork needed
- Ready for Cursor AI

### ✅ Step-by-Step
- Organized in logical order
- Test points after each phase
- Clear dependencies

### ✅ Cursor-Optimized
- Prompts ready to copy/paste
- File paths included
- Context provided

### ✅ Professional
- Industry best practices
- Error handling
- Testing strategies
- Deployment process

---

## 🎯 Success Metrics

By following this documentation, you will build:

✅ A fully functional desktop application  
✅ Auto-scraping YTS website  
✅ Beautiful modern UI  
✅ Integrated torrent downloads  
✅ Real-time progress tracking  
✅ Desktop notifications  
✅ Configurable settings  
✅ Windows executable  
✅ Professional installer  

---

## 🆘 Getting Help

### While Building

1. **Check the relevant doc** - All answers are in the guides
2. **Ask Cursor AI** - "Explain this code" or "Fix this error"
3. **Review examples** - Code examples in every guide
4. **Test incrementally** - Don't build everything at once

### Common Issues

- **Setup problems** → See `01-SETUP-GUIDE.md` troubleshooting
- **Scraper not working** → See `04-SCRAPER-GUIDE.md` error handling
- **UI not displaying** → See `05-UI-DESIGN.md` specifications
- **Build failing** → See `06-DEPLOYMENT.md` troubleshooting

---

## 📊 Documentation Stats

- **Total Pages**: ~100+ pages of documentation
- **Code Examples**: 50+ code snippets
- **Cursor Prompts**: 20+ ready-to-use prompts
- **Diagrams**: Architecture diagrams, UI wireframes
- **APIs**: 15+ documented endpoints

---

## 🎉 Ready to Start?

### Your Next Steps:

1. ✅ Read `CURSOR-GUIDE.md` (15 min)
2. ✅ Setup environment via `01-SETUP-GUIDE.md` (30 min)
3. ✅ Open `02-DEVELOPMENT-STEPS.md` in Cursor
4. ✅ Copy first prompt (STEP 1.1)
5. ✅ Paste into Cursor AI
6. ✅ Start building! 🚀

---

## 📞 Project Info

- **Version**: 1.0.0
- **Platform**: Windows 10/11
- **Language**: Python 3.11+
- **Framework**: PyQt6
- **License**: Personal Use Only

---

## 🌟 Features You'll Build

### Core
- [x] YTS web scraping
- [x] Movie database (SQLite)
- [x] Filter by genre/year/quality
- [x] Search functionality
- [x] Torrent downloads
- [x] Progress tracking

### UI
- [x] Dark theme interface
- [x] Movie grid view
- [x] Movie details dialog
- [x] Download manager
- [x] Settings panel
- [x] Status bar

### Advanced
- [x] Auto-scraping (30 min)
- [x] Desktop notifications
- [x] Poster caching
- [x] Download queue
- [x] Pause/Resume downloads
- [x] Custom download location

---

## 💪 You've Got This!

This documentation gives you **everything you need** to build a professional desktop application. Every line of code, every component, every feature is documented and ready to build with Cursor AI.

**Time to start building! 🎬**

---

**Start Here Version**: 1.0  
**Last Updated**: February 2026  
**Next Steps**: Open `CURSOR-GUIDE.md`
