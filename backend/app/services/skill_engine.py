import re
import io
import uuid
from typing import List, Dict, Any, Optional, Tuple, Set
from pypdf import PdfReader
from docx import Document

# ----------------------------------------------------
# 1. INDUSTRY SKILL TAXONOMY & ROLE WEIGHTS
# ----------------------------------------------------

# Weights:
# Tier 1 (Mandatory Core Language / Primary Framework): 1.5
# Tier 2 (Standard Core Database / Architecture / Tooling): 1.0
# Tier 3 (Secondary / Optional / Specialized): 0.5

ROLE_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "Full Stack Developer": {
        "core_skills": {
            "JavaScript": 1.5,
            "TypeScript": 1.5,
            "React": 1.5,
            "Node.js": 1.5,
            "Python": 1.5,
            "FastAPI": 1.5,
            "MongoDB": 1.0,
            "SQL": 1.0,
            "Git": 1.0,
            "REST API": 1.0,
            "Docker": 1.0
        },
        "optional_skills": {
            "Next.js": 0.5,
            "PostgreSQL": 0.5,
            "Redis": 0.5,
            "GraphQL": 0.5,
            "Tailwind CSS": 0.5,
            "CI/CD": 0.5,
            "AWS": 0.5,
            "System Design": 0.5
        },
        "categories": {
            "Frontend": ["React", "JavaScript", "TypeScript", "Next.js", "Tailwind CSS", "HTML5", "CSS3", "Vue.js", "Redux"],
            "Backend": ["Python", "Node.js", "FastAPI", "Django", "Express", "REST API", "GraphQL", "Go"],
            "Database & Cloud": ["MongoDB", "PostgreSQL", "MySQL", "Redis", "Docker", "AWS", "Git", "Kubernetes"],
            "Engineering & Architecture": ["System Design", "Microservices", "Data Structures", "Algorithms", "CI/CD", "Testing"]
        }
    },
    "Frontend Developer": {
        "core_skills": {
            "JavaScript": 1.5,
            "TypeScript": 1.5,
            "React": 1.5,
            "HTML5": 1.0,
            "CSS3": 1.0,
            "Tailwind CSS": 1.0,
            "Git": 1.0,
            "REST API": 1.0,
            "Responsive Design": 1.0
        },
        "optional_skills": {
            "Next.js": 0.5,
            "Vue.js": 0.5,
            "Redux": 0.5,
            "Webpack": 0.5,
            "Vite": 0.5,
            "Performance Optimization": 0.5,
            "Jest": 0.5,
            "GraphQL": 0.5
        },
        "categories": {
            "Core Frontend": ["JavaScript", "TypeScript", "HTML5", "CSS3", "Responsive Design"],
            "Frameworks": ["React", "Next.js", "Vue.js", "Redux", "Tailwind CSS"],
            "Tooling & APIs": ["Git", "REST API", "GraphQL", "Webpack", "Vite", "Jest"],
            "User Experience": ["UI/UX Design", "Performance Optimization", "Accessibility (a11y)"]
        }
    },
    "Backend Developer": {
        "core_skills": {
            "Python": 1.5,
            "FastAPI": 1.5,
            "Node.js": 1.5,
            "SQL": 1.5,
            "MongoDB": 1.0,
            "PostgreSQL": 1.0,
            "Git": 1.0,
            "REST API": 1.0,
            "Docker": 1.0
        },
        "optional_skills": {
            "Django": 0.5,
            "Express": 0.5,
            "Redis": 0.5,
            "Kafka": 0.5,
            "Microservices": 0.5,
            "Kubernetes": 0.5,
            "AWS": 0.5,
            "System Design": 0.5
        },
        "categories": {
            "Languages & Frameworks": ["Python", "FastAPI", "Node.js", "Django", "Express", "Go", "Java"],
            "Databases & Storage": ["MongoDB", "PostgreSQL", "MySQL", "Redis", "SQL"],
            "Cloud & DevOps": ["Docker", "Kubernetes", "AWS", "Git", "CI/CD", "Linux"],
            "Architecture": ["System Design", "Microservices", "REST API", "GraphQL", "Event-Driven"]
        }
    },
    "Data Scientist / AI Engineer": {
        "core_skills": {
            "Python": 1.5,
            "Machine Learning": 1.5,
            "Pandas": 1.5,
            "NumPy": 1.0,
            "Scikit-Learn": 1.5,
            "SQL": 1.0,
            "Deep Learning": 1.0,
            "Git": 1.0
        },
        "optional_skills": {
            "PyTorch": 0.5,
            "TensorFlow": 0.5,
            "FastAPI": 0.5,
            "Docker": 0.5,
            "NLP": 0.5,
            "Computer Vision": 0.5,
            "Data Visualization": 0.5,
            "BigQuery": 0.5
        },
        "categories": {
            "Programming & Math": ["Python", "SQL", "Linear Algebra", "Statistics", "NumPy"],
            "Machine Learning": ["Machine Learning", "Scikit-Learn", "Pandas", "Feature Engineering"],
            "Deep Learning & AI": ["Deep Learning", "PyTorch", "TensorFlow", "NLP", "Transformers", "Computer Vision"],
            "Deployment & Data": ["FastAPI", "Docker", "Git", "Data Visualization", "BigQuery"]
        }
    },
    "DevOps / Cloud Engineer": {
        "core_skills": {
            "Linux": 1.5,
            "Docker": 1.5,
            "Kubernetes": 1.5,
            "AWS": 1.5,
            "CI/CD": 1.5,
            "Git": 1.0,
            "Python": 1.0,
            "Terraform": 1.0,
            "Bash": 1.0
        },
        "optional_skills": {
            "Ansible": 0.5,
            "GCP": 0.5,
            "Azure": 0.5,
            "Prometheus": 0.5,
            "Grafana": 0.5,
            "Networking": 0.5,
            "Security": 0.5
        },
        "categories": {
            "Containers & Orchestration": ["Docker", "Kubernetes", "Helm"],
            "Cloud Platforms": ["AWS", "Azure", "GCP", "Terraform"],
            "Automation & CI/CD": ["CI/CD", "Git", "Jenkins", "GitHub Actions", "Ansible"],
            "Systems & Monitoring": ["Linux", "Bash", "Python", "Prometheus", "Grafana", "Networking"]
        }
    }
}

