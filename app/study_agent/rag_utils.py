"""
RAG (Retrieval-Augmented Generation) utilities for the educational tutor system
"""
import os
import logging
import pdb
import json
import weaviate
from typing import List, Dict, Any, Optional
from weaviate.classes.init import Auth
import weaviate.classes.config as weaviate_config

# Updated imports for Windows compatibility
try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError:
    from langchain.document_loaders import PyPDFLoader

try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from app.study_agent.pdf_reader_utils import PDF_ReaderUtils, PageContent
from app.study_agent.chunk_strategy import DocumentChunker

logger = logging.getLogger(__name__)

class RAGManager:
    """Manages the RAG system for educational content retrieval"""
    
    def __init__(self, api_key: str,
                 weaviate_url: str, weaviate_api_key: str, vectorstore_path: str = "vectorstore"):
        """
        Initialize RAG Manager
        
        Args:
            api_key (str): Google API key
            vectorstore_path (str): Path to store the vector database
        """
        self.api_key = api_key
        self.vectorstore_path = vectorstore_path
        self.vectorstore = None
        self.embeddings = None
        self.retriever = None
        self.client = None
        self.weaviate_url = weaviate_url
        self.weaviate_api_key = weaviate_api_key
        self.chunker = DocumentChunker()
        
        # Initialize embeddings
        self._initialize_embeddings()
        self._initialize_weaviate_client()

    def _initialize_embeddings(self):
        """Initialize Google embeddings"""
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.api_key
            )
            logger.info("Google embeddings initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise

    def _initialize_weaviate_client(self):
        """Initialize Weaviate client"""
        try:
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=Auth.api_key(self.weaviate_api_key)
            )
            logger.info("Weaviate client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise

    def load_pdf_with_board(self, pdf_path: str, subject: str, class_name: str, chapter: str, board: str, topics: List[str]) -> List[Document]:
        """
        Load and process PDF with metadata including board information and build vector store
        
        Args:
            pdf_path (str): Path to PDF file
            subject (str): Subject name (e.g., "Mathematics")
            class_name (str): Class name (e.g., "Class 5")
            chapter (str): Chapter name (e.g., "Chapter 2")
            board (str): Educational board (e.g., "CBSE", "NCERT", "ICSE", "State Board")
        
        Returns:
            List[Document]: List of processed documents with board metadata
        """
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            logger.info(f"Loading PDF: {pdf_path} for {board} board")
            
            # Load PDF
            pdf_reader_utils = PDF_ReaderUtils()
            documents = pdf_reader_utils.get_pdf_processing_info(
                api_key=self.api_key,
                pdf_path=pdf_path,
                subject=subject,
                class_name=class_name,
                chapter=chapter,
                board=board,
                topics=topics,
                filename=os.path.basename(pdf_path)
            )
            # convert json object from `training_data/data/eemm102_page1_2.json` and convert it to List[PageContent]
            # with open("training_data/data/eemm102_page1_2.json", "r") as f:
            #     json_data = json.load(f)
            #     documents = [PageContent(**page) for page in json_data]

            # pdb.set_trace()  # Debugging line to inspect documents
            # print(documents)
            # for doc in documents:
            #     doc.print_json()

            chunked_docs = []

            for doc in documents:

                # Add metadata to each document
                doc.metadata["region"] = self._get_board_region(board)
                doc.metadata["curriculum_type"] = self._get_curriculum_type(board)
                # chunk the document content
                logger.info("Chunking documents for vector store...")
                chunked_document_contents = self.chunk_documents(doc.content)
                logger.info(f"Created {len(chunked_document_contents)} chunks")
                for chunked_document_content in chunked_document_contents:
                    chunked_doc = doc.copy()
                    chunked_doc.content = chunked_document_content
                    chunked_docs.append(chunked_doc)

            self.add_documents_to_weaviate(chunked_docs)
            logger.info(f"Loaded {len(documents)} documents from PDF")

            logger.info(f"Vector store setup completed for {board} {subject}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading PDF with board info: {e}")
            raise
    
    def _get_curriculum_type(self, board: str) -> str:
        """
        Get curriculum type based on board
        
        Args:
            board (str): Educational board name
            
        Returns:
            str: Curriculum type
        """
        board_lower = board.lower()
        
        if "cbse" in board_lower:
            return "National"
        elif "ncert" in board_lower:
            return "National"
        elif "icse" in board_lower:
            return "National"
        elif "state" in board_lower:
            return "State"
        elif "international" in board_lower or "ib" in board_lower:
            return "International"
        else:
            return "Other"
    
    def _get_board_region(self, board: str) -> str:
        """
        Get board region
        
        Args:
            board (str): Educational board name
            
        Returns:
            str: Board region
        """
        board_lower = board.lower()
        
        # State boards
        state_boards = {
            "maharashtra": "Maharashtra",
            "karnataka": "Karnataka", 
            "tamil nadu": "Tamil Nadu",
            "kerala": "Kerala",
            "gujarat": "Gujarat",
            "rajasthan": "Rajasthan",
            "west bengal": "West Bengal",
            "uttar pradesh": "Uttar Pradesh",
            "delhi": "Delhi"
        }
        
        for state, region in state_boards.items():
            if state in board_lower:
                return region
        
        # National boards
        if any(term in board_lower for term in ["cbse", "ncert", "icse"]):
            return "National"
        
        return "Unknown"
    
    def chunk_documents(self, document_content: str) -> List[str]:
        """
        Advanced chunking with size limits while preserving educational structure
        """
        max_size = 1000  # Maximum size for each chunk
        overlap_size = 100  # Overlap size for chunks
        try:
            chunks = self.chunker.chunk_educational_content(
                content=document_content,
                strategy="advanced",
                max_chunk_size=max_size,
                overlap_size=overlap_size
            )
            
            logger.info(f"Advanced chunking created {len(chunks)} sections with size limit {max_size}")
            pdb.set_trace()  # Debugging line to inspect chunks
            print(chunks)
            return chunks
            
        except Exception as e:
            logger.error(f"Error in advanced chunking: {e}")
            # Fallback to RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_size,
                chunk_overlap=100,
                length_function=len
            )
            return text_splitter.split_text(document_content)
        
    def retrieve_context_by_board(self, query: str, board_filter: Optional[str] = None, 
                                 class_filter: Optional[str] = None, subject_filter: Optional[str] = None, 
                                 top_k: int = 3) -> List[Document]:
        """
        Retrieve relevant context with optional board, class, and subject filtering
        
        Args:
            query (str): Search query
            board_filter (str, optional): Filter by specific board (e.g., "CBSE", "NCERT")
            class_filter (str, optional): Filter by specific class (e.g., "Class 5", "Class 6")
            subject_filter (str, optional): Filter by specific subject (e.g., "Mathematics", "Science")
            top_k (int): Number of documents to retrieve
        
        Returns:
            List[Document]: Retrieved documents filtered by board, class, and subject
        """
        try:
            if not self.retriever:
                logger.warning("No retriever available. Please setup RAG system first.")
                return []
            
            # Retrieve documents
            retrieved_docs = self.retriever.get_relevant_documents(query)
            
            # Apply filters if specified
            filtered_docs = []
            for doc in retrieved_docs:
                metadata = doc.metadata
                
                # Check board filter
                if board_filter:
                    doc_board = metadata.get('board', '').lower()
                    if board_filter.lower() not in doc_board:
                        continue
                
                # Check class filter
                if class_filter:
                    doc_class = metadata.get('class', '').lower()
                    if class_filter.lower() not in doc_class:
                        continue
                
                # Check subject filter
                if subject_filter:
                    doc_subject = metadata.get('subject', '').lower()
                    if subject_filter.lower() not in doc_subject:
                        continue
                
                # If all filters pass, add to filtered results
                filtered_docs.append(doc)
            
            # Use filtered docs if any filters were applied, otherwise use original
            final_docs = filtered_docs if (board_filter or class_filter or subject_filter) else retrieved_docs
            
            filters_applied = []
            if board_filter:
                filters_applied.append(f"Board: {board_filter}")
            if class_filter:
                filters_applied.append(f"Class: {class_filter}")
            if subject_filter:
                filters_applied.append(f"Subject: {subject_filter}")
            
            filter_str = f" ({', '.join(filters_applied)})" if filters_applied else ""
            
            logger.info(f"Retrieved {len(final_docs)} documents for query: {query[:50]}...{filter_str}")
            return final_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving context by filters: {e}")
            return []
    
    def get_context_string_with_board(self, query: str, board_filter: Optional[str] = None, 
                                     class_filter: Optional[str] = None, subject_filter: Optional[str] = None, 
                                     top_k: int = 3) -> str:
        """
        Get context as a formatted string with board, class, and subject information
        
        Args:
            query (str): Search query
            board_filter (str, optional): Filter by specific board
            class_filter (str, optional): Filter by specific class
            subject_filter (str, optional): Filter by specific subject
            top_k (int): Number of documents to retrieve
        
        Returns:
            str: Formatted context string with detailed metadata
        """
        try:
            docs = self.retrieve_context_by_board(query, board_filter, class_filter, subject_filter, top_k)
            
            if not docs:
                # Build filter description for no results message
                filters = []
                if board_filter:
                    filters.append(f"{board_filter} board")
                if class_filter:
                    filters.append(f"{class_filter}")
                if subject_filter:
                    filters.append(f"{subject_filter}")
                
                filter_desc = " for " + ", ".join(filters) if filters else ""
                return f"No relevant context found in the knowledge base{filter_desc}."
            
            context_parts = []
            for i, doc in enumerate(docs, 1):
                metadata = doc.metadata
                content = doc.page_content.strip()
                
                context_part = f"""
Context {i}:
Board: {metadata.get('board', 'Unknown')}
Subject: {metadata.get('subject', 'Unknown')}
Class: {metadata.get('class', 'Unknown')}
Chapter: {metadata.get('chapter', 'Unknown')}
Curriculum Type: {metadata.get('curriculum_type', 'Unknown')}
Region: {metadata.get('region', 'Unknown')}
Content: {content}
"""
                context_parts.append(context_part)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting context string with filters: {e}")
            return f"Error retrieving context: {str(e)}"
    
    def get_available_boards(self) -> List[str]:
        """
        Get list of available boards in the current vector store
        
        Returns:
            List[str]: List of board names
        """
        try:
            if not self.vectorstore:
                return []
            
            # This is a simplified approach - in a real implementation,
            # you'd query the vector store metadata
            boards = set()
            
            # For now, return common Indian education boards
            common_boards = [
                "CBSE", "NCERT", "ICSE", "Maharashtra State Board",
                "Karnataka State Board", "Tamil Nadu State Board",
                "Kerala State Board", "Gujarat State Board"
            ]
            
            return common_boards
            
        except Exception as e:
            logger.error(f"Error getting available boards: {e}")
            return []
    
    def create_weaviate_schema(self, schema_name: str = "EducationalDocument"):
        """Create Weaviate schema/collection for educational documents"""
        try:
            # Check if collection already exists
            if self.client.collections.exists(schema_name):
                logger.info(f"{schema_name} collection already exists")
                return self.client.collections.get(schema_name)

            # Create collection with properties
            collection = self.client.collections.create(
                name=schema_name,
                properties=[
                    weaviate_config.Property(
                        name="content",
                        data_type=weaviate_config.DataType.TEXT,
                        description="The main content of the document"
                    ),
                    weaviate_config.Property(
                        name="subject",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Subject of the document"
                    ),
                    weaviate_config.Property(
                        name="class_name",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Class/grade level"
                    ),
                    weaviate_config.Property(
                        name="chapter",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Chapter name"
                    ),
                    weaviate_config.Property(
                        name="board",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Educational board"
                    ),
                    weaviate_config.Property(
                        name="region",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Geographic region"
                    ),
                    weaviate_config.Property(
                        name="curriculum_type",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Type of curriculum"
                    ),
                    weaviate_config.Property(
                        name="topics",
                        data_type=weaviate_config.DataType.TEXT,
                        description="Topics covered in the document"
                    )
                ],
                # No vectorizer - we'll provide embeddings manually
                vectorizer_config=weaviate_config.Configure.Vectorizer.none(),
                vector_index_config=weaviate_config.Configure.VectorIndex.hnsw(
                    distance_metric=weaviate_config.VectorDistances.COSINE
                )
            )
            
            logger.info("EducationalDocument collection created successfully")
            return collection
            
        except Exception as e:
            logger.error(f"Error creating Weaviate schema: {e}")
            raise

    def add_documents_to_weaviate(self, documents: List[Any], collection_name: str = "EducationalDocument"):
        """
        Add documents with metadata to Weaviate
        
        Args:
            documents: List of PageContent objects or similar
            collection_name: Name of the Weaviate collection
        """
        try:
            logger.info("Creating Weaviate collection...")
            # Create or get collection
            collection = self.create_weaviate_schema(collection_name)

            # Prepare data for batch insertion
            data_objects = []
            pdb.set_trace()
            for i, doc in enumerate(documents):  # Fixed: Added enumerate
                # Convert PageContent to dictionary format
                if hasattr(doc, 'content') and hasattr(doc, 'metadata'):
                    # Handle PageContent objects
                    content = doc.content
                    metadata = doc.metadata
                elif isinstance(doc, dict):
                    # Handle dictionary objects
                    content = doc.get('content', '')
                    metadata = doc.get('metadata', {})
                else:
                    logger.warning(f"Unsupported document type: {type(doc)}")
                    continue

                # Generate embeddings using your GoogleGenerativeAIEmbeddings instance
                try:
                    logger.info(f"Generating embedding for document {i+1}/{len(documents)}")
                    content_vector = self.embeddings.embed_query(content)
                    logger.debug(f"Generated {len(content_vector)}-dimensional embedding for content of length {len(content)}")
                except Exception as e:
                    logger.error(f"Failed to generate embedding for document {i+1}: {e}")
                    continue 
                
                # Prepare properties for Weaviate
                properties = {
                    "content": content,
                    "subject": metadata.get("subject", ""),
                    "class_name": metadata.get("class", ""),
                    "chapter": metadata.get("chapter", ""),
                    "board": metadata.get("board", ""),
                    "region": metadata.get("region", ""),
                    "curriculum_type": metadata.get("curriculum_type", ""),
                    "topics": str(metadata.get("topics", []))
                }
                
                # Add object with vector
                data_objects.append({
                    "properties": properties,
                    "vector": content_vector
                })
            
            logger.info(f"Inserting {len(data_objects)} documents into Weaviate...")
            pdb.set_trace()
            # Batch insert documents
            with collection.batch.dynamic() as batch:
                for i, obj in enumerate(data_objects):
                    # Fixed: Pass both properties AND vector to Weaviate
                    batch.add_object(
                        properties=obj["properties"],
                        vector=obj["vector"]
                    )
                    pdb.set_trace()
                    if (i + 1) % 10 == 0:  # Log progress every 10 items
                        logger.info(f"Processed {i + 1}/{len(data_objects)} documents")
            
            logger.info(f"Successfully added {len(data_objects)} documents to Weaviate")
            
        except Exception as e:
            logger.error(f"Error adding documents to Weaviate: {e}")
            raise

    def retrieve_hybrid_search(self, query: str, alpha: float = 0.8, top_k: int = 5, where_filter: Optional[Dict] = None) -> List[Dict]:
        """
        Perform hybrid search combining vector similarity and keyword search
        
        Args:
            query (str): Search query
            alpha (float): Weight for vector search vs keyword search (0.0 = pure keyword, 1.0 = pure vector)
            top_k (int): Number of results to return
            where_filter (Dict, optional): Metadata filters
        
        Returns:
            List[Dict]: Search results with content, metadata, and scores
        """
        try:
            if not self.client:
                logger.error("Weaviate client not initialized")
                return []
            
            collection = self.client.collections.get("EducationalDocument")
            
            # Generate query embedding for vector search
            query_vector = self.embeddings.embed_query(query)
            
            # Build hybrid search query
            search_query = collection.query.hybrid(
                query=query,
                vector=query_vector,
                alpha=alpha,
                limit=top_k,
                where=where_filter
            )
            
            # Execute search
            results = search_query.objects
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_result = {
                    "content": result.properties.get("content", ""),
                    "metadata": {
                        "subject": result.properties.get("subject", ""),
                        "class_name": result.properties.get("class_name", ""),
                        "chapter": result.properties.get("chapter", ""),
                        "board": result.properties.get("board", ""),
                        "region": result.properties.get("region", ""),
                        "curriculum_type": result.properties.get("curriculum_type", ""),
                        "topics": result.properties.get("topics", "")
                    },
                    "score": getattr(result.metadata, 'score', 0.0),
                    "explain_score": getattr(result.metadata, 'explain_score', None)
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Hybrid search returned {len(formatted_results)} results for query: '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []