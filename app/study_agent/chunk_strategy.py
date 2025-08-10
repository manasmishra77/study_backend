"""
Document Chunking Strategies for Educational Content
"""
import re
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChunkInfo:
    """Information about a chunk"""
    content: str
    chunk_index: int
    total_chunks: int
    chunk_id: str
    heading: Optional[str] = None
    word_count: int = 0
    char_count: int = 0

class DocumentChunker:
    """
    Class for chunking educational documents based on various strategies
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def chunk_by_headings(self, document_content: str) -> List[str]:
        """
        Chunk document content based on markdown headings (# and ##)
        
        Args:
            document_content (str): The full content to be chunked
        
        Returns:
            List[str]: List of content chunks, each starting with a heading
        """
        if not document_content or not document_content.strip():
            return [document_content] if document_content else [""]
        
        # Split content by lines
        lines = document_content.split('\n')
        chunks = []
        current_chunk = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if line is a heading (starts with # or ##)
            if line_stripped.startswith('#') and len(line_stripped) > 1:
                # If we have accumulated content, save it as a chunk
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk).strip()
                    if chunk_content:  # Only add non-empty chunks
                        chunks.append(chunk_content)
                    current_chunk = []
                
                # Start new chunk with the heading
                current_chunk.append(line)
            else:
                # Add line to current chunk
                current_chunk.append(line)
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_content = '\n'.join(current_chunk).strip()
            if chunk_content:
                chunks.append(chunk_content)
        
        # If no chunks were created (no headings found), return the entire content as one chunk
        if not chunks:
            return [document_content.strip()]
        
        # Log chunking information
        self.logger.info(f"Content chunked into {len(chunks)} sections based on headings")
        for i, chunk in enumerate(chunks):
            first_line = chunk.split('\n')[0][:50] + "..." if len(chunk.split('\n')[0]) > 50 else chunk.split('\n')[0]
            self.logger.debug(f"Chunk {i+1}: {first_line}")
        
        return chunks

    def chunk_by_headings_advanced(self, document_content: str, max_chunk_size: int = 1000, overlap_size: int = 100) -> List[str]:
        """
        Advanced chunking method with size limits and overlap
        
        Args:
            document_content (str): The full content to be chunked
            max_chunk_size (int): Maximum characters per chunk
            overlap_size (int): Number of characters to overlap between chunks
        
        Returns:
            List[str]: List of content chunks
        """
        if not document_content or not document_content.strip():
            return [document_content] if document_content else [""]
        
        # First, do heading-based chunking
        heading_chunks = self.chunk_by_headings(document_content)
        
        final_chunks = []
        
        for chunk in heading_chunks:
            if len(chunk) <= max_chunk_size:
                # Chunk is small enough, add as is
                final_chunks.append(chunk)
            else:
                # Chunk is too large, need to split further
                sub_chunks = self._split_large_chunk(chunk, max_chunk_size, overlap_size)
                final_chunks.extend(sub_chunks)
        
        return final_chunks

    def _split_large_chunk(self, chunk: str, max_size: int, overlap_size: int) -> List[str]:
        """
        Split a large chunk into smaller pieces while preserving structure
        
        Args:
            chunk (str): The chunk to split
            max_size (int): Maximum size per sub-chunk
            overlap_size (int): Overlap between sub-chunks
        
        Returns:
            List[str]: List of sub-chunks
        """
        if len(chunk) <= max_size:
            return [chunk]
        
        # Try to split on paragraphs first (double newlines)
        paragraphs = chunk.split('\n\n')
        
        if len(paragraphs) == 1:
            # No paragraph breaks, split on single newlines
            paragraphs = chunk.split('\n')
        
        sub_chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph would exceed max_size
            if len(current_chunk) + len(para) + 2 > max_size:  # +2 for newlines
                if current_chunk:
                    sub_chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap
                    if overlap_size > 0 and len(current_chunk) > overlap_size:
                        overlap_text = current_chunk[-overlap_size:]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    # Single paragraph is too large, force split
                    if len(para) > max_size:
                        # Split by sentences or words as last resort
                        words = para.split(' ')
                        temp_chunk = ""
                        for word in words:
                            if len(temp_chunk) + len(word) + 1 > max_size:
                                if temp_chunk:
                                    sub_chunks.append(temp_chunk.strip())
                                    temp_chunk = word
                                else:
                                    # Single word is too long, just add it
                                    sub_chunks.append(word)
                                    temp_chunk = ""
                            else:
                                temp_chunk += (" " + word) if temp_chunk else word
                        if temp_chunk:
                            current_chunk = temp_chunk
                    else:
                        current_chunk = para
            else:
                # Add paragraph to current chunk
                current_chunk += ("\n\n" + para) if current_chunk else para
        
        # Add final chunk
        if current_chunk:
            sub_chunks.append(current_chunk.strip())
        
        return sub_chunks

    def chunk_by_sentences(self, document_content: str, max_sentences: int = 5) -> List[str]:
        """
        Chunk content by sentences
        
        Args:
            document_content (str): The content to chunk
            max_sentences (int): Maximum sentences per chunk
        
        Returns:
            List[str]: List of sentence-based chunks
        """
        if not document_content or not document_content.strip():
            return [document_content] if document_content else [""]
        
        # Simple sentence splitting (can be improved with better NLP)
        sentences = re.split(r'[.!?]+', document_content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        
        for sentence in sentences:
            current_chunk.append(sentence)
            
            if len(current_chunk) >= max_sentences:
                chunk_content = '. '.join(current_chunk) + '.'
                chunks.append(chunk_content)
                current_chunk = []
        
        # Add remaining sentences
        if current_chunk:
            chunk_content = '. '.join(current_chunk) + '.'
            chunks.append(chunk_content)
        
        return chunks

    def chunk_by_paragraphs(self, document_content: str, max_paragraphs: int = 3) -> List[str]:
        """
        Chunk content by paragraphs
        
        Args:
            document_content (str): The content to chunk
            max_paragraphs (int): Maximum paragraphs per chunk
        
        Returns:
            List[str]: List of paragraph-based chunks
        """
        if not document_content or not document_content.strip():
            return [document_content] if document_content else [""]
        
        paragraphs = [p.strip() for p in document_content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            return [document_content]
        
        chunks = []
        current_chunk = []
        
        for paragraph in paragraphs:
            current_chunk.append(paragraph)
            
            if len(current_chunk) >= max_paragraphs:
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append(chunk_content)
                current_chunk = []
        
        # Add remaining paragraphs
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append(chunk_content)
        
        return chunks

    def get_chunk_info(self, chunks: List[str]) -> List[ChunkInfo]:
        """
        Get detailed information about chunks
        
        Args:
            chunks (List[str]): List of content chunks
        
        Returns:
            List[ChunkInfo]: List of chunk information objects
        """
        chunk_infos = []
        
        for i, chunk in enumerate(chunks):
            # Extract heading if present
            lines = chunk.split('\n')
            heading = None
            for line in lines:
                if line.strip().startswith('#'):
                    heading = line.strip()
                    break
            
            chunk_info = ChunkInfo(
                content=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                chunk_id=f"chunk_{i}",
                heading=heading,
                word_count=len(chunk.split()),
                char_count=len(chunk)
            )
            
            chunk_infos.append(chunk_info)
        
        return chunk_infos

    def test_chunking_with_sample_data(self, json_file_path: str = "training_data/data/eemm102_page1_2.json") -> None:
        """
        Test the chunking methods with sample JSON data
        
        Args:
            json_file_path (str): Path to the JSON file containing sample data
        """
        try:
            # Load sample data
            with open(json_file_path, "r") as f:
                json_data = json.load(f)
            
            # Get page 1 content
            page_1_data = next((page for page in json_data if page["page_number"] == 1), None)
            
            if not page_1_data:
                self.logger.error("Page 1 not found in JSON data")
                return
            
            content = page_1_data["content"]
            self.logger.info("Original content:")
            self.logger.info(content)
            self.logger.info("\n" + "="*50 + "\n")
            
            # Test heading-based chunking
            self.logger.info("=== Testing Heading-Based Chunking ===")
            chunks = self.chunk_by_headings(content)
            self.logger.info(f"Chunked into {len(chunks)} pieces:")
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"\n--- Chunk {i} ---")
                self.logger.info(chunk)
                self.logger.info(f"Length: {len(chunk)} characters")
            
            # Test advanced chunking
            self.logger.info("\n" + "="*50 + "\n")
            self.logger.info("=== Testing Advanced Chunking with Size Limits ===")
            
            advanced_chunks = self.chunk_by_headings_advanced(content, max_chunk_size=300, overlap_size=50)
            self.logger.info(f"Advanced chunking created {len(advanced_chunks)} pieces:")
            
            for i, chunk in enumerate(advanced_chunks, 1):
                self.logger.info(f"\n--- Advanced Chunk {i} ---")
                self.logger.info(chunk)
                self.logger.info(f"Length: {len(chunk)} characters")
            
            # Test paragraph chunking
            self.logger.info("\n" + "="*50 + "\n")
            self.logger.info("=== Testing Paragraph-Based Chunking ===")
            
            para_chunks = self.chunk_by_paragraphs(content, max_paragraphs=2)
            self.logger.info(f"Paragraph chunking created {len(para_chunks)} pieces:")
            
            for i, chunk in enumerate(para_chunks, 1):
                self.logger.info(f"\n--- Paragraph Chunk {i} ---")
                self.logger.info(chunk)
                self.logger.info(f"Length: {len(chunk)} characters")
            
            # Get chunk information
            self.logger.info("\n" + "="*50 + "\n")
            self.logger.info("=== Chunk Information ===")
            
            chunk_infos = self.get_chunk_info(chunks)
            for info in chunk_infos:
                self.logger.info(f"Chunk {info.chunk_index}: {info.heading or 'No heading'}")
                self.logger.info(f"  Words: {info.word_count}, Characters: {info.char_count}")
                
        except Exception as e:
            self.logger.error(f"Error testing chunking: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def chunk_educational_content(self, content: str, strategy: str = "headings", **kwargs) -> List[str]:
        """
        Main method to chunk educational content using specified strategy
        
        Args:
            content (str): Content to chunk
            strategy (str): Chunking strategy ("headings", "advanced", "sentences", "paragraphs")
            **kwargs: Additional parameters for specific strategies
        
        Returns:
            List[str]: Chunked content
        """
        strategies = {
            "headings": self.chunk_by_headings,
            "advanced": lambda x: self.chunk_by_headings_advanced(
                x, 
                kwargs.get("max_chunk_size", 1000), 
                kwargs.get("overlap_size", 100)
            ),
            "sentences": lambda x: self.chunk_by_sentences(
                x, 
                kwargs.get("max_sentences", 5)
            ),
            "paragraphs": lambda x: self.chunk_by_paragraphs(
                x, 
                kwargs.get("max_paragraphs", 3)
            )
        }
        
        if strategy not in strategies:
            self.logger.warning(f"Unknown strategy '{strategy}', using 'headings' as default")
            strategy = "headings"
        
        return strategies[strategy](content)


def main():
    """
    Main function to test the chunking strategies
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create chunker instance
    chunker = DocumentChunker()
    
    # Test with sample data
    chunker.test_chunking_with_sample_data()


if __name__ == "__main__":
    main()