ALL_KNOWN_SKILLS: Dict[str, Dict[str, str]] = {
    # Languages
    "python": {"name": "Python", "category": "Technical", "type": "Language"},
    "javascript": {"name": "JavaScript", "category": "Technical", "type": "Language"},
    "typescript": {"name": "TypeScript", "category": "Technical", "type": "Language"},
    "java": {"name": "Java", "category": "Technical", "type": "Language"},
    "c++": {"name": "C++", "category": "Technical", "type": "Language"},
    "c#": {"name": "C#", "category": "Technical", "type": "Language"},
    "go": {"name": "Go", "category": "Technical", "type": "Language"},
    "golang": {"name": "Go", "category": "Technical", "type": "Language"},
    "sql": {"name": "SQL", "category": "Technical", "type": "Language"},
    "html": {"name": "HTML5", "category": "Technical", "type": "Markup"},
    "html5": {"name": "HTML5", "category": "Technical", "type": "Markup"},
    "css": {"name": "CSS3", "category": "Technical", "type": "Style"},
    "css3": {"name": "CSS3", "category": "Technical", "type": "Style"},
    "bash": {"name": "Bash", "category": "Technical", "type": "Scripting"},

    # Frameworks & Libraries
    "react": {"name": "React", "category": "Frameworks & Libraries", "type": "Frontend"},
    "react.js": {"name": "React", "category": "Frameworks & Libraries", "type": "Frontend"},
    "reactjs": {"name": "React", "category": "Frameworks & Libraries", "type": "Frontend"},
    "next.js": {"name": "Next.js", "category": "Frameworks & Libraries", "type": "Fullstack"},
    "nextjs": {"name": "Next.js", "category": "Frameworks & Libraries", "type": "Fullstack"},
    "vue": {"name": "Vue.js", "category": "Frameworks & Libraries", "type": "Frontend"},
    "vue.js": {"name": "Vue.js", "category": "Frameworks & Libraries", "type": "Frontend"},
    "tailwind": {"name": "Tailwind CSS", "category": "Frameworks & Libraries", "type": "CSS"},
    "tailwind css": {"name": "Tailwind CSS", "category": "Frameworks & Libraries", "type": "CSS"},
    "node": {"name": "Node.js", "category": "Frameworks & Libraries", "type": "Backend"},
    "node.js": {"name": "Node.js", "category": "Frameworks & Libraries", "type": "Backend"},
    "nodejs": {"name": "Node.js", "category": "Frameworks & Libraries", "type": "Backend"},
    "fastapi": {"name": "FastAPI", "category": "Frameworks & Libraries", "type": "Backend"},
    "django": {"name": "Django", "category": "Frameworks & Libraries", "type": "Backend"},
    "flask": {"name": "Flask", "category": "Frameworks & Libraries", "type": "Backend"},
    "express": {"name": "Express", "category": "Frameworks & Libraries", "type": "Backend"},
    "express.js": {"name": "Express", "category": "Frameworks & Libraries", "type": "Backend"},
    "spring": {"name": "Spring Boot", "category": "Frameworks & Libraries", "type": "Backend"},
    "spring boot": {"name": "Spring Boot", "category": "Frameworks & Libraries", "type": "Backend"},
    "redux": {"name": "Redux", "category": "Frameworks & Libraries", "type": "State Management"},
    "pandas": {"name": "Pandas", "category": "Frameworks & Libraries", "type": "Data Science"},
    "numpy": {"name": "NumPy", "category": "Frameworks & Libraries", "type": "Data Science"},
    "scikit-learn": {"name": "Scikit-Learn", "category": "Frameworks & Libraries", "type": "Machine Learning"},
    "sklearn": {"name": "Scikit-Learn", "category": "Frameworks & Libraries", "type": "Machine Learning"},
    "pytorch": {"name": "PyTorch", "category": "Frameworks & Libraries", "type": "Deep Learning"},
    "tensorflow": {"name": "TensorFlow", "category": "Frameworks & Libraries", "type": "Deep Learning"},

    # Databases & Cloud
    "mongodb": {"name": "MongoDB", "category": "Databases & Cloud", "type": "NoSQL Database"},
    "postgresql": {"name": "PostgreSQL", "category": "Databases & Cloud", "type": "Relational Database"},
    "postgres": {"name": "PostgreSQL", "category": "Databases & Cloud", "type": "Relational Database"},
    "mysql": {"name": "MySQL", "category": "Databases & Cloud", "type": "Relational Database"},
    "redis": {"name": "Redis", "category": "Databases & Cloud", "type": "Cache/NoSQL"},
    "docker": {"name": "Docker", "category": "Databases & Cloud", "type": "Containerization"},
    "kubernetes": {"name": "Kubernetes", "category": "Databases & Cloud", "type": "Orchestration"},
    "aws": {"name": "AWS", "category": "Databases & Cloud", "type": "Cloud"},
    "azure": {"name": "Azure", "category": "Databases & Cloud", "type": "Cloud"},
    "gcp": {"name": "Google Cloud", "category": "Databases & Cloud", "type": "Cloud"},
    "git": {"name": "Git", "category": "Databases & Cloud", "type": "Version Control"},
    "github": {"name": "Git", "category": "Databases & Cloud", "type": "Version Control"},
    "ci/cd": {"name": "CI/CD", "category": "Databases & Cloud", "type": "DevOps"},
    "terraform": {"name": "Terraform", "category": "Databases & Cloud", "type": "IaC"},
    "linux": {"name": "Linux", "category": "Databases & Cloud", "type": "Operating System"},

    # Concepts & Architecture
    "rest api": {"name": "REST API", "category": "Technical", "type": "Architecture"},
    "restful": {"name": "REST API", "category": "Technical", "type": "Architecture"},
    "graphql": {"name": "GraphQL", "category": "Technical", "type": "API"},
    "system design": {"name": "System Design", "category": "Technical", "type": "Architecture"},
    "microservices": {"name": "Microservices", "category": "Technical", "type": "Architecture"},
    "machine learning": {"name": "Machine Learning", "category": "Technical", "type": "AI"},
    "deep learning": {"name": "Deep Learning", "category": "Technical", "type": "AI"},
    "nlp": {"name": "NLP", "category": "Technical", "type": "AI"},
    "data structures": {"name": "Data Structures", "category": "Technical", "type": "Computer Science"},
    "algorithms": {"name": "Algorithms", "category": "Technical", "type": "Computer Science"},
    "responsive design": {"name": "Responsive Design", "category": "Technical", "type": "Frontend UI"},
    "responsive designs": {"name": "Responsive Design", "category": "Technical", "type": "Frontend UI"},

    # Soft Skills & Methodologies
    "agile": {"name": "Agile Methodology", "category": "Soft Skills", "type": "Methodology"},
    "scrum": {"name": "Agile Methodology", "category": "Soft Skills", "type": "Methodology"},
    "problem solving": {"name": "Problem Solving", "category": "Soft Skills", "type": "Cognitive"},
    "communication": {"name": "Communication", "category": "Soft Skills", "type": "Interpersonal"},
    "teamwork": {"name": "Team Collaboration", "category": "Soft Skills", "type": "Interpersonal"},
    "team collaboration": {"name": "Team Collaboration", "category": "Soft Skills", "type": "Interpersonal"},
    "leadership": {"name": "Leadership", "category": "Soft Skills", "type": "Interpersonal"}
}

# ----------------------------------------------------
# 2. SKILL PREREQUISITE DIRECTED ACYCLIC GRAPH (DAG)
# ----------------------------------------------------

PREREQUISITE_GRAPH: Dict[str, List[str]] = {
    # Foundational Programming & Tools
    "Python": [],
    "JavaScript": [],
    "HTML5": [],
    "CSS3": [],
    "SQL": [],
    "Git": [],
    "Linux": [],
    "Bash": ["Linux"],

    # Frontend Stack
    "TypeScript": ["JavaScript"],
    "Responsive Design": ["HTML5", "CSS3"],
    "Tailwind CSS": ["CSS3"],
    "React": ["JavaScript", "HTML5", "CSS3"],
    "Redux": ["React", "JavaScript"],
    "Next.js": ["React", "TypeScript"],
    "Vue.js": ["JavaScript", "HTML5"],

    # Backend Stack & Storage
    "REST API": [],
    "FastAPI": ["Python", "REST API"],
    "Django": ["Python", "SQL"],
    "Node.js": ["JavaScript"],
    "Express": ["Node.js", "REST API"],
    "PostgreSQL": ["SQL"],
    "MySQL": ["SQL"],
    "MongoDB": [],
    "Redis": [],

    # Data Science & AI
    "NumPy": ["Python"],
    "Pandas": ["Python", "NumPy"],
    "Scikit-Learn": ["Python", "Pandas", "NumPy"],
    "Machine Learning": ["Python", "Scikit-Learn"],
    "Deep Learning": ["Machine Learning", "Python"],
    "PyTorch": ["Deep Learning", "Python"],
    "TensorFlow": ["Deep Learning", "Python"],

    # DevOps & Infrastructure
    "Docker": ["Linux"],
    "Kubernetes": ["Docker"],
    "CI/CD": ["Git", "Docker"],
    "AWS": ["Linux", "Docker"],
    "Terraform": ["AWS", "Linux"],

    # Architecture & Synthesis
    "Microservices": ["Docker", "REST API"],
    "System Design": ["REST API", "SQL", "Redis"],
    "Production Capstone": ["System Design", "CI/CD"]
}

class CycleDependencyError(ValueError):
    """Raised when a circular prerequisite dependency is detected."""
    pass

def detect_cycles(graph: Dict[str, List[str]]) -> Optional[List[str]]:
    """
    Detects circular dependencies in a prerequisite graph using 3-color DFS.
    Returns the cycle path as a list of strings if a cycle exists, or None if DAG.
    """
    # 0 = unvisited, 1 = visiting (in active recursion stack), 2 = fully visited
    visited: Dict[str, int] = {}
    cycle_nodes: List[str] = []

    def dfs(node: str, current_path: List[str]) -> bool:
        visited[node] = 1
        for prereq in graph.get(node, []):
            if visited.get(prereq, 0) == 0:
                if dfs(prereq, current_path + [prereq]):
                    return True
            elif visited.get(prereq, 0) == 1:
                # Cycle detected
                cycle_nodes.extend(current_path + [prereq])
                return True
        visited[node] = 2
        return False

    for n in list(graph.keys()):
        if visited.get(n, 0) == 0:
            if dfs(n, [n]):
                return cycle_nodes
    return None

