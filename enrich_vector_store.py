"""
Enrich Vector Store with New Knowledge Documents
=================================================
This script indexes new comprehensive Markdown guides into the vector store
to improve RAG retrieval and evaluation scores.

The script:
1. Scans for new .md files in documents_departements folders
2. Extracts and chunks text content
3. Generates embeddings
4. Inserts into PostgreSQL pgvector
5. Preserves existing indexed documents
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag.retriever import index_document, departement_deja_indexe
from src.rag.vector_store import init_vector_table
from sqlalchemy import text
from src.database.connection import engine

# Department mapping (folder name -> database department name)
DEPARTMENT_MAPPING = {
    "rh": "RH",
    "it": "IT & Cybersécurité",
    "marketing": "Marketing & Digital",
    "productivite": "Productivité & Transversal",
    "service_client": "Service Client",
    "support_b2b": "Support B2B",
}

def get_document_count(departement: str) -> int:
    """Get current number of chunks for a department"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM documents_vectorises WHERE departement = :dep"),
            {"dep": departement}
        )
        return result.scalar() or 0


def find_documents_to_index(base_path: str = "data/documents_departements"):
    """Find all documents in departements folders"""
    docs_by_dept = {}
    
    for folder_name, dept_name in DEPARTMENT_MAPPING.items():
        folder_path = os.path.join(base_path, folder_name)
        if not os.path.exists(folder_path):
            continue
            
        docs = []
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(('.pdf', '.txt', '.md')):
                docs.append((filepath, filename))
        
        if docs:
            docs_by_dept[dept_name] = docs
    
    return docs_by_dept


def main(auto_confirm: bool = False):
    print("=" * 80)
    print("VECTOR STORE ENRICHMENT - Knowledge Base Expansion")
    print("=" * 80)
    print()
    
    # Initialize vector table if needed
    print("[SETUP] Initializing vector store...")
    try:
        init_vector_table()
        print("[OK] Vector store ready")
    except Exception as e:
        print(f"[WARNING] Vector store initialization: {e}")
    
    print()
    
    # Show current state
    print("[STATE] CURRENT VECTOR STORE STATE")
    print("-" * 80)
    for folder_name, dept_name in DEPARTMENT_MAPPING.items():
        count = get_document_count(dept_name)
        status = "[OK]" if count > 0 else "[EMPTY]"
        print(f"{status} {dept_name:<30} {count:>5} chunks")
    print()
    
    # Find documents to index
    print("[SCAN] SCANNING FOR DOCUMENTS")
    print("-" * 80)
    docs_by_dept = find_documents_to_index()
    
    total_docs = sum(len(docs) for docs in docs_by_dept.values())
    print(f"Found {total_docs} documents across {len(docs_by_dept)} departments")
    print()
    
    for dept_name, docs in docs_by_dept.items():
        print(f"[DEPT] {dept_name}:")
        for filepath, filename in docs:
            file_size = os.path.getsize(filepath) / 1024  # KB
            print(f"   - {filename:<50} ({file_size:.1f} KB)")
    print()
    
    # Confirm before proceeding
    if not auto_confirm:
        response = input("[CONFIRM] Proceed with indexing? This will ADD to existing data (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    else:
        print("[AUTO] Auto-confirm mode: proceeding with indexing...")
    
    print()
    print("=" * 80)
    print("INDEXING DOCUMENTS")
    print("=" * 80)
    print()
    
    total_indexed = 0
    total_chunks = 0
    errors = []
    
    for dept_name, docs in docs_by_dept.items():
        print(f"\n[DEPT] Processing {dept_name}...")
        print("-" * 80)
        
        chunks_before = get_document_count(dept_name)
        
        for filepath, filename in docs:
            print(f"   Indexing {filename}...", end=" ")
            
            try:
                # Index document (adds chunks to vector store)
                index_document(filepath, dept_name)
                total_indexed += 1
                print("[OK]")
                
            except Exception as e:
                print(f"[ERROR] {str(e)[:100]}")
                errors.append((filename, str(e)))
        
        chunks_after = get_document_count(dept_name)
        new_chunks = chunks_after - chunks_before
        total_chunks += new_chunks
        
        print(f"   [STATS] {dept_name}: {chunks_before} -> {chunks_after} chunks (+{new_chunks})")
    
    print()
    print("=" * 80)
    print("INDEXING COMPLETE")
    print("=" * 80)
    print(f"[OK] Successfully indexed: {total_indexed}/{total_docs} documents")
    print(f"[INFO] Total new chunks added: {total_chunks}")
    
    if errors:
        print(f"[ERROR] Errors: {len(errors)}")
        for filename, error in errors[:5]:
            print(f"   - {filename}: {error[:100]}")
    
    print()
    print("[FINAL] FINAL VECTOR STORE STATE")
    print("-" * 80)
    for folder_name, dept_name in DEPARTMENT_MAPPING.items():
        count = get_document_count(dept_name)
        status = "[OK]" if count > 10 else "[LOW]" if count > 0 else "[EMPTY]"
        print(f"{status} {dept_name:<30} {count:>5} chunks")
    
    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. [OK] Vector store enriched with new knowledge")
    print("2. [NEXT] Adjust RAG retrieval top_k parameter")
    print("3. [NEXT] Re-evaluate executions to measure improvement")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich vector store with knowledge documents")
    parser.add_argument('--auto', action='store_true', help='Auto-confirm without prompting')
    args = parser.parse_args()
    
    main(auto_confirm=args.auto)
