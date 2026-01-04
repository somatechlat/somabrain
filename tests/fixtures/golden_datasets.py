"""Golden test datasets for SomaBrain Full Capacity Testing.

This module provides:
- GoldenMemoryItem: Test item with known relevance score
- GoldenTestSet: Collection of items with queries and expected rankings
- GoldenQuery: Query with expected results and relevance judgments
- GOLDEN_CORPUS_100: 100-item golden test set for quality metrics

All data is clearly marked as TEST DATA for quality verification.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class GoldenMemoryItem:
    """Golden test item with known relevance score.

    Attributes:
        id: Unique identifier for the item
        content: Text content of the memory
        embedding: Pre-computed embedding vector (optional, computed if None)
        relevance_score: Known relevance score [0.0, 1.0]
        memory_type: Type of memory (episodic, semantic, procedural)
        metadata: Additional metadata for the item
    """

    id: str
    content: str
    relevance_score: float
    memory_type: str = "episodic"
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Execute post init  .
            """

        if self.embedding is None:
            # Generate deterministic embedding from content hash
            self.embedding = _generate_deterministic_embedding(self.content)


@dataclass
class GoldenQuery:
    """Query with expected results and relevance judgments.

    Attributes:
        query_text: The query string
        expected_top_k: List of item IDs expected in top-k results
        relevance_judgments: Map of item_id -> relevance score
    """

    query_text: str
    expected_top_k: List[str]
    relevance_judgments: Dict[str, float] = field(default_factory=dict)