def topological_sort_prerequisites(skills_to_schedule: List[str], graph: Optional[Dict[str, List[str]]] = None) -> List[str]:
    """
    Given a list of skills, expands prerequisites and sorts them topologically
    so that foundational skills always precede dependent skills.
    """
    if graph is None:
        graph = PREREQUISITE_GRAPH

    cycle = detect_cycles(graph)
    if cycle:
        raise CycleDependencyError(f"Prerequisite cycle detected in skill graph: {' -> '.join(cycle)}")

    # Expand to include direct prerequisites of skills_to_schedule
    all_needed: Set[str] = set()
    
    def collect(skill: str):
        if skill not in all_needed:
            all_needed.add(skill)
            for p in graph.get(skill, []):
                collect(p)

    for s in skills_to_schedule:
        collect(s)

    # Perform Kahn's / In-degree topological sort
    in_degree: Dict[str, int] = {k: 0 for k in all_needed}
    for node in all_needed:
        for prereq in graph.get(node, []):
            if prereq in all_needed:
                in_degree[node] = in_degree.get(node, 0) + 1

    # Queue of nodes with in_degree 0 (prerequisites that require nothing else in this set)
    queue = [n for n in all_needed if in_degree[n] == 0]
    sorted_skills = []

    while queue:
        # Sort queue alphabetically for determinism
        queue.sort()
        curr = queue.pop(0)
        sorted_skills.append(curr)

        for dependent, prereqs in graph.items():
            if dependent in all_needed and curr in prereqs:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    if len(sorted_skills) != len(all_needed):
        raise CycleDependencyError("Topological sort could not resolve all dependencies due to an internal cycle.")

    return sorted_skills

# ----------------------------------------------------
# 3. RESUME TEXT & SKILL EXTRACTION
# ----------------------------------------------------

# Negation and aspiration phrases that should NOT be counted as acquired skills
NEGATION_PATTERNS = [
    r'no\s+(?:prior\s+)?experience\s+(?:in|with)',
    r'not\s+familiar\s+with',
    r'lacks?\s+(?:experience\s+in|knowledge\s+of)',
    r'without\s+(?:any\s+)?experience\s+(?:in|with)',
    r'interested\s+in\s+learning',
    r'looking\s+to\s+learn',
    r'want\s+to\s+learn',
    r'aiming\s+to\s+learn',
    r'seeking\s+(?:training|mentorship|guidance)\s+in',
    r'plan(?:ning)?\s+to\s+learn',
    r'hoping\s+to\s+learn',
    r'basic\s+desire\s+to\s+study'
]

def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Uploaded file payload is empty (0 bytes).")

    ext = filename.lower().split('.')[-1]
    text = ""
    try:
        if ext == 'pdf':
            reader = PdfReader(io.BytesIO(file_bytes))
            if len(reader.pages) == 0:
                raise ValueError("PDF document contains no readable pages.")
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif ext in ['docx', 'doc']:
            doc = Document(io.BytesIO(file_bytes))
            for p in doc.paragraphs:
                if p.text:
                    text += p.text + "\n"
        elif ext in ['txt', 'md']:
            text = file_bytes.decode('utf-8', errors='ignore')
        else:
            raise ValueError(f"Unsupported file format: '.{ext}'. Supported formats are PDF, DOCX, TXT.")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to parse {ext.upper()} file: {str(e)}")

    cleaned = text.strip()
    if len(cleaned) < 10:
        raise ValueError("Extracted text is too short or unreadable to be a valid document.")
    return cleaned

def extract_skills_from_text(raw_text: str, target_role: str = "Full Stack Developer") -> List[Dict[str, Any]]:
    if not raw_text or len(raw_text.strip()) < 5:
        return []

    text_lower = raw_text.lower()
    found_skills_map: Dict[str, Dict[str, Any]] = {}

    for key, meta in ALL_KNOWN_SKILLS.items():
        # Boundary matching with lookaround:
        # Handles symbols like c++, c#, .net while preventing 'java' matching 'javascript'
        if key in ["c++", "c#", ".net"]:
            escaped_key = re.escape(key)
            pattern = r'(?<![a-zA-Z0-9])' + escaped_key + r'(?![a-zA-Z0-9])'
        else:
            pattern = r'(?<![a-zA-Z0-9_])' + re.escape(key) + r'(?![a-zA-Z0-9_])'

        matches = list(re.finditer(pattern, text_lower))
        valid_matches = []

        for m in matches:
            # Check 60 characters preceding the match for negation or aspiration context
            start_pos = max(0, m.start() - 60)
            prefix_window = text_lower[start_pos:m.start()]
            
            is_negated = False
            for neg_pat in NEGATION_PATTERNS:
                if re.search(neg_pat, prefix_window):
                    is_negated = True
                    break

            if not is_negated:
                valid_matches.append(m)

        if valid_matches:
            canonical_name = meta["name"]
            count = len(valid_matches)

            # Contextual self-declared proficiency estimation from document mentions
            if count >= 4 or any(term in text_lower for term in [f"lead {key}", f"senior {key}", f"advanced {key}", f"expert {key}"]):
                proficiency = "Advanced"
                confidence = 0.95
            elif count >= 2 or any(term in text_lower for term in [f"proficient {key}", f"experience with {key}", f"built with {key}"]):
                proficiency = "Intermediate"
                confidence = 0.85
            else:
                proficiency = "Beginner"
                confidence = 0.75

            if canonical_name not in found_skills_map:
                found_skills_map[canonical_name] = {
                    "name": canonical_name,
                    "category": meta["category"],
                    "proficiency_level": proficiency,
                    "confidence_score": confidence,
                    "source": "resume_extracted",
                    "evidence_count": count
                }
            else:
                # If duplicate alias matched, aggregate count and upgrade if higher
                found_skills_map[canonical_name]["evidence_count"] += count
                if proficiency == "Advanced":
                    found_skills_map[canonical_name]["proficiency_level"] = "Advanced"

    extracted_list = list(found_skills_map.values())
    extracted_list.sort(key=lambda x: (x["category"], x["name"]))
    return extracted_list

# ----------------------------------------------------
# 4. QUESTION BANK & ADAPTIVE ASSESSMENT
# ----------------------------------------------------

QUESTION_BANK: List[Dict[str, Any]] = [
    # FastAPI
    {
        "id": "q_fastapi_beg_1",
        "skill": "FastAPI",
        "category": "Backend",
        "difficulty": "Beginner",
        "question": "Which decorator in FastAPI registers a handler for HTTP GET requests?",
        "options": [
            "@app.get('/path')",
            "@app.route_get('/path')",
            "@app.request_get('/path')",
            "@app.fetch('/path')"
        ],
        "correct_option": 0,
        "explanation": "FastAPI uses operation decorators directly on the FastAPI app instance such as @app.get(), @app.post(), etc."
    },
    {
        "id": "q_fastapi_int_1",
        "skill": "FastAPI",
        "category": "Backend",
        "difficulty": "Intermediate",
        "question": "What is the primary benefit of using Pydantic models for request bodies in FastAPI?",
        "options": [
            "Automatic data parsing, type validation, and interactive OpenAPI schema documentation",
            "Automatic compile-time C extension optimization",
            "Direct two-way binding to relational database tables without an ORM",
            "Automatic websocket synchronization across multiple worker nodes"
        ],
        "correct_option": 0,
        "explanation": "Pydantic performs automatic data validation, conversion, and powers automatic OpenAPI (Swagger) schema generation in FastAPI."
    },
    {
        "id": "q_fastapi_adv_1",
        "skill": "FastAPI",
        "category": "Backend",
        "difficulty": "Advanced",
        "question": "In FastAPI, how does `Depends` execute cleanup code (e.g. closing database sessions) after a response is returned?",
        "options": [
            "Using a generator dependency with `yield` inside a `try...finally` block",
            "By registering a global middleware with `@app.middleware('cleanup')`",
            "By throwing an HTTPException with status code 200",
            "FastAPI does not support teardown cleanup in dependencies"
        ],
        "correct_option": 0,
        "explanation": "Dependencies using `yield` execute their pre-request code before handing over to the path operation, and their post-yield code after the response is generated."
    },

    # React
    {
        "id": "q_react_beg_1",
        "skill": "React",
        "category": "Frontend",
        "difficulty": "Beginner",
        "question": "Which React hook is used to manage local state within a functional component?",
        "options": [
            "useState",
            "useEffect",
            "useContext",
            "useRef"
        ],
        "correct_option": 0,
        "explanation": "useState declares state variables that trigger component re-renders when updated."
    },
    {
        "id": "q_react_int_1",
        "skill": "React",
        "category": "Frontend",
        "difficulty": "Intermediate",
        "question": "In React 18+, when does useEffect run by default if an empty dependency array [] is passed?",
        "options": [
            "Before the component DOM elements are rendered to the screen",
            "Once after the initial component mount",
            "On every state update and re-render cycle",
            "Synchronously before all child components mount"
        ],
        "correct_option": 1,
        "explanation": "With an empty dependency array ([]), useEffect executes once right after the initial mount of the component."
    },
    {
        "id": "q_react_adv_1",
        "skill": "React",
        "category": "Frontend",
        "difficulty": "Advanced",
        "question": "What is the purpose of React 18's `useTransition` hook?",
        "options": [
            "Marks state updates as non-urgent transitions, keeping the UI responsive to user input",
            "Executes CSS 3D transform transitions synchronously",
            "Automatically converts Class components into Functional components",
            "Forces immediate synchronous flush of pending effects"
        ],
        "correct_option": 0,
        "explanation": "useTransition lets developers differentiate between urgent updates (like typing) and non-urgent transitions (like rendering a filtered list)."
    },

    # Python
    {
        "id": "q_py_beg_1",
        "skill": "Python",
        "category": "Backend",
        "difficulty": "Beginner",
        "question": "Which built-in function returns the total number of items in a Python collection such as a list or string?",
        "options": [
            "len()",
            "count()",
            "size()",
            "length()"
        ],
        "correct_option": 0,
        "explanation": "The built-in len() function returns the length (the number of items) of an object in O(1) time."
    },
    {
        "id": "q_py_int_1",
        "skill": "Python",
        "category": "Backend",
        "difficulty": "Intermediate",
        "question": "In Python, what is the difference between asyncio coroutines and standard OS threads?",
        "options": [
            "Asyncio uses single-threaded cooperative multitasking with an event loop; OS threads use preemptive scheduling by the OS kernel",
            "Asyncio can bypass Python's GIL for CPU-bound matrix multiplication automatically",
            "Threads require no memory overhead while asyncio allocates a separate OS process for every coroutine",
            "Asyncio only works with synchronous blocking socket libraries"
        ],
        "correct_option": 0,
        "explanation": "Asyncio is built on single-threaded cooperative multitasking where the event loop manages task switching at non-blocking I/O yield points."
    },
    {
        "id": "q_py_adv_1",
        "skill": "Python",
        "category": "Backend",
        "difficulty": "Advanced",
        "question": "In Python 3.12+, how does the per-interpreter GIL behave with subinterpreters (PEP 684)?",
        "options": [
            "Each subinterpreter possesses its own independent GIL, enabling true multicore CPU parallelism across Python threads",
            "The GIL remains globally shared across all Python runtimes in the OS",
            "Subinterpreters disable automatic garbage collection entirely",
            "PEP 684 only applies to synchronous SQLite connections"
        ],
        "correct_option": 0,
        "explanation": "PEP 684 introduces a per-interpreter GIL allowing concurrent execution of Python bytecode across multiple OS threads without process IPC overhead."
    },

    # JavaScript
    {
        "id": "q_js_beg_1",
        "skill": "JavaScript",
        "category": "Frontend",
        "difficulty": "Beginner",
        "question": "Which keyword declares a block-scoped reassignable variable in modern ES6+ JavaScript?",
        "options": [
            "let",
            "var",
            "constant",
            "global"
        ],
        "correct_option": 0,
        "explanation": "let defines a block-scoped local variable, whereas var has function-level scope and is hoisted."
    },
    {
        "id": "q_js_int_1",
        "skill": "JavaScript",
        "category": "Frontend",
        "difficulty": "Intermediate",
        "question": "What will Promise.all([p1, p2, p3]) do if one of the promises (p2) rejects?",
        "options": [
            "Wait for all other promises to resolve and return only the successful ones",
            "Immediately reject with the reason of the first rejected promise",
            "Automatically retry the rejected promise up to 3 times",
            "Return an array containing null for the failed index"
        ],
        "correct_option": 1,
        "explanation": "Promise.all follows fail-fast behavior: if any promise rejects, the entire returned promise immediately rejects with that error."
    },
    {
        "id": "q_js_adv_1",
        "skill": "JavaScript",
        "category": "Frontend",
        "difficulty": "Advanced",
        "question": "In the V8 engine event loop, when are Promise microtasks executed relative to setTimeout macrotasks?",
        "options": [
            "All queued microtasks run to exhaustion at the end of each macrotask and before the next macrotask is dequeued",
            "Macrotasks always preempt queued microtasks synchronously",
            "Microtasks and macrotasks alternate execution in a 1:1 round-robin fashion",
            "Microtasks are executed in an independent background worker thread"
        ],
        "correct_option": 0,
        "explanation": "The microtask queue (Promise callbacks, queueMicrotask) has higher priority and drains completely after the current execution context and before the next macrotask runs."
    },

    # TypeScript
    {
        "id": "q_ts_beg_1",
        "skill": "TypeScript",
        "category": "Frontend",
        "difficulty": "Beginner",
        "question": "Which keyword is used in TypeScript to declare the shape and contract of an object?",
        "options": [
            "interface",
            "structure",
            "schema",
            "contract"
        ],
        "correct_option": 0,
        "explanation": "interface declares a type contract defining property names and their corresponding types for objects in TypeScript."
    },
    {
        "id": "q_ts_int_1",
        "skill": "TypeScript",
        "category": "Frontend",
        "difficulty": "Intermediate",
        "question": "What does the `keyof T` operator produce in TypeScript?",
        "options": [
            "A union type of all known, public property names of type T",
            "An array of string values containing property names at runtime",
            "A boolean checking if a key exists in object T",
            "A copy of object T with optional properties"
        ],
        "correct_option": 0,
        "explanation": "The keyof operator produces a union literal type of all string or numeric property names of a given type."
    },
    {
        "id": "q_ts_adv_1",
        "skill": "TypeScript",
        "category": "Frontend",
        "difficulty": "Advanced",
        "question": "In conditional types, what does `T extends Array<infer U> ? U : never` achieve?",
        "options": [
            "Extracts the element type U from an array type T at compile time",
            "Converts an array into a tuple of fixed length",
            "Enforces that array elements cannot be null or undefined",
            "Dynamically parses JSON strings into typed arrays at runtime"
        ],
        "correct_option": 0,
        "explanation": "The infer keyword introduces a type variable within the condition of a conditional type to extract inner types such as element types from arrays."
    },

    # Node.js
    {
        "id": "q_node_beg_1",
        "skill": "Node.js",
        "category": "Backend",
        "difficulty": "Beginner",
        "question": "Which built-in core module in Node.js provides utilities for resolving file and directory paths across operating systems?",
        "options": [
            "path",
            "fs",
            "url",
            "os"
        ],
        "correct_option": 0,
        "explanation": "The 'path' module provides utilities for working with file and directory paths (path.join, path.resolve)."
    },
    {
        "id": "q_node_int_1",
        "skill": "Node.js",
        "category": "Backend",
        "difficulty": "Intermediate",
        "question": "In Node.js, what is the architectural responsibility of `libuv`?",
        "options": [
            "Managing the event loop, cross-platform asynchronous I/O, and the underlying threadpool",
            "Executing JavaScript bytecode in a standalone JIT engine",
            "Validating JSON request bodies for Express routers",
            "Transpiling modern TypeScript code into ES5 JavaScript"
        ],
        "correct_option": 0,
        "explanation": "libuv is a C library that handles the event loop, threadpool for file and DNS operations, and non-blocking asynchronous socket I/O."
    },
    {
        "id": "q_node_adv_1",
        "skill": "Node.js",
        "category": "Backend",
        "difficulty": "Advanced",
        "question": "When building a high-throughput API in Node.js, what is the best practice for heavy CPU-bound cryptography or image compression?",
        "options": [
            "Offloading to Node.js Worker Threads (`worker_threads`) or native C++ addons",
            "Calling process.nextTick in a recursive synchronous loop",
            "Increasing the V8 heap allocation to 8 GB via --max-old-space-size",
            "Writing synchronous blocking code directly in the Express route handler"
        ],
        "correct_option": 0,
        "explanation": "Node.js worker_threads allocate separate threads with isolated memory, preventing CPU-intensive processing from blocking the main event loop."
    },

    # SQL
    {
        "id": "q_sql_beg_1",
        "skill": "SQL",
        "category": "Databases & Cloud",
        "difficulty": "Beginner",
        "question": "Which SQL statement is used to query and extract records from a database table?",
        "options": [
            "SELECT",
            "FETCH",
            "RETRIEVE",
            "EXTRACT"
        ],
        "correct_option": 0,
        "explanation": "SELECT is the fundamental ANSI SQL query clause used to retrieve rows and columns from database tables."
    },
    {
        "id": "q_sql_int_1",
        "skill": "SQL",
        "category": "Databases & Cloud",
        "difficulty": "Intermediate",
        "question": "What is the functional difference between `WHERE` and `HAVING` clauses in SQL?",
        "options": [
            "`WHERE` filters rows before any group aggregations take place; `HAVING` filters aggregated groups after `GROUP BY`",
            "`HAVING` only works on primary key columns",
            "`WHERE` requires an index, while `HAVING` performs table scans",
            "They are completely interchangeable syntactical aliases"
        ],
        "correct_option": 0,
        "explanation": "WHERE filters source records before grouping; HAVING applies condition filters to grouped aggregate metrics."
    },
    {
        "id": "q_sql_adv_1",
        "skill": "SQL",
        "category": "Databases & Cloud",
        "difficulty": "Advanced",
        "question": "What is the primary difference between a clustered and non-clustered index in relational databases?",
        "options": [
            "A clustered index determines the physical order of table rows on disk; a non-clustered index is a separate index structure with pointers to the data rows",
            "Clustered indexes can only be applied to foreign key columns",
            "Non-clustered indexes permanently duplicate all table columns in memory",
            "Clustered indexes prevent table updates and deletions"
        ],
        "correct_option": 0,
        "explanation": "A clustered index alters how table data is physically organized on disk (one per table), whereas non-clustered indexes create auxiliary B-Trees pointing to row locations."
    },

    # MongoDB
    {
        "id": "q_mongo_beg_1",
        "skill": "MongoDB",
        "category": "Databases & Cloud",
        "difficulty": "Beginner",
        "question": "In MongoDB, what is the document-based equivalent of a relational database 'table'?",
        "options": [
            "Collection",
            "Document",
            "Schema",
            "View"
        ],
        "correct_option": 0,
        "explanation": "In MongoDB, records are JSON-like BSON documents grouped together inside collections."
    },
    {
        "id": "q_mongo_int_1",
        "skill": "MongoDB",
        "category": "Databases & Cloud",
        "difficulty": "Intermediate",
        "question": "Which MongoDB index type is specifically optimized for high-performance equality lookups and range scans on a single field?",
        "options": [
            "Single Field Index (B-Tree)",
            "Text Search Inverted Index",
            "Geospatial 2dsphere Index",
            "TTL Partial Index"
        ],
        "correct_option": 0,
        "explanation": "MongoDB utilizes B-Tree based Single Field indexes for fast O(log N) equality searches and range queries."
    },
    {
        "id": "q_mongo_adv_1",
        "skill": "MongoDB",
        "category": "Databases & Cloud",
        "difficulty": "Advanced",
        "question": "In a MongoDB replica set with write concern `w: 'majority'`, when does the server acknowledge a write to the client?",
        "options": [
            "After the write has been committed to the on-disk journal on a calculated majority of voting replica nodes",
            "Immediately as soon as the primary node receives the TCP packet in memory",
            "Only after all secondary nodes execute a manual compact command",
            "After exactly 30 seconds regardless of node status"
        ],
        "correct_option": 0,
        "explanation": "w: 'majority' guarantees durability by ensuring a write is committed to the journal on a majority of voting replica set members before returning success."
    },

    # Docker
    {
        "id": "q_docker_beg_1",
        "skill": "Docker",
        "category": "Databases & Cloud",
        "difficulty": "Beginner",
        "question": "Which Docker CLI command displays a list of all currently running containers on the host?",
        "options": [
            "docker ps",
            "docker run",
            "docker list",
            "docker images"
        ],
        "correct_option": 0,
        "explanation": "docker ps lists active running containers (and docker ps -a includes stopped containers)."
    },
    {
        "id": "q_docker_int_1",
        "skill": "Docker",
        "category": "Databases & Cloud",
        "difficulty": "Intermediate",
        "question": "In Docker, what is the best practice for keeping production container images lightweight and secure?",
        "options": [
            "Multi-stage builds that separate compile dependencies from runtime artifacts",
            "Installing all build tools inside the runtime container for on-the-fly debugging",
            "Running container processes directly as root for unrestricted file permissions",
            "Committing intermediate stopped containers into new layers"
        ],
        "correct_option": 0,
        "explanation": "Multi-stage Docker builds allow you to compile assets in a heavy build stage and copy only required binaries into a minimal base runtime image."
    },
    {
        "id": "q_docker_adv_1",
        "skill": "Docker",
        "category": "Databases & Cloud",
        "difficulty": "Advanced",
        "question": "What is the primary operational difference between a custom user-defined bridge network and the default bridge network in Docker?",
        "options": [
            "User-defined bridge networks provide automatic internal DNS resolution between containers by container name",
            "User-defined bridge networks disable TCP container-to-container communication",
            "The default bridge network automatically encrypts container traffic with mTLS",
            "User-defined bridge networks can only attach to stopped containers"
        ],
        "correct_option": 0,
        "explanation": "Containers connected to custom user-defined bridge networks can communicate by container name via embedded DNS, whereas the default bridge requires legacy links or explicit IP addresses."
    },

    # Git
    {
        "id": "q_git_beg_1",
        "skill": "Git",
        "category": "Databases & Cloud",
        "difficulty": "Beginner",
        "question": "What is the primary difference between `git merge` and `git rebase`?",
        "options": [
            "`git merge` preserves complete branch history with a merge commit; `git rebase` rewrites commits on top of the base branch for a linear history",
            "`git rebase` creates a permanent remote backup branch automatically",
            "`git merge` permanently deletes uncommitted changes in your staging area",
            "`git rebase` only works on branches that have never been pushed"
        ],
        "correct_option": 0,
        "explanation": "Merge retains existing commit ancestry with an explicit merge commit, whereas rebase replays your commits atop the upstream base branch."
    },
    {
        "id": "q_git_int_1",
        "skill": "Git",
        "category": "Databases & Cloud",
        "difficulty": "Intermediate",
        "question": "Which Git command discards uncommitted changes in a specific file in your working tree?",
        "options": [
            "git restore <file>",
            "git commit --amend",
            "git branch -D",
            "git fetch --all"
        ],
        "correct_option": 0,
        "explanation": "git restore <file> discards unstaged changes in the working tree, reverting the file to the state of the index/HEAD."
    },
    {
        "id": "q_git_adv_1",
        "skill": "Git",
        "category": "Databases & Cloud",
        "difficulty": "Advanced",
        "question": "How does `git cherry-pick <commit-hash>` incorporate changes from another branch?",
        "options": [
            "It extracts the exact diff changes introduced by the specified commit and applies them as a brand new commit on the current HEAD",
            "It permanently moves the commit out of the source branch and removes its history",
            "It performs a recursive merge of all previous parent commits up to the root",
            "It switches the current tracking upstream remote repository"
        ],
        "correct_option": 0,
        "explanation": "git cherry-pick copies the change set of a specific commit and creates a new commit on top of your current branch with a distinct commit hash."
    },

    # REST API & Architecture
    {
        "id": "q_rest_beg_1",
        "skill": "REST API",
        "category": "Technical",
        "difficulty": "Beginner",
        "question": "Which standard HTTP status code signifies that a new resource has been successfully created on the server?",
        "options": [
            "201 Created",
            "200 OK",
            "204 No Content",
            "301 Moved Permanently"
        ],
        "correct_option": 0,
        "explanation": "HTTP 201 Created indicates that the request has succeeded and led to the creation of a new resource."
    },
    {
        "id": "q_rest_int_1",
        "skill": "REST API",
        "category": "Technical",
        "difficulty": "Intermediate",
        "question": "In REST architecture, what does it mean for an HTTP method to be 'idempotent'?",
        "options": [
            "Making multiple identical requests produces the exact same server side-effects as making a single request",
            "The method cannot accept query string parameters",
            "The response must be encrypted with an asymmetric public key",
            "The endpoint must return an empty 204 response body"
        ],
        "correct_option": 0,
        "explanation": "Methods like GET, PUT, and DELETE are idempotent because executing them N times leaves the server in the identical state as executing them once."
    },
    {
        "id": "q_rest_adv_1",
        "skill": "REST API",
        "category": "Technical",
        "difficulty": "Advanced",
        "question": "What is the primary role of the HTTP `ETag` and `If-None-Match` headers in web caching and concurrency?",
        "options": [
            "Validating whether cached client resources have changed on the server, avoiding unnecessary data transfer (304 Not Modified)",
            "Enforcing JWT token signatures on incoming request payloads",
            "Specifying allowed cross-origin resource sharing origins",
            "Enabling chunked HTTP/2 multiplexing streams"
        ],
        "correct_option": 0,
        "explanation": "ETag provides a content hash digest; clients send If-None-Match to receive a lightweight 304 Not Modified if the resource remains unchanged."
    },

    # System Design
    {
        "id": "q_system_int_1",
        "skill": "System Design",
        "category": "Architecture",
        "difficulty": "Intermediate",
        "question": "What is the primary difference between horizontal and vertical database scaling?",
        "options": [
            "Vertical scaling adds more CPU/RAM to a single server; horizontal scaling distributes data across multiple independent nodes (sharding)",
            "Vertical scaling requires NoSQL databases while horizontal scaling only works on MySQL",
            "Horizontal scaling reduces network latency to zero",
            "Vertical scaling partitions tables into microservices"
        ],
        "correct_option": 0,
        "explanation": "Vertical scaling upgrades existing hardware resources on a single machine; horizontal scaling scales out by partitioning workloads across a distributed cluster."
    },
    {
        "id": "q_system_adv_1",
        "skill": "System Design",
        "category": "Architecture",
        "difficulty": "Advanced",
        "question": "When designing an API with heavy read traffic and low write frequency, which strategy provides the lowest latency cache layer?",
        "options": [
            "In-memory Redis Cache with Cache-Aside pattern and TTL invalidation",
            "Writing all queries directly to normalized disk tables",
            "Re-calculating aggregations on every user request in Python",
            "Storing full JSON responses in local filesystem flat files"
        ],
        "correct_option": 0,
        "explanation": "A distributed in-memory cache like Redis using Cache-Aside delivers sub-millisecond read response times and reduces database pressure."
    },

    # Linux & DevOps
    {
        "id": "q_linux_beg_1",
        "skill": "Linux",
        "category": "Databases & Cloud",
        "difficulty": "Beginner",
        "question": "Which standard Linux shell command prints the absolute path of the current working directory?",
        "options": [
            "pwd",
            "cd",
            "ls",
            "whoami"
        ],
        "correct_option": 0,
        "explanation": "pwd (print working directory) displays the full absolute path of the current shell location."
    },
    {
        "id": "q_linux_int_1",
        "skill": "Linux",
        "category": "Databases & Cloud",
        "difficulty": "Intermediate",
        "question": "In Linux filesystems, what is the key difference between a hard link and a symbolic (soft) link?",
        "options": [
            "A hard link shares the exact same inode number as the target file; a symbolic link is a separate file containing a pathname reference",
            "Hard links can cross different mounted storage filesystems",
            "Symbolic links cannot point to directories",
            "Deleting the original file retains symbolic links while breaking hard links"
        ],
        "correct_option": 0,
        "explanation": "Hard links point directly to the underlying filesystem inode (cannot span filesystems); symbolic links store the target pathname and become broken if the target moves."
    },
    {
        "id": "q_k8s_int_1",
        "skill": "Kubernetes",
        "category": "Databases & Cloud",
        "difficulty": "Intermediate",
        "question": "In Kubernetes architecture, what is the fundamental atomic unit of deployment and scheduling?",
        "options": [
            "Pod",
            "Container",
            "Deployment",
            "Node"
        ],
        "correct_option": 0,
        "explanation": "A Pod is the smallest deployable computing unit in Kubernetes, encapsulating one or more co-located containers sharing networking and storage."
    },
    {
        "id": "q_k8s_adv_1",
        "skill": "Kubernetes",
        "category": "Databases & Cloud",
        "difficulty": "Advanced",
        "question": "What is the primary role of the Kubernetes Kube-Scheduler control plane component?",
        "options": [
            "Assigning newly created unscheduled Pods to suitable worker Nodes based on resource requests, taints, and affinity policies",
            "Proxying external HTTP ingress network packets to Pod IPs",
            "Compiling container images from source git repositories",
            "Replicating etcd database journals across worker nodes"
        ],
        "correct_option": 0,
        "explanation": "Kube-Scheduler evaluates node filtering (predicates) and scoring (priorities) to select the optimal worker node for unscheduled pods."
    },

    # Machine Learning
    {
        "id": "q_ml_int_1",
        "skill": "Machine Learning",
        "category": "Technical",
        "difficulty": "Intermediate",
        "question": "What is the primary statistical benefit of k-fold cross-validation over a single train-test split?",
        "options": [
            "Provides a more robust and lower-variance estimate of model generalization performance across the entire dataset",
            "Eliminates the risk of overfitting permanently",
            "Reduces training runtime by a factor of k",
            "Converts continuous regression tasks into classification tasks"
        ],
        "correct_option": 0,
        "explanation": "k-fold cross-validation ensures every observation is used for both training and validation across k iterations, reducing evaluation variance."
    },
    {
        "id": "q_ml_adv_1",
        "skill": "Deep Learning",
        "category": "Technical",
        "difficulty": "Advanced",
        "question": "What causes the vanishing gradient problem in deep neural networks with sigmoid activations?",
        "options": [
            "The derivative of the sigmoid function peaks at 0.25, causing backpropagated error gradients to exponentially decay through repeated chain rule multiplications",
            "Weights become NaN due to float overflow in matrix multiplication",
            "The learning rate dynamically increases to infinity during training",
            "Softmax loss functions cancel out all hidden layer gradients"
        ],
        "correct_option": 0,
        "explanation": "Because sigmoid derivatives are <= 0.25, multiplying many layers in backpropagation causes gradients to diminish toward zero in early layers, preventing weight updates."
    }
]

def generate_assessment_for_role(
    target_role: str,
    user_skills: Optional[List[str]] = None,
    num_questions: int = 5,
    difficulty_preference: str = "balanced"
) -> Dict[str, Any]:
    role_meta = ROLE_TAXONOMY.get(target_role, ROLE_TAXONOMY["Full Stack Developer"])
    core_skills_map = role_meta["core_skills"]
    core_skills_lower = [s.lower() for s in core_skills_map.keys()]
    if user_skills:
        core_skills_lower.extend([s.lower() for s in user_skills])

    # Filter matching questions
    matched_questions = []
    fallback_questions = []

    for q in QUESTION_BANK:
        if q["skill"].lower() in core_skills_lower:
            matched_questions.append(q)
        else:
            fallback_questions.append(q)

    # Order by difficulty if preference is specified
    if difficulty_preference == "beginner":
        matched_questions.sort(key=lambda x: (x["difficulty"] != "Beginner", x["difficulty"] != "Intermediate"))
    elif difficulty_preference == "advanced":
        matched_questions.sort(key=lambda x: (x["difficulty"] != "Advanced", x["difficulty"] != "Intermediate"))

    selected = (matched_questions + fallback_questions)[:max(3, min(num_questions, len(QUESTION_BANK)))]
    assessment_id = f"asm_{uuid.uuid4().hex[:12]}"

    client_questions = []
    for q in selected:
        client_questions.append({
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "skill": q["skill"],
            "difficulty": q["difficulty"]
        })

    return {
        "assessment_id": assessment_id,
        "target_role": target_role,
        "questions": client_questions,
        "total_questions": len(client_questions),
        "_server_questions": selected
    }

