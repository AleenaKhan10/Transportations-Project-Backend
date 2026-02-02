"""
Embedding Service for Maintenance Cases Vector Search.

This service provides functions for:
1. Generating text embeddings using OpenAI
2. Searching similar maintenance cases using vector similarity
3. Storing cases with their embeddings

Uses: OpenAI text-embedding-3-small (1536 dimensions)
"""

from typing import Optional, List
from openai import OpenAI
from sqlmodel import Session, text
from config import settings
from db.database import engine
from helpers import logger
from models.maintenance_case import MaintenanceCase, EMBEDDING_DIMENSIONS


# =============================================================================
# OPENAI CLIENT SETUP
# =============================================================================

# Initialize OpenAI client
_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client (singleton pattern)."""
    global _openai_client
    
    if _openai_client is None:
        if not settings.OPEN_AI_KEY:
            raise ValueError("OPEN_AI_KEY not configured in settings")
        _openai_client = OpenAI(api_key=settings.OPEN_AI_KEY)
    
    return _openai_client


# =============================================================================
# EMBEDDING GENERATION
# =============================================================================


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for given text using OpenAI.
    
    Args:
        text: The text to generate embedding for
        
    Returns:
        List of 1536 floats representing the embedding vector,
        or None if generation fails
        
    Example:
        >>> embedding = generate_embedding("Engine making clicking noise")
        >>> len(embedding)
        1536
    """
    # Validate input
    if not text or len(text.strip()) < 3:
        logger.warning("Text too short for embedding generation")
        return None
    
    try:
        # Clean and truncate text (OpenAI limit is ~8000 tokens)
        clean_text = text.strip()[:8000]
        
        # Call OpenAI API
        client = get_openai_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=clean_text,
            dimensions=EMBEDDING_DIMENSIONS
        )
        
        # Extract embedding from response
        embedding = response.data[0].embedding
        
        logger.info(f"Generated embedding for text ({len(clean_text)} chars)")
        return embedding
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        return None


# =============================================================================
# SIMILAR CASE SEARCH
# =============================================================================


def search_similar_cases(
    issue_description: str,
    limit: int = 5,
    category: Optional[str] = None,
    min_similarity: float = 0.5
) -> List[dict]:
    """
    Search for similar maintenance cases based on issue description.
    
    Args:
        issue_description: The driver's problem description
        limit: Maximum number of results to return (default: 5)
        category: Optional filter by category (mechanical, tire, etc.)
        min_similarity: Minimum similarity threshold (0-1, default: 0.5)
        
    Returns:
        List of similar cases with their solutions and similarity scores
        
    Example:
        >>> cases = search_similar_cases("Engine clicking noise")
        >>> cases[0]
        {
            "id": 1,
            "issue_description": "Engine making clicking sound",
            "solution": "Replaced timing belt tensioner",
            "category": "engine",
            "similarity": 0.89
        }
    """
    # Generate embedding for the search query
    query_embedding = generate_embedding(issue_description)
    
    if query_embedding is None:
        logger.warning("Could not generate embedding for search query")
        return []
    
    try:
        with Session(engine) as session:
            # Debug: Check if any cases exist with embeddings
            count_sql = text("SELECT COUNT(*) FROM dev.maintenance_cases WHERE embedding IS NOT NULL")
            count_result = session.execute(count_sql).scalar()
            logger.info(f"DEBUG: Cases with embeddings in DB: {count_result}")
            
            # Build the SQL query for vector similarity search
            # Using cosine distance: 1 - (embedding <=> query) = similarity
            # NOTE: Using CAST() instead of :: to avoid SQLAlchemy parameter conflict
            sql = text("""
                SELECT 
                    id,
                    issue_description,
                    solution,
                    resolution_steps,
                    category,
                    driver_id,
                    truck_id,
                    trailer_id,
                    1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM dev.maintenance_cases
                WHERE embedding IS NOT NULL
                    AND (:category IS NULL OR category = :category)
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """)
            
            # Format embedding as PostgreSQL array
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            logger.info(f"DEBUG: Embedding string length: {len(embedding_str)}")
            
            result = session.execute(
                sql,
                {
                    "query_embedding": embedding_str,
                    "category": category,
                    "limit": limit
                }
            )
            
            # Format results
            cases = []
            all_rows = list(result)
            logger.info(f"DEBUG: Raw rows returned: {len(all_rows)}")
            
            for row in all_rows:
                similarity = float(row.similarity) if row.similarity else 0
                logger.info(f"DEBUG: Case {row.id} similarity: {similarity}")
                
                # Filter by minimum similarity (lowered to 0.3 for debugging)
                if similarity < min_similarity:
                    logger.info(f"DEBUG: Skipping case {row.id} - similarity {similarity} < {min_similarity}")
                    continue
                    
                cases.append({
                    "id": row.id,
                    "issue_description": row.issue_description,
                    "solution": row.solution,
                    "resolution_steps": row.resolution_steps,
                    "category": row.category,
                    "driver_id": row.driver_id,
                    "truck_id": row.truck_id,
                    "trailer_id": row.trailer_id,
                    "similarity": round(similarity, 3)
                })
            
            logger.info(f"Found {len(cases)} similar cases for query")
            return cases
            
    except Exception as e:
        logger.error(f"Error searching similar cases: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


# =============================================================================
# STORE CASE WITH EMBEDDING
# =============================================================================


def store_case_with_embedding(
    issue_description: str,
    solution: str,
    category: str = "other",
    resolution_steps: Optional[str] = None,
    driver_id: Optional[str] = None,
    truck_id: Optional[str] = None,
    trailer_id: Optional[str] = None,
    source_ticket_id: Optional[int] = None,
) -> Optional[MaintenanceCase]:
    """
    Create a new maintenance case with its embedding.
    
    This automatically generates the embedding from the issue + solution
    text and stores it with the case for future similarity searches.
    
    Args:
        issue_description: The problem description
        solution: How the issue was resolved
        category: Issue category (default: "other")
        resolution_steps: Optional detailed steps
        driver_id: Optional driver ID
        truck_id: Optional truck ID
        trailer_id: Optional trailer ID
        source_ticket_id: Optional link to original ticket
        
    Returns:
        Created MaintenanceCase object, or None if failed
    """
    try:
        # Generate embedding from combined text
        # Combine issue + solution for better semantic matching
        combined_text = f"{issue_description} {solution or ''}"
        embedding = generate_embedding(combined_text)
        
        if embedding is None:
            logger.warning("Could not generate embedding, storing case without it")
        
        # Create case using model method
        with Session(engine) as session:
            case = MaintenanceCase(
                issue_description=issue_description,
                solution=solution,
                resolution_steps=resolution_steps,
                category=category,
                driver_id=driver_id,
                truck_id=truck_id,
                trailer_id=trailer_id,
                source_ticket_id=source_ticket_id,
                embedding=embedding,
                created_by="embedding_service"
            )
            
            session.add(case)
            session.commit()
            session.refresh(case)
            
            logger.info(f"Stored maintenance case #{case.id} with embedding")
            return case
            
    except Exception as e:
        logger.error(f"Failed to store case with embedding: {str(e)}")
        return None


def update_case_embedding(case_id: int) -> bool:
    """
    Update/regenerate embedding for an existing case.
    
    Useful when issue_description or solution is updated.
    
    Args:
        case_id: The case ID to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Session(engine) as session:
            case = session.get(MaintenanceCase, case_id)
            
            if not case:
                logger.warning(f"Case #{case_id} not found")
                return False
            
            # Generate new embedding
            combined_text = f"{case.issue_description} {case.solution or ''}"
            embedding = generate_embedding(combined_text)
            
            if embedding is None:
                logger.warning(f"Could not regenerate embedding for case #{case_id}")
                return False
            
            # Update case
            case.embedding = embedding
            session.add(case)
            session.commit()
            
            logger.info(f"Updated embedding for case #{case_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to update case embedding: {str(e)}")
        return False


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def check_embedding_health() -> dict:
    """
    Check if embedding service is properly configured and working.
    
    Returns:
        Dictionary with health status
    """
    status = {
        "openai_configured": bool(settings.OPEN_AI_KEY),
        "embedding_model": "text-embedding-3-small",
        "dimensions": EMBEDDING_DIMENSIONS,
        "test_embedding": None
    }
    
    # Try generating a test embedding
    try:
        test_embedding = generate_embedding("Health check test")
        status["test_embedding"] = "success" if test_embedding else "failed"
        status["embedding_length"] = len(test_embedding) if test_embedding else 0
    except Exception as e:
        status["test_embedding"] = f"error: {str(e)}"
    
    return status