@dataclass
class GoldenTestSet:
    """Collection of golden items for quality testing.

    Attributes:
        name: Name of the test set
        items: List of golden memory items
        queries: List of queries with expected results
        expected_rankings: Map of query_text -> ordered list of item IDs
    """

    name: str
    items: List[GoldenMemoryItem]
    queries: List[GoldenQuery]
    expected_rankings: Dict[str, List[str]] = field(default_factory=dict)

    def get_item_by_id(self, item_id: str) -> Optional[GoldenMemoryItem]:
        """Get item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_relevant_items(
        self, query: GoldenQuery, threshold: float = 0.5
    ) -> List[str]:
        """Get item IDs with relevance above threshold for a query."""
        return [
            item_id
            for item_id, score in query.relevance_judgments.items()
            if score >= threshold
        ]


def _generate_deterministic_embedding(text: str, dim: int = 1024) -> np.ndarray:
    """Generate a deterministic embedding from text using hash.

    This creates reproducible embeddings for testing without requiring
    an actual embedding model. The embeddings are normalized to unit length.

    Args:
        text: Input text to embed
        dim: Embedding dimension (default 1024)

    Returns:
        Unit-normalized embedding vector
    """
    # Use SHA-256 hash to seed random generator for reproducibility
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(hash_bytes[:8], byteorder="big")
    rng = np.random.default_rng(seed)

    # Generate random vector and normalize
    vec = rng.standard_normal(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


# ---------------------------------------------------------------------------
# Golden Test Corpus - 100 Items
# ---------------------------------------------------------------------------


def _create_golden_corpus_100() -> GoldenTestSet:
    """Create a 100-item golden test corpus with known relevance scores.

    The corpus covers diverse topics to test retrieval quality:
    - Technology (20 items)
    - Science (20 items)
    - Business (20 items)
    - Health (20 items)
    - General Knowledge (20 items)

    Each category has 4 queries with known relevant items.
    """
    items: List[GoldenMemoryItem] = []
    queries: List[GoldenQuery] = []
    expected_rankings: Dict[str, List[str]] = {}

    # Technology items (g001-g020)
    tech_items = [
        ("g001", "quantum computing breakthrough enables faster cryptography", 1.0),
        ("g002", "machine learning optimization techniques for neural networks", 0.95),
        ("g003", "cloud infrastructure scaling patterns for microservices", 0.9),
        ("g004", "blockchain consensus mechanisms and distributed ledgers", 0.85),
        ("g005", "artificial intelligence ethics and responsible AI development", 0.8),
        ("g006", "cybersecurity best practices for enterprise systems", 0.75),
        ("g007", "edge computing architectures for IoT devices", 0.7),
        ("g008", "natural language processing advances in transformers", 0.65),
        ("g009", "computer vision applications in autonomous vehicles", 0.6),
        ("g010", "database optimization and query performance tuning", 0.55),
        ("g011", "software engineering principles and clean code practices", 0.5),
        ("g012", "DevOps automation and continuous integration pipelines", 0.45),
        ("g013", "mobile application development frameworks comparison", 0.4),
        ("g014", "web security vulnerabilities and prevention strategies", 0.35),
        ("g015", "data engineering pipelines for real-time analytics", 0.3),
        ("g016", "API design patterns and RESTful architecture", 0.25),
        ("g017", "containerization with Docker and Kubernetes orchestration", 0.2),
        ("g018", "serverless computing benefits and limitations", 0.15),
        ("g019", "version control workflows and Git branching strategies", 0.1),
        ("g020", "agile methodology and scrum framework implementation", 0.05),
    ]

    for item_id, content, relevance in tech_items:
        items.append(
            GoldenMemoryItem(
                id=item_id,
                content=content,
                relevance_score=relevance,
                memory_type="semantic",
                metadata={"category": "technology"},
            )
        )

    # Science items (g021-g040)
    science_items = [
        ("g021", "climate change impact on global ecosystems and biodiversity", 1.0),
        ("g022", "genetic engineering advances in CRISPR technology", 0.95),
        ("g023", "space exploration missions to Mars and beyond", 0.9),
        ("g024", "renewable energy sources and sustainable power generation", 0.85),
        ("g025", "neuroscience discoveries about brain plasticity", 0.8),
        ("g026", "particle physics experiments at CERN collider", 0.75),
        ("g027", "oceanography research on deep sea ecosystems", 0.7),
        ("g028", "astronomy observations of exoplanets and habitable zones", 0.65),
        ("g029", "chemistry innovations in materials science", 0.6),
        ("g030", "biology of aging and longevity research", 0.55),
        ("g031", "environmental conservation and wildlife protection", 0.5),
        ("g032", "geology and plate tectonics understanding", 0.45),
        ("g033", "meteorology advances in weather prediction models", 0.4),
        ("g034", "botany research on plant genetics and agriculture", 0.35),
        ("g035", "zoology studies on animal behavior and cognition", 0.3),
        ("g036", "microbiology and antibiotic resistance research", 0.25),
        ("g037", "paleontology discoveries of ancient species", 0.2),
        ("g038", "ecology and ecosystem dynamics modeling", 0.15),
        ("g039", "physics of quantum entanglement phenomena", 0.1),
        ("g040", "mathematics advances in number theory", 0.05),
    ]

    for item_id, content, relevance in science_items:
        items.append(
            GoldenMemoryItem(
                id=item_id,
                content=content,
                relevance_score=relevance,
                memory_type="semantic",
                metadata={"category": "science"},
            )
        )

    # Business items (g041-g060)
    business_items = [
        ("g041", "startup funding strategies and venture capital trends", 1.0),
        ("g042", "market analysis techniques for competitive intelligence", 0.95),
        ("g043", "leadership development and executive coaching methods", 0.9),
        ("g044", "supply chain optimization and logistics management", 0.85),
        ("g045", "financial planning and investment portfolio strategies", 0.8),
        ("g046", "marketing automation and customer engagement platforms", 0.75),
        ("g047", "human resources management and talent acquisition", 0.7),
        ("g048", "business intelligence and data-driven decision making", 0.65),
        ("g049", "project management methodologies and tools", 0.6),
        ("g050", "customer relationship management best practices", 0.55),
        ("g051", "e-commerce platforms and online retail strategies", 0.5),
        ("g052", "corporate governance and compliance frameworks", 0.45),
        ("g053", "mergers and acquisitions due diligence processes", 0.4),
        ("g054", "brand management and reputation building", 0.35),
        ("g055", "sales enablement and revenue optimization", 0.3),
        ("g056", "risk management and business continuity planning", 0.25),
        ("g057", "international trade and global market expansion", 0.2),
        ("g058", "entrepreneurship and small business development", 0.15),
        ("g059", "accounting standards and financial reporting", 0.1),
        ("g060", "organizational change management strategies", 0.05),
    ]

    for item_id, content, relevance in business_items:
        items.append(
            GoldenMemoryItem(
                id=item_id,
                content=content,
                relevance_score=relevance,
                memory_type="semantic",
                metadata={"category": "business"},
            )
        )

    # Health items (g061-g080)
    health_items = [
        ("g061", "mental health awareness and psychological well-being", 1.0),
        ("g062", "nutrition science and dietary guidelines for health", 0.95),
        ("g063", "exercise physiology and fitness training programs", 0.9),
        ("g064", "preventive medicine and health screening protocols", 0.85),
        ("g065", "chronic disease management and treatment options", 0.8),
        ("g066", "pharmaceutical research and drug development pipelines", 0.75),
        ("g067", "telemedicine platforms and remote healthcare delivery", 0.7),
        ("g068", "public health policy and epidemiology studies", 0.65),
        ("g069", "medical imaging advances and diagnostic technologies", 0.6),
        ("g070", "surgical techniques and minimally invasive procedures", 0.55),
        ("g071", "rehabilitation therapy and physical recovery methods", 0.5),
        ("g072", "sleep science and circadian rhythm research", 0.45),
        ("g073", "immunology and vaccine development progress", 0.4),
        ("g074", "cardiology advances in heart disease treatment", 0.35),
        ("g075", "oncology research and cancer treatment innovations", 0.3),
        ("g076", "pediatric care and child development milestones", 0.25),
        ("g077", "geriatric medicine and elderly care approaches", 0.2),
        ("g078", "dental health and oral hygiene best practices", 0.15),
        ("g079", "dermatology and skin health management", 0.1),
        ("g080", "alternative medicine and integrative health approaches", 0.05),
    ]

    for item_id, content, relevance in health_items:
        items.append(
            GoldenMemoryItem(
                id=item_id,
                content=content,
                relevance_score=relevance,
                memory_type="semantic",
                metadata={"category": "health"},
            )
        )

    # General Knowledge items (g081-g100)
    general_items = [
        ("g081", "world history and major historical events timeline", 1.0),
        ("g082", "geography and world cultures exploration", 0.95),
        ("g083", "philosophy and ethical reasoning frameworks", 0.9),
        ("g084", "literature classics and literary analysis methods", 0.85),
        ("g085", "art history and visual arts appreciation", 0.8),
        ("g086", "music theory and composition techniques", 0.75),
        ("g087", "language learning and linguistics research", 0.7),
        ("g088", "psychology and human behavior understanding", 0.65),
        ("g089", "sociology and social dynamics studies", 0.6),
        ("g090", "economics principles and market theory", 0.55),
        ("g091", "political science and governance systems", 0.5),
        ("g092", "anthropology and human evolution studies", 0.45),
        ("g093", "archaeology and ancient civilizations research", 0.4),
        ("g094", "religious studies and comparative theology", 0.35),
        ("g095", "education methods and learning theories", 0.3),
        ("g096", "communication skills and public speaking", 0.25),
        ("g097", "critical thinking and problem solving techniques", 0.2),
        ("g098", "creativity and innovation methodologies", 0.15),
        ("g099", "time management and productivity strategies", 0.1),
        ("g100", "personal development and self-improvement", 0.05),
    ]

    for item_id, content, relevance in general_items:
        items.append(
            GoldenMemoryItem(
                id=item_id,
                content=content,
                relevance_score=relevance,
                memory_type="semantic",
                metadata={"category": "general"},
            )
        )

    # Create queries with expected results
    # Technology queries
    queries.append(
        GoldenQuery(
            query_text="quantum computing and cryptography",
            expected_top_k=["g001", "g039", "g002"],
            relevance_judgments={"g001": 1.0, "g039": 0.6, "g002": 0.4},
        )
    )
    expected_rankings["quantum computing and cryptography"] = ["g001", "g039", "g002"]

    queries.append(
        GoldenQuery(
            query_text="machine learning neural networks",
            expected_top_k=["g002", "g008", "g005"],
            relevance_judgments={"g002": 1.0, "g008": 0.8, "g005": 0.5},
        )
    )
    expected_rankings["machine learning neural networks"] = ["g002", "g008", "g005"]

    # Science queries
    queries.append(
        GoldenQuery(
            query_text="climate change ecosystems",
            expected_top_k=["g021", "g031", "g038"],
            relevance_judgments={"g021": 1.0, "g031": 0.7, "g038": 0.5},
        )
    )
    expected_rankings["climate change ecosystems"] = ["g021", "g031", "g038"]

    queries.append(
        GoldenQuery(
            query_text="genetic engineering CRISPR",
            expected_top_k=["g022", "g030", "g034"],
            relevance_judgments={"g022": 1.0, "g030": 0.5, "g034": 0.4},
        )
    )
    expected_rankings["genetic engineering CRISPR"] = ["g022", "g030", "g034"]

    # Business queries
    queries.append(
        GoldenQuery(
            query_text="startup funding venture capital",
            expected_top_k=["g041", "g058", "g045"],
            relevance_judgments={"g041": 1.0, "g058": 0.6, "g045": 0.5},
        )
    )
    expected_rankings["startup funding venture capital"] = ["g041", "g058", "g045"]

    # Health queries
    queries.append(
        GoldenQuery(
            query_text="mental health psychological well-being",
            expected_top_k=["g061", "g088", "g072"],
            relevance_judgments={"g061": 1.0, "g088": 0.7, "g072": 0.4},
        )
    )
    expected_rankings["mental health psychological well-being"] = [
        "g061",
        "g088",
        "g072",
    ]

    # General queries
    queries.append(
        GoldenQuery(
            query_text="world history historical events",
            expected_top_k=["g081", "g093", "g092"],
            relevance_judgments={"g081": 1.0, "g093": 0.6, "g092": 0.5},
        )
    )
    expected_rankings["world history historical events"] = ["g081", "g093", "g092"]

    return GoldenTestSet(
        name="golden_corpus_100",
        items=items,
        queries=queries,
        expected_rankings=expected_rankings,
    )


# Pre-built golden corpus for import
GOLDEN_CORPUS_100 = _create_golden_corpus_100()


def get_golden_corpus() -> GoldenTestSet:
    """Get the 100-item golden test corpus."""
    return GOLDEN_CORPUS_100


def get_category_items(category: str) -> List[GoldenMemoryItem]:
    """Get items from a specific category."""
    return [
        item
        for item in GOLDEN_CORPUS_100.items
        if item.metadata.get("category") == category
    ]