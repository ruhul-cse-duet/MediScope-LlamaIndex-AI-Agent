"""Enhanced RAG service with better error handling and validation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import ProcessingError

logger = logging.getLogger(__name__)


@dataclass
class RagDocument:
    """RAG document with metadata and optional score."""
    
    doc_id: str
    text: str
    metadata: dict[str, Any]
    score: float | None = None


class SimpleRagStore:
    """Simple JSON-based RAG store with error handling."""
    
    def __init__(self, path: Path) -> None:
        """Initialize the RAG store.
        
        Args:
            path: Path to the JSON storage file
        """
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if not self.path.exists():
                self._write({"documents": [], "version": "1.0"})
                logger.info(f"Created new RAG store at {self.path}")
            else:
                # Validate existing file
                data = self._read()
                if "documents" not in data:
                    logger.warning("Invalid RAG store format, reinitializing")
                    self._write({"documents": [], "version": "1.0"})
                else:
                    logger.info(
                        f"Loaded RAG store with {len(data.get('documents', []))} documents"
                    )
        except Exception as exc:
            logger.error(f"Failed to initialize RAG store: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to initialize RAG store",
                details={"path": str(path), "error": str(exc)},
            )
    
    def _read(self) -> dict[str, Any]:
        """Read data from storage with error handling.
        
        Returns:
            dict: Storage data
            
        Raises:
            ProcessingError: If read fails
        """
        try:
            content = self.path.read_text(encoding="utf-8")
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in RAG store: {str(exc)}")
            raise ProcessingError(
                "RAG store is corrupted",
                details={"path": str(self.path), "error": str(exc)},
            )
        except Exception as exc:
            logger.error(f"Failed to read RAG store: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to read RAG store",
                details={"path": str(self.path), "error": str(exc)},
            )
    
    def _write(self, data: dict[str, Any]) -> None:
        """Write data to storage with error handling.
        
        Args:
            data: Data to write
            
        Raises:
            ProcessingError: If write fails
        """
        try:
            # Write to temp file first, then move (atomic operation)
            temp_path = self.path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp_path.replace(self.path)
        except Exception as exc:
            logger.error(f"Failed to write RAG store: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to write RAG store",
                details={"path": str(self.path), "error": str(exc)},
            )
    
    def add(self, text: str, metadata: dict[str, Any] | None = None) -> RagDocument:
        """Add document to store.
        
        Args:
            text: Document text
            metadata: Optional metadata
            
        Returns:
            RagDocument: Added document
            
        Raises:
            ProcessingError: If add fails
        """
        try:
            payload = self._read()
            doc = {
                "doc_id": uuid4().hex,
                "text": text,
                "metadata": metadata or {},
            }
            payload["documents"].append(doc)
            self._write(payload)
            
            logger.debug(f"Added document to RAG store | ID: {doc['doc_id']}")
            return RagDocument(**doc)
        
        except ProcessingError:
            raise
        except Exception as exc:
            logger.error(f"Failed to add document: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to add document to RAG store",
                details={"error": str(exc)},
            )
    
    def list(self) -> List[RagDocument]:
        """List all documents.
        
        Returns:
            List[RagDocument]: All documents
            
        Raises:
            ProcessingError: If list fails
        """
        try:
            payload = self._read()
            documents = payload.get("documents", [])
            
            # Validate document structure
            valid_docs = []
            for doc in documents:
                if isinstance(doc, dict) and "doc_id" in doc and "text" in doc:
                    valid_docs.append(
                        RagDocument(
                            doc_id=doc.get("doc_id", ""),
                            text=doc.get("text", ""),
                            metadata=doc.get("metadata", {}),
                        )
                    )
                else:
                    logger.warning(f"Skipping invalid document: {doc}")
            
            return valid_docs
        
        except ProcessingError:
            raise
        except Exception as exc:
            logger.error(f"Failed to list documents: {str(exc)}", exc_info=True)
            raise ProcessingError(
                "Failed to list RAG documents",
                details={"error": str(exc)},
            )


class SimpleRagService:
    """Simple RAG service with keyword matching."""
    
    def __init__(self, store: SimpleRagStore) -> None:
        """Initialize service with store.
        
        Args:
            store: RAG store instance
        """
        self.store = store
    
    def ingest(self, text: str, metadata: dict[str, Any] | None = None) -> RagDocument:
        """Ingest document.
        
        Args:
            text: Document text
            metadata: Optional metadata
            
        Returns:
            RagDocument: Ingested document
        """
        return self.store.add(text=text, metadata=metadata)
    
    def query(self, query_text: str, top_k: int = 3) -> List[RagDocument]:
        """Query documents using keyword matching.
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            List[RagDocument]: Matching documents with scores
        """
        try:
            docs = self.store.list()
            if not docs:
                logger.debug("No documents in RAG store")
                return []
            
            # Extract meaningful query terms (length > 2)
            query_terms = {
                term.lower() for term in query_text.split() if len(term) > 2
            }
            
            if not query_terms:
                logger.debug("No meaningful query terms")
                return []
            
            # Score documents
            scored: list[RagDocument] = []
            for doc in docs:
                tokens = {
                    term.lower() for term in doc.text.split() if len(term) > 2
                }
                
                # Calculate overlap score
                overlap = query_terms.intersection(tokens)
                score = len(overlap) / max(len(query_terms), 1)
                
                if score > 0:  # Only include documents with matches
                    scored.append(
                        RagDocument(
                            doc_id=doc.doc_id,
                            text=doc.text,
                            metadata=doc.metadata,
                            score=score,
                        )
                    )
            
            # Sort by score and return top_k
            scored.sort(key=lambda item: item.score or 0, reverse=True)
            result = scored[:top_k]
            
            logger.debug(
                f"RAG query returned {len(result)} documents | "
                f"Query terms: {len(query_terms)} | "
                f"Total docs: {len(docs)}"
            )
            
            return result
        
        except Exception as exc:
            logger.error(f"RAG query failed: {str(exc)}", exc_info=True)
            return []


class RagService:
    """RAG service with multiple backend support."""
    
    def __init__(self) -> None:
        """Initialize RAG service."""
        self._simple = SimpleRagService(
            SimpleRagStore(settings.data_dir / "rag_store.json")
        )
        self._llama_index = None
        
        if settings.rag_provider == "llamaindex":
            try:
                self._llama_index = self._init_llamaindex()
            except Exception as exc:
                logger.warning(
                    f"LlamaIndex initialization failed, falling back to simple RAG: {str(exc)}"
                )
        
        logger.info(f"RAG service initialized with provider: {settings.rag_provider}")
    
    def _init_llamaindex(self):
        """Initialize LlamaIndex with error handling.
        
        Returns:
            VectorStoreIndex or None
        """
        try:
            from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
            
            # Configure LlamaIndex
            Settings.llm = None  # Use external LLM
            Settings.embed_model = "local"
            
            docs_path = settings.data_dir / "documents"
            docs_path.mkdir(parents=True, exist_ok=True)
            
            # Load documents
            documents = SimpleDirectoryReader(input_dir=str(docs_path)).load_data()
            
            if not documents:
                logger.warning("No documents found for LlamaIndex")
                return None
            
            # Create index
            index = VectorStoreIndex.from_documents(documents)
            logger.info(f"LlamaIndex initialized with {len(documents)} documents")
            return index
        
        except ImportError as exc:
            logger.warning(f"LlamaIndex not installed: {str(exc)}")
            return None
        except Exception as exc:
            logger.error(f"LlamaIndex initialization failed: {str(exc)}", exc_info=True)
            return None
    
    def ingest(self, text: str, metadata: dict[str, Any] | None = None) -> RagDocument:
        """Ingest document into RAG system.
        
        Args:
            text: Document text
            metadata: Optional metadata
            
        Returns:
            RagDocument: Ingested document
        """
        return self._simple.ingest(text=text, metadata=metadata)
    
    def query(self, query_text: str, top_k: int = 3) -> List[RagDocument]:
        """Query RAG system.
        
        Args:
            query_text: Query text
            top_k: Number of results
            
        Returns:
            List[RagDocument]: Matching documents
        """
        # Try LlamaIndex first if available
        if self._llama_index:
            try:
                query_engine = self._llama_index.as_query_engine(similarity_top_k=top_k)
                response = query_engine.query(query_text)
                
                if hasattr(response, "source_nodes"):
                    results: list[RagDocument] = []
                    for node in response.source_nodes:
                        metadata = getattr(node, "metadata", {}) or {}
                        text = getattr(node, "text", "")
                        score = getattr(node, "score", None)
                        doc_id = metadata.get("doc_id", uuid4().hex)
                        
                        results.append(
                            RagDocument(
                                doc_id=doc_id,
                                text=text,
                                metadata=metadata,
                                score=score,
                            )
                        )
                    
                    logger.debug(f"LlamaIndex returned {len(results)} documents")
                    return results
            
            except Exception as exc:
                logger.warning(
                    f"LlamaIndex query failed, falling back to simple RAG: {str(exc)}"
                )
        
        # Fallback to simple RAG
        return self._simple.query(query_text=query_text, top_k=top_k)


rag_service = RagService()
