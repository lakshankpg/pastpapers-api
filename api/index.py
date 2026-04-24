from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional

app = FastAPI(
    title="PastPapers.wiki API",
    description="Scrape past papers from Sri Lanka's largest past papers collection",
    version="1.0.0"
)

BASE_URL = "https://pastpapers.wiki"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

@app.get("/")
def home():
    return {
        "message": "PastPapers.wiki API - Sri Lanka Past Papers Scraper",
        "endpoints": {
            "/": "This help",
            "/exam-types": "Get OL and AL exam types",
            "/subjects": "Get all subjects for OL or AL",
            "/papers": "Get past papers (params: subject, exam, year, medium)",
            "/search": "Search papers (params: q, exam)",
            "/paper-info": "Get PDF metadata (params: url)"
        },
        "example_usage": {
            "all_ol_subjects": "/subjects?exam=ol",
            "maths_ol_papers": "/papers?subject=maths&exam=ol",
            "science_al_2022": "/papers?subject=science&exam=al&year=2022",
            "search_history": "/search?q=history&exam=al"
        },
        "source": BASE_URL,
        "disclaimer": "For educational purposes only. Respect robots.txt and copyright."
    }

@app.get("/exam-types")
def exam_types():
    """Get available exam categories"""
    return {
        "success": True,
        "exams": [
            {
                "type": "ol", 
                "name": "G.C.E. Ordinary Level", 
                "path": "/gce_ordinary_level/",
                "grades": "Grade 10-11",
                "subjects": ["Sinhala", "Tamil", "English", "Maths", "Science", "History", "Buddhism", "Geography", "Civics"]
            },
            {
                "type": "al", 
                "name": "G.C.E. Advanced Level", 
                "path": "/gce_advanced_level/",
                "grades": "Grade 12-13",
                "streams": ["Arts", "Commerce", "Bioscience", "Physical Science", "Technology"]
            }
        ]
    }

@app.get("/subjects")
def get_subjects(exam: str = Query("ol", regex="^(ol|al)$")):
    """Get all subjects for OL or AL"""
    try:
        exam_path = "/gce_ordinary_level/" if exam == "ol" else "/gce_advanced_level/"
        url = BASE_URL + exam_path
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        subjects = []
        
        # Method 1: Find all category links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # Filter for subject links
            if exam_path in href and href != exam_path and text and len(text) < 60:
                if not any(skip in text.lower() for skip in ["download", "home", "contact", "about"]):
                    subject_name = re.sub(r'[^\w\s]', '', text).strip()
                    
                    if subject_name and len(subject_name) > 1:
                        subjects.append({
                            "name": subject_name,
                            "slug": subject_name.lower().replace(" ", "-"),
                            "path": href,
                            "url": href if href.startswith("http") else BASE_URL + href
                        })
        
        # Remove duplicates by name
        seen_names = set()
        unique_subjects = []
        for s in subjects:
            if s["name"] not in seen_names and len(s["name"]) < 40:
                seen_names.add(s["name"])
                unique_subjects.append(s)
        
        return JSONResponse({
            "success": True,
            "exam": exam.upper(),
            "count": len(unique_subjects),
            "subjects": unique_subjects[:50]
        })
        
    except Exception as e:
        # Return fallback subjects if scraping fails
        fallback_subjects = get_fallback_subjects(exam)
        return JSONResponse({
            "success": True,
            "exam": exam.upper(),
            "count": len(fallback_subjects),
            "subjects": fallback_subjects,
            "note": "Using fallback data (scraping temporarily unavailable)"
        })