def grade_assessment(server_questions: List[Dict[str, Any]], user_answers: Dict[str, int]) -> Dict[str, Any]:
    correct_count = 0
    question_results = []
    category_counts: Dict[str, Dict[str, int]] = {}
    skill_counts: Dict[str, Dict[str, int]] = {}

    for q in server_questions:
        qid = q["id"]
        cat = q.get("category", "General")
        skill = q.get("skill", "General")

        if cat not in category_counts:
            category_counts[cat] = {"total": 0, "correct": 0}
        category_counts[cat]["total"] += 1

        if skill not in skill_counts:
            skill_counts[skill] = {"total": 0, "correct": 0}
        skill_counts[skill]["total"] += 1

        selected_opt = user_answers.get(qid, -1)
        is_correct = (selected_opt == q["correct_option"])
        if is_correct:
            correct_count += 1
            category_counts[cat]["correct"] += 1
            skill_counts[skill]["correct"] += 1

        question_results.append({
            "question_id": qid,
            "question": q["question"],
            "skill": q["skill"],
            "difficulty": q.get("difficulty", "Intermediate"),
            "selected_option": selected_opt,
            "correct_option": q["correct_option"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })

    total = len(server_questions)
    score_pct = round((correct_count / total * 100), 1) if total > 0 else 0.0

    category_scores = {}
    for cat, stats in category_counts.items():
        category_scores[cat] = round((stats["correct"] / stats["total"] * 100), 1) if stats["total"] > 0 else 0.0

    # Explicit Demonstrated Skill Scores (0.0 to 1.0)
    demonstrated_skill_scores = {}
    demonstrated_levels = {}
    for skill, stats in skill_counts.items():
        skill_pct = (stats["correct"] / stats["total"]) if stats["total"] > 0 else 0.0
        demonstrated_skill_scores[skill] = round(skill_pct, 2)
        if skill_pct >= 0.8:
            demonstrated_levels[skill] = "Advanced"
        elif skill_pct >= 0.5:
            demonstrated_levels[skill] = "Intermediate"
        else:
            demonstrated_levels[skill] = "Demonstrated Gap"

    return {
        "total_questions": total,
        "correct_answers": correct_count,
        "score_percentage": score_pct,
        "category_scores": category_scores,
        "demonstrated_skill_scores": demonstrated_skill_scores,
        "demonstrated_levels": demonstrated_levels,
        "question_results": question_results
    }

def select_next_adaptive_question(
    target_role: str,
    answered_questions: List[Dict[str, Any]],
    user_skills: Optional[List[str]] = None,
    session_max_questions: int = 5
) -> Optional[Dict[str, Any]]:
    """
    Transparent, deterministic adaptive question selection policy (ADAPT-v1.0-baseline).

    Rules:
    1. Maximum Questions Bound: Returns None if len(answered_questions) >= session_max_questions.
    2. Dynamic Difficulty Transition:
       - Initial question: starts at 'Intermediate' difficulty.
       - If previous answer was CORRECT:
         Beginner -> Intermediate -> Advanced -> Advanced (step up or maintain high proficiency).
       - If previous answer was INCORRECT:
         Advanced -> Intermediate -> Beginner -> Beginner (step down or re-test foundations).
    3. Core Skill Coverage Priority:
       - Prioritizes untested core skills for target_role in taxonomy order.
       - If all core skills have at least 1 observation, targets the skill with the lowest accuracy.
    4. Deterministic Anti-Repetition & Exhaustion Fallback:
       - Never serves a question already present in answered_questions.
       - If exact (skill, target_difficulty) question is exhausted, falls back to:
         (a) adjacent difficulty for same skill,
         (b) another unassessed role skill matching target difficulty,
         (c) any unused question matching role,
         (d) gracefully terminates early (returns None) if question bank exhausted.
    """
    if len(answered_questions) >= session_max_questions:
        return None

    role_meta = ROLE_TAXONOMY.get(target_role, ROLE_TAXONOMY["Full Stack Developer"])
    core_skills = list(role_meta["core_skills"].keys())
    
    answered_ids = {q.get("question_id") or q.get("id") for q in answered_questions}
    
    # 1. Determine target difficulty
    if not answered_questions:
        target_diff = "Intermediate"
    else:
        last_item = answered_questions[-1]
        last_diff = last_item.get("difficulty", "Intermediate")
        was_correct = last_item.get("is_correct", False)
        
        if was_correct:
            if last_diff == "Beginner":
                target_diff = "Intermediate"
            else:
                target_diff = "Advanced"
        else:
            if last_diff == "Advanced":
                target_diff = "Intermediate"
            else:
                target_diff = "Beginner"

    # 2. Determine target skill
    tested_skills_lower = {q.get("skill", "").lower() for q in answered_questions}
    untested_core = [s for s in core_skills if s.lower() not in tested_skills_lower]
    
    if untested_core:
        target_skill = untested_core[0]
    else:
        # Re-test skill with lowest accuracy
        skill_perf: Dict[str, List[bool]] = {}
        for q in answered_questions:
            sk = q.get("skill", "General")
            if sk not in skill_perf:
                skill_perf[sk] = []
            skill_perf[sk].append(q.get("is_correct", False))
        
        sorted_by_perf = sorted(
            skill_perf.keys(),
            key=lambda sk: (sum(skill_perf[sk]) / len(skill_perf[sk]), len(skill_perf[sk]))
        )
        target_skill = sorted_by_perf[0] if sorted_by_perf else core_skills[0]

    # 3. Candidate pool selection hierarchy
    # Tier A: Exact (skill, difficulty)
    pool = [q for q in QUESTION_BANK if q["id"] not in answered_ids and q["skill"].lower() == target_skill.lower() and q["difficulty"] == target_diff]
    
    # Tier B: Same skill, any available difficulty
    if not pool:
        pool = [q for q in QUESTION_BANK if q["id"] not in answered_ids and q["skill"].lower() == target_skill.lower()]
        
    # Tier C: Other untested role core skill matching target difficulty
    if not pool:
        pool = [q for q in QUESTION_BANK if q["id"] not in answered_ids and q["skill"].lower() in [s.lower() for s in core_skills] and q["difficulty"] == target_diff]
        
    # Tier D: Any other role skill unused
    if not pool:
        pool = [q for q in QUESTION_BANK if q["id"] not in answered_ids and q["skill"].lower() in [s.lower() for s in core_skills]]
        
    # Tier E: Any unused question in whole bank
    if not pool:
        pool = [q for q in QUESTION_BANK if q["id"] not in answered_ids]

    if pool:
        return pool[0]
    return None

# ----------------------------------------------------
# 5. TRANSPARENT BASELINE READINESS ENGINE (SR-v2.0)
# ----------------------------------------------------

def calculate_readiness_score(
    target_role: str,
    extracted_skills: List[Dict[str, Any]],
    assessment_demonstrated_scores: Optional[Dict[str, float]] = None,
    assessment_overall_score: Optional[float] = None,
    is_assessed: bool = False
) -> Dict[str, Any]:
    """
    Transparent, versioned readiness score algorithm (SR-v2.0-baseline).

    Mathematical Specification:
    ReadinessScore = [Sum(w_i * P_eff(s_i)) / Sum(w_i)] * 100

    Rules:
    - Assessed skills: P_eff(s_i) = demonstrated_score (0.0 to 1.0).
    - Unassessed declared skills: P_eff(s_i) = P_declared * 0.50 (provisional discount).
    - Missing skills: P_eff(s_i) = 0.0.
    - Zero fake 75% free pass for unassessed candidates.
    - Unassessed candidate is clearly distinguished from a candidate who took the test and failed.
    """
    role_meta = ROLE_TAXONOMY.get(target_role, ROLE_TAXONOMY["Full Stack Developer"])
    core_skills_map: Dict[str, float] = role_meta["core_skills"]
    optional_skills_map: Dict[str, float] = role_meta["optional_skills"]

    # Map extracted skills by canonical lower-case name
    resume_declared_map: Dict[str, Dict[str, Any]] = {
        s["name"].lower(): s for s in extracted_skills
    }

    # Combined role requirements with weights
    combined_requirements: Dict[str, Tuple[float, str]] = {}
    for sk, wt in core_skills_map.items():
        combined_requirements[sk] = (wt, "Core")
    for sk, wt in optional_skills_map.items():
        combined_requirements[sk] = (wt, "Optional")

    skill_contributions = []
    core_total_weight = sum(core_skills_map.values())
    opt_total_weight = sum(optional_skills_map.values())
    core_accumulated_score = 0.0
    opt_accumulated_score = 0.0

    matched_skills = []
    gap_skills = []
    critical_core_gaps = []
    optional_gaps = []
    core_skills_assessed_count = 0

    demonstrated_scores = assessment_demonstrated_scores or {}

    for skill_name, (weight, tier) in combined_requirements.items():
        sk_lower = skill_name.lower()

        is_skill_assessed = sk_lower in [k.lower() for k in demonstrated_scores.keys()]
        if is_skill_assessed and tier == "Core":
            core_skills_assessed_count += 1

        # Check declared level in resume
        declared_item = resume_declared_map.get(sk_lower)
        declared_level = declared_item["proficiency_level"] if declared_item else None
        
        # Numeric baseline from declared level
        if declared_level == "Advanced":
            declared_val = 0.85
        elif declared_level == "Intermediate":
            declared_val = 0.70
        elif declared_level == "Beginner":
            declared_val = 0.50
        else:
            declared_val = 0.0

        # Effective proficiency calculation
        if is_skill_assessed:
            score = 0.0
            for k, v in demonstrated_scores.items():
                if k.lower() == sk_lower:
                    score = v
                    break
            effective_p = float(score)
            if effective_p >= 0.70:
                status = "verified_competency"
                explanation = f"Assessment-verified competency ({round(effective_p * 100)}% test accuracy)."
            elif effective_p >= 0.40:
                status = "partial_competency"
                explanation = f"Partial assessment competency ({round(effective_p * 100)}% accuracy). Upskilling recommended."
            else:
                status = "demonstrated_gap"
                explanation = f"Assessed but demonstrated knowledge gap ({round(effective_p * 100)}% accuracy)."
        elif declared_item is not None:
            # Declared on resume, but unverified
            # Provisional uncertainty discount of 50%
            discount_factor = 0.50
            effective_p = round(declared_val * discount_factor, 2)
            status = "declared_unassessed"
            explanation = f"Declared on resume ({declared_level}), but unassessed; 50% provisional discount applied until validated."
        else:
            effective_p = 0.0
            status = "missing"
            explanation = "Skill absent from resume and no assessment evidence available."

        # Weight accumulation
        skill_score = weight * effective_p
        if tier == "Core":
            core_accumulated_score += skill_score
        else:
            opt_accumulated_score += skill_score

        gap_amount = round(max(0.0, 1.0 - effective_p), 2)

        # Categorize into matched or gap lists:
        # A skill is a gap if it is missing or demonstrated gap (effective_p < 0.50 when assessed).
        # Skills declared on resume that haven't failed an assessment are considered provisional matches.
        if status in ("missing", "demonstrated_gap"):
            gap_skills.append(skill_name)
            if tier == "Core":
                critical_core_gaps.append(skill_name)
            else:
                optional_gaps.append(skill_name)
        else:
            matched_skills.append(skill_name)

        skill_contributions.append({
            "skill": skill_name,
            "weight": weight,
            "tier": tier,
            "declared_level": declared_level,
            "assessed": is_skill_assessed,
            "demonstrated_score": demonstrated_scores.get(skill_name) if is_skill_assessed else None,
            "effective_proficiency": effective_p,
            "weighted_score": round(skill_score, 3),
            "max_possible": weight,
            "gap": gap_amount,
            "status": status,
            "explanation": explanation
        })

    # Core and Optional score normalized to [0, 100]
    core_pct = (core_accumulated_score / core_total_weight * 100) if core_total_weight > 0 else 0.0
    opt_pct = (opt_accumulated_score / opt_total_weight * 100) if opt_total_weight > 0 else 0.0

    if opt_total_weight > 0:
        # Core skills constitute 90% of job readiness baseline; optional skills provide 10% specialization bonus
        overall_readiness_score = round(0.90 * core_pct + 0.10 * opt_pct, 1)
    else:
        overall_readiness_score = round(core_pct, 1)

    # Bound strictly between 0.0 and 100.0 (no artificial floors)
    overall_readiness_score = max(0.0, min(100.0, overall_readiness_score))

    # Readiness Band
    if overall_readiness_score >= 80.0:
        readiness_level = "Job Ready"
    elif overall_readiness_score >= 65.0:
        readiness_level = "Near Ready"
    elif overall_readiness_score >= 45.0:
        readiness_level = "Intermediate"
    else:
        readiness_level = "Needs Upskilling"

    # Assessment Coverage Metric
    total_core_skills = len(core_skills_map)
    assessment_coverage_pct = round((core_skills_assessed_count / total_core_skills * 100), 1) if total_core_skills > 0 else 0.0

    # Category breakdowns with explainable weighting
    categories_def = role_meta.get("categories", {})
    category_breakdown = []

    for cat_name, cat_skills in categories_def.items():
        cat_skills_lower = [cs.lower() for cs in cat_skills]
        relevant_contributions = [sc for sc in skill_contributions if sc["skill"].lower() in cat_skills_lower]

        if relevant_contributions:
            cat_actual = sum(sc["weighted_score"] for sc in relevant_contributions)
            cat_max = sum(sc["max_possible"] for sc in relevant_contributions)
            cat_score = round((cat_actual / cat_max * 100), 1) if cat_max > 0 else 0.0
        else:
            cat_score = 0.0

        status_tag = "Strong" if cat_score >= 75.0 else ("Moderate" if cat_score >= 50.0 else "Needs Focus")
        category_breakdown.append({
            "category": cat_name,
            "score": cat_score,
            "status": status_tag
        })

    # Actionable and specific recommendations
    recommendations = []
    if critical_core_gaps:
        recommendations.append(f"Close mandatory core gaps: Master {', '.join(critical_core_gaps[:3])}.")
    if not is_assessed or assessment_coverage_pct < 50.0:
        recommendations.append(f"Complete technical assessments to validate unverified skills (current coverage: {assessment_coverage_pct}%).")
    if matched_skills:
        primary_tool = matched_skills[0]
        secondary_tool = matched_skills[1] if len(matched_skills) > 1 else "React"
        recommendations.append(f"Build a portfolio-grade capstone deploying {primary_tool} and {secondary_tool} into production.")
    else:
        recommendations.append(f"Start with foundational {target_role} coursework starting from programming basics.")

    return {
        "formula_version": "SR-v2.0-baseline",
        "overall_readiness_score": overall_readiness_score,
        "readiness_level": readiness_level,
        "is_assessed": is_assessed,
        "assessment_coverage_pct": assessment_coverage_pct,
        "category_breakdown": category_breakdown,
        "matched_skills": matched_skills,
        "gap_skills": gap_skills,
        "critical_core_gaps": critical_core_gaps,
        "optional_gaps": optional_gaps,
        "skill_contributions": skill_contributions,
        "recommendations": recommendations
    }

# ----------------------------------------------------
# 6. PREREQUISITE-AWARE LEARNING PATH GENERATOR
# ----------------------------------------------------

def generate_learning_path_for_gaps(
    target_role: str,
    gap_skills: List[str],
    matched_skills: List[str]
) -> List[Dict[str, Any]]:
    """
    Generates a 4-week structured curriculum using DAG topological sorting.
    Guarantees:
    - Foundational prerequisites always scheduled in earlier weeks before advanced dependents.
    - Zero circular dependency violations.
    - Explicit 'recommendation_reason' for every module.
    """
    # 1. Expand dependencies and sort topologically
    target_gaps = gap_skills if gap_skills else ["System Design", "Docker", "CI/CD", "Testing"]
    ordered_skills = topological_sort_prerequisites(target_gaps, PREREQUISITE_GRAPH)

    # 2. Partition into 4 progressive milestone weeks
    # Foundational prerequisites -> Intermediate integration -> Tooling & CI/CD -> Capstone
    w1_skills = []
    w2_skills = []
    w3_skills = []
    w4_skills = []

    for s in ordered_skills:
        prereqs = PREREQUISITE_GRAPH.get(s, [])
        if not prereqs or s in ["Python", "JavaScript", "HTML5", "CSS3", "SQL", "Git", "Linux"]:
            w1_skills.append(s)
        elif any(p in ["Python", "JavaScript", "SQL"] for p in prereqs) and s in ["FastAPI", "React", "Node.js", "Django", "TypeScript"]:
            w2_skills.append(s)
        elif s in ["Docker", "Kubernetes", "CI/CD", "AWS", "Terraform", "Redis", "MongoDB", "PostgreSQL"]:
            w3_skills.append(s)
        else:
            w4_skills.append(s)

    # Ensure each week has at least one item
    if not w1_skills:
        w1_skills = [ordered_skills[0]] if ordered_skills else ["Programming Fundamentals"]
    if not w2_skills:
        w2_skills = [ordered_skills[min(1, len(ordered_skills)-1)]] if len(ordered_skills) > 1 else ["Framework Architecture"]
    if not w3_skills:
        w3_skills = ["Docker & Automated Testing"]
    if not w4_skills:
        w4_skills = ["System Design & Production Capstone"]

    def make_items(skills_list: List[str], week_num: int) -> List[Dict[str, Any]]:
        items = []
        for sk in skills_list[:2]:
            prereqs = PREREQUISITE_GRAPH.get(sk, [])
            prereq_note = f" (Requires {', '.join(prereqs)})" if prereqs else " (Foundational prerequisite)"
            items.append({
                "id": f"item_w{week_num}_{uuid.uuid4().hex[:6]}",
                "title": f"Mastery of {sk}{prereq_note}",
                "description": f"Targeted study of {sk} syntax, performance patterns, and integration for {target_role}.",
                "resource_url": "https://roadmap.sh/",
                "duration_hours": 6,
                "completed": False,
                "prerequisites": prereqs,
                "recommendation_reason": f"Required for {target_role}; addresses identified skill gap in {sk}."
            })
            items.append({
                "id": f"item_w{week_num}_lab_{uuid.uuid4().hex[:6]}",
                "title": f"Practical Hands-on Project: {sk}",
                "description": f"Implement real-world test cases, API handlers, or interfaces using {sk}.",
                "resource_url": "https://github.com/topics/awesome-guides",
                "duration_hours": 8,
                "completed": False,
                "prerequisites": prereqs,
                "recommendation_reason": f"Hands-on competency verification lab for {sk}."
            })
        return items

    milestones = [
        {
            "week": 1,
            "title": "Week 1: Core Prerequisites & Foundation Gap Elimination",
            "focus_skills": w1_skills,
            "items": make_items(w1_skills, 1)
        },
        {
            "week": 2,
            "title": "Week 2: Framework Integration & API Architecture",
            "focus_skills": w2_skills,
            "items": make_items(w2_skills, 2)
        },
        {
            "week": 3,
            "title": "Week 3: Containerization, Testing & CI/CD Pipelines",
            "focus_skills": w3_skills,
            "items": make_items(w3_skills, 3)
        },
        {
            "week": 4,
            "title": f"Week 4: Advanced Scalability & Production Capstone for {target_role}",
            "focus_skills": w4_skills,
            "items": make_items(w4_skills, 4)
        }
    ]

    return milestones