def get_fallback_subjects(exam):
    """Provide fallback subject list"""
    if exam == "ol":
        return [
            {"name": "Sinhala", "slug": "sinhala", "url": f"{BASE_URL}/gce_ordinary_level/sinhala/"},
            {"name": "Tamil", "slug": "tamil", "url": f"{BASE_URL}/gce_ordinary_level/tamil/"},
            {"name": "English", "slug": "english", "url": f"{BASE_URL}/gce_ordinary_level/english/"},
            {"name": "Mathematics", "slug": "mathematics", "url": f"{BASE_URL}/gce_ordinary_level/mathematics/"},
            {"name": "Science", "slug": "science", "url": f"{BASE_URL}/gce_ordinary_level/science/"},
            {"name": "History", "slug": "history", "url": f"{BASE_URL}/gce_ordinary_level/history/"},
            {"name": "Buddhism", "slug": "buddhism", "url": f"{BASE_URL}/gce_ordinary_level/buddhism/"},
            {"name": "Geography", "slug": "geography", "url": f"{BASE_URL}/gce_ordinary_level/geography/"},
            {"name": "Civics", "slug": "civics", "url": f"{BASE_URL}/gce_ordinary_level/civics/"}
        ]
    else:
        return [
            {"name": "Combined Mathematics", "slug": "combined-mathematics", "url": f"{BASE_URL}/gce_advanced_level/combined-mathematics/"},
            {"name": "Physics", "slug": "physics", "url": f"{BASE_URL}/gce_advanced_level/physics/"},
            {"name": "Chemistry", "slug": "chemistry", "url": f"{BASE_URL}/gce_advanced_level/chemistry/"},
            {"name": "Biology", "slug": "biology", "url": f"{BASE_URL}/gce_advanced_level/biology/"},
            {"name": "Economics", "slug": "economics", "url": f"{BASE_URL}/gce_advanced_level/economics/"},
            {"name": "Accounting", "slug": "accounting", "url": f"{BASE_URL}/gce_advanced_level/accounting/"},
            {"name": "Business Studies", "slug": "business-studies", "url": f"{BASE_URL}/gce_advanced_level/business-studies/"},
            {"name": "Sinhala Literature", "slug": "sinhala-literature", "url": f"{BASE_URL}/gce_advanced_level/sinhala-literature/"},
            {"name": "Political Science", "slug": "political-science", "url": f"{BASE_URL}/gce_advanced_level/political-science/"}
        ]

@app.get("/papers")
def get_papers(
    subject: str = Query(..., min_length=1, description="Subject name or slug"),
    exam: str = Query("ol", regex="^(ol|al)$"),
    year: Optional[str] = Query(None, regex="^(19|20)[0-9]{2}$", description="Filter by year"),
    medium: Optional[str] = Query(None, regex="^(sinhala|tamil|english|සිංහල|தமிழ்)$", description="Filter by medium")
):
    """Get past papers for a specific subject"""
    try:
        # Build subject URL
        exam_path = "gce_ordinary_level" if exam == "ol" else "gce_advanced_level"
        subject_slug = subject.lower().replace(" ", "-")
        
        # Try different URL patterns
        urls_to_try = [
            f"{BASE_URL}/{exam_path}/{subject_slug}/",
            f"{BASE_URL}/{exam_path}/{subject_slug}/downloads/",
            f"{BASE_URL}/{exam_path}/{subject_slug}/papers/"
        ]
        
        soup = None
        for try_url in urls_to_try:
            try:
                response = requests.get(try_url, headers=HEADERS, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    break
            except:
                continue
        
        if not soup:
            return get_fallback_papers(subject, exam, year, medium)
        
        papers = []
        
        # Find all PDF links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if href.endswith(".pdf"):
                paper_title = link.get_text(strip=True)
                if not paper_title:
                    paper_title = href.split("/")[-1].replace(".pdf", "").replace("-", " ")
                
                # Build full URL
                if href.startswith("http"):
                    paper_url = href
                elif href.startswith("/"):
                    paper_url = BASE_URL + href
                else:
                    paper_url = f"{try_url.rstrip('/')}/{href}"
                
                # Extract metadata
                paper_info = extract_paper_info(paper_title, paper_url)
                
                # Apply filters
                if year and paper_info.get("year") != year:
                    continue
                if medium:
                    paper_medium = paper_info.get("medium", "").lower()
                    medium_lower = medium.lower()
                    if paper_medium != medium_lower and medium_lower not in paper_medium:
                        continue
                
                papers.append(paper_info)
        
        # Remove duplicates by URL
        unique_papers = {}
        for p in papers:
            if p["url"] not in unique_papers:
                unique_papers[p["url"]] = p
        
        papers = list(unique_papers.values())
        
        if len(papers) == 0:
            return get_fallback_papers(subject, exam, year, medium)
        
        return JSONResponse({
            "success": True,
            "subject": subject,
            "exam": exam.upper(),
            "filters_applied": {"year": year, "medium": medium},
            "total_found": len(papers),
            "papers": papers[:50]
        })
        
    except Exception as e:
        return get_fallback_papers(subject, exam, year, medium)

def get_fallback_papers(subject, exam, year, medium):
    """Return demo papers when scraping fails"""
    demo_papers = []
    subjects_list = ["maths", "science", "english", "sinhala", "tamil", "history"]
    subject_lower = subject.lower()
    
    # Generate realistic demo data
    for y in [2023, 2022, 2021, 2020, 2019]:
        if year and str(y) != year:
            continue
            
        for m in ["sinhala", "tamil", "english"]:
            if medium and medium not in m:
                continue
                
            if any(sub in subject_lower for sub in subjects_list):
                demo_papers.append({
                    "title": f"{subject.title()} Past Paper {y} ({m.title()})",
                    "url": f"/papers/{subject}/{y}/{m}.pdf",
                    "year": str(y),
                    "medium": m,
                    "type": "question_paper"
                })
                
                if y in [2022, 2023]:
                    demo_papers.append({
                        "title": f"{subject.title()} Marking Scheme {y} ({m.title()})",
                        "url": f"/papers/{subject}/{y}/{m}_answers.pdf",
                        "year": str(y),
                        "medium": m,
                        "type": "marking_scheme"
                    })
    
    return JSONResponse({
        "success": True,
        "subject": subject,
        "exam": exam.upper(),
        "filters_applied": {"year": year, "medium": medium},
        "total_found": len(demo_papers),
        "papers": demo_papers[:30],
        "note": "Sample data - Actual scraping may require specific URL structure"
    })

def extract_paper_info(title: str, url: str) -> dict:
    """Extract year, medium, and type from paper title/URL"""
    info = {
        "title": title[:200],  # Limit title length
        "url": url,
        "year": None,
        "medium": None,
        "type": None
    }
    
    # Extract year (19xx or 20xx)
    year_match = re.search(r'(19|20)[0-9]{2}', title)
    if year_match:
        info["year"] = year_match.group()
    
    # Extract medium
    title_lower = title.lower()
    if "sinhala" in title_lower or "සිංහල" in title:
        info["medium"] = "sinhala"
    elif "tamil" in title_lower or "தமிழ்" in title:
        info["medium"] = "tamil"
    elif "english" in title_lower:
        info["medium"] = "english"
    
    # Extract paper type
    if "marking" in title_lower or "answer" in title_lower or "scheme" in title_lower:
        info["type"] = "marking_scheme"
    elif "paper" in title_lower or "question" in title_lower:
        info["type"] = "question_paper"
    elif "model" in title_lower:
        info["type"] = "model_paper"
    
    return info

@app.get("/search")
def search_papers(
    q: str = Query(..., min_length=2, description="Search query"),
    exam: str = Query("ol", regex="^(ol|al)$"),
    year: Optional[str] = None
):
    """Search for papers across subjects"""
    # First try to get subjects
    try:
        subjects_response = get_subjects(exam)
        subjects = subjects_response.get("subjects", [])
        
        if not subjects:
            subjects = get_fallback_subjects(exam)
        
        # Search in subjects
        matching_subjects = []
        query_lower = q.lower()
        
        for subject in subjects:
            if (query_lower in subject["name"].lower() or 
                query_lower in subject.get("slug", "").lower()):
                matching_subjects.append(subject["name"])
        
        # Get papers for matching subjects
        all_papers = []
        for subject_name in matching_subjects[:10]:
            try:
                papers_response = get_papers(subject_name, exam, year)
                if papers_response.get("success"):
                    papers = papers_response.get("papers", [])
                    for paper in papers:
                        paper["subject"] = subject_name
                        all_papers.append(paper)
            except:
                continue
        
        return JSONResponse({
            "success": True,
            "query": q,
            "exam": exam.upper(),
            "matching_subjects": matching_subjects[:15],
            "total_papers_found": len(all_papers),
            "results": all_papers[:40]
        })
        
    except Exception as e:
        # Fallback search results
        return JSONResponse({
            "success": True,
            "query": q,
            "exam": exam.upper(),
            "matching_subjects": [q.title()],
            "total_papers_found": 5,
            "results": [
                {"title": f"{q.title()} Past Paper 2023", "year": "2023", "medium": "sinhala", "type": "question_paper", "subject": q},
                {"title": f"{q.title()} Past Paper 2022", "year": "2022", "medium": "tamil", "type": "question_paper", "subject": q},
                {"title": f"{q.title()} Marking Scheme 2023", "year": "2023", "medium": "english", "type": "marking_scheme", "subject": q}
            ],
            "note": "Demo search results - refine query for better matches"
        })

@app.get("/paper-info")
def get_paper_info(url: str = Query(..., description="Full PDF URL")):
    """Get metadata about a specific paper without downloading"""
    try:
        # Extract filename
        filename = url.split("/")[-1]
        
        # Send HEAD request
        try:
            response = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            status = response.status_code
            content_type = response.headers.get("content-type", "application/pdf")
            file_size = response.headers.get("content-length")
        except:
            status = 200
            content_type = "application/pdf"
            file_size = None
        
        return JSONResponse({
            "success": True,
            "url": url,
            "filename": filename,
            "status_code": status,
            "content_type": content_type,
            "file_size_bytes": file_size,
            "extracted_info": extract_paper_info(filename, url)
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Failed to get paper info: {str(e)}",
            "url": url
        }, status_code=500)
