"""
Enhanced PDF Vision Processing Script with Metadata Support
Uses PyMuPDF instead of pdf2image to avoid Poppler dependency
"""
import google.generativeai as genai
import os
import fitz  # PyMuPDF
from PIL import Image
import io
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set API key
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class PageContent:
    """Data class to hold page content and metadata"""
    page_number: int
    content: str
    metadata: Dict[str, Any]
    image_info: Dict[str, Any]


class PDF_ReaderUtils:
    """Utility class for PDF reading and processing with metadata support
    """
    def __init__(self):
        pass


    def setup_gemini(self, api_key: str) -> genai.GenerativeModel:
        """Setup Gemini API and return vision model"""
        try:
            google_api_key = api_key
            
            genai.configure(api_key=google_api_key)
            
            # Use the correct model name for vision tasks
            vision_model = genai.GenerativeModel("gemini-1.5-pro")
            logger.info("✅ Gemini 1.5 Pro model initialized successfully")
            return vision_model
        
        except Exception as e:
            logger.error(f"❌ Failed to setup Gemini: {e}")
            raise

    def create_pdf_metadata(self, pdf_path: str, subject: str = None, class_name: str = None, 
                        chapter: str = None, board: str = None, topics: List[str] = None,
                        filename: str = None) -> Dict[str, Any]:
        """
        Create base metadata for the PDF document
        
        Args:
            pdf_path: Path to PDF file
            subject: Subject name (e.g., "Mathematics")
            class_name: Class name (e.g., "Class 5")
            chapter: Chapter name (e.g., "Chapter 3: Fractions")
            board: Educational board (e.g., "NCERT", "CBSE")
            topics: List of topics covered
        
        Returns:
            Dictionary containing PDF metadata
        """
        
        metadata = {
            "filename": filename,
            "filepath": pdf_path,
            "subject": subject or "Unknown",
            "class": class_name or "Unknown", 
            "chapter": chapter or f"Chapter from {filename}",
            "board": board or "Unknown",
            "topics": topics or [],
            "document_type": "textbook",
            "language": "english",
            "processed_at": datetime.now().isoformat(),
            "file_size": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
        }
        
        return metadata

    def create_page_metadata(self, base_metadata: Dict[str, Any], page_num: int, 
                            image_size: tuple, content_length: int,
                            additional_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create metadata for a specific page
        
        Args:
            base_metadata: Base PDF metadata
            page_num: Page number (1-indexed)
            image_size: Tuple of (width, height) of the image
            content_length: Length of extracted content
            additional_metadata: Any additional page-specific metadata
        
        Returns:
            Dictionary containing page metadata
        """
        page_metadata = base_metadata.copy()
        
        # Add page-specific information
        page_metadata.update({
            "page_number": page_num,
            "page_id": f"{base_metadata['filename']}_page_{page_num}",
            "image_width": image_size[0],
            "image_height": image_size[1],
            "content_length": content_length,
            "extraction_method": "gemini_vision",
            "chunk_type": "page",
            # Add weaviate-specific fields
            "weaviate_class": "EducationalDocument",
            "searchable_content": True
        })
        
        # Add any additional metadata
        if additional_metadata:
            page_metadata.update(additional_metadata)
        
        return page_metadata

    def pdf_to_images_with_metadata(self, pdf_path: str, base_metadata: Dict[str, Any], 
                                zoom_factor: float = 2.0) -> List[Dict[str, Any]]:
        """
        Convert PDF pages to PIL Images with metadata
        
        Args:
            pdf_path: Path to PDF file
            base_metadata: Base metadata for the PDF
            zoom_factor: Zoom factor for image quality
        
        Returns:
            List of dictionaries containing image and metadata
        """
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            logger.info(f"📄 Loading PDF: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            logger.info(f"📊 PDF has {len(pdf_document)} pages")
            
            pages_data = []
            for page_num in range(len(pdf_document)):
                logger.info(f"🖼️ Converting page {page_num + 1}/{len(pdf_document)} to image...")
                
                page = pdf_document[page_num]
                # Create transformation matrix for zoom
                mat = fitz.Matrix(zoom_factor, zoom_factor)
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat)
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Create image info
                image_info = {
                    "format": "PNG",
                    "mode": img.mode,
                    "size": img.size,
                    "zoom_factor": zoom_factor
                }
                
                # Create initial page metadata (content_length will be added later)
                page_metadata = self.create_page_metadata(
                    base_metadata, 
                    page_num + 1, 
                    img.size, 
                    0,  # Will be updated after content extraction
                    {"image_info": image_info}
                )
                
                pages_data.append({
                    "image": img,
                    "metadata": page_metadata,
                    "image_info": image_info
                })
                
                logger.info(f"✅ Page {page_num + 1} converted (size: {img.size})")
            
            pdf_document.close()
            logger.info(f"✅ Successfully converted {len(pages_data)} pages to images with metadata")
            return pages_data
        
        except Exception as e:
            logger.error(f"❌ Failed to convert PDF to images: {e}")
            raise

    def process_image_with_gemini(self, vision_model: genai.GenerativeModel, 
                                page_data: Dict[str, Any],
                                prompt: str = None) -> PageContent:
        """
        Process a single image with Gemini Pro Vision and return PageContent with metadata
        
        Args:
            vision_model: Gemini vision model
            page_data: Dictionary containing image, metadata, and image_info
            prompt: Custom prompt (optional)
        
        Returns:
            PageContent object with content and metadata
        """
        try:
            image = page_data["image"]
            metadata = page_data["metadata"]
            page_num = metadata["page_number"]
            
            if prompt is None:
                prompt = f"""Extract all educational content from this page {page_num} of a {metadata['subject']} textbook in structured Markdown format. Include:
                - All headings and subheadings
                - All text content  
                - Mathematical formulas and expressions
                - Figure descriptions
                - Exercise questions and problems
                - Any diagrams or illustrations descriptions
                
                Subject: {metadata['subject']}
                Class: {metadata['class']}
                Chapter: {metadata['chapter']}
                
                Format the output as clean, readable Markdown."""
            
            logger.info(f"🧠 Processing page {page_num} with Gemini Pro Vision...")
            
            # Convert PIL Image to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            response = vision_model.generate_content([prompt, image])
            
            content = ""
            if response.text:
                content = response.text
                logger.info(f"✅ Page {page_num} processed successfully ({len(content)} characters)")
            else:
                content = f"# Page {page_num}\n\n*No content extracted*"
                logger.warning(f"⚠️ Page {page_num} returned empty response")
            
            # Update metadata with content length
            metadata["content_length"] = len(content)
            metadata["extraction_status"] = "success" if response.text else "empty_response"
            
            # Add content analysis metadata
            content_lower = content.lower()
            metadata.update({
                "has_formulas": any(char in content for char in ["=", "+", "-", "×", "÷", "∑", "∫"]),
                "has_exercises": any(word in content_lower for word in ["exercise", "question", "problem", "solve"]),
                "has_diagrams": any(word in content_lower for word in ["figure", "diagram", "image", "chart", "graph"]),
                "estimated_reading_time": len(content.split()) // 200,  # rough estimate in minutes
                "word_count": len(content.split())
            })
            
            return PageContent(
                page_number=page_num,
                content=content,
                metadata=metadata,
                image_info=page_data["image_info"]
            )
        
        except Exception as e:
            logger.error(f"❌ Failed to process page {metadata.get('page_number', 'unknown')}: {e}")
            
            # Create error metadata
            error_metadata = metadata.copy()
            error_metadata.update({
                "content_length": 0,
                "extraction_status": "error",
                "error_message": str(e)
            })
            
            return PageContent(
                page_number=metadata.get('page_number', 0),
                content=f"# Page {metadata.get('page_number', 'unknown')}\n\n*Error processing page: {str(e)}*",
                metadata=error_metadata,
                image_info=page_data.get("image_info", {})
            )

    def process_pdf_with_vision_and_metadata(self, api_key: str,
                                              pdf_path: str,
                                        subject: str = None,
                                        class_name: str = None,
                                        chapter: str = None,
                                        board: str = None,
                                        topics: List[str] = None,
                                        output_file: str = None,
                                        metadata_file: str = None,
                                        filename: str = None) -> List[PageContent]:
        """
        Complete PDF processing pipeline with metadata
        
        Args:
            pdf_path: Path to PDF file
            subject: Subject name
            class_name: Class name
            chapter: Chapter name
            board: Educational board
            topics: List of topics
            output_file: Optional output file path for content
            metadata_file: Optional output file path for metadata
        
        Returns:
            List of PageContent objects with content and metadata
        """
        try:
            logger.info("🚀 Starting PDF vision processing with metadata...")
            
            # Create base metadata
            base_metadata = self.create_pdf_metadata(pdf_path, subject, class_name, chapter, board, topics, filename=filename)
            logger.info(f"📋 Base metadata created: {json.dumps(base_metadata, indent=2)}")
            
            # Setup Gemini
            vision_model = self.setup_gemini(api_key=api_key)
            
            # Convert PDF to images with metadata
            pages_data = self.pdf_to_images_with_metadata(pdf_path, base_metadata)
            
            # Process each page
            all_page_contents = []
            total_pages = len(pages_data)
            
            for i, page_data in enumerate(pages_data):
                logger.info(f"📄 Processing page {i + 1}/{total_pages}...")
                
                page_content = self.process_image_with_gemini(vision_model, page_data)
                all_page_contents.append(page_content)
                
                # Progress update
                progress = ((i + 1) / total_pages) * 100
                logger.info(f"📊 Progress: {progress:.1f}% ({i + 1}/{total_pages} pages)")
            
            # Save combined content to file if specified
            if output_file:
                try:
                    combined_content = "\n\n---\n\n".join([
                        f"# Page {pc.page_number}\n\n{pc.content}" 
                        for pc in all_page_contents
                    ])
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(combined_content)
                    logger.info(f"💾 Content saved to: {output_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to save content: {e}")
            
            # Save metadata to file if specified
            if metadata_file:
                try:
                    metadata_list = [
                        {
                            "page_number": pc.page_number,
                            "metadata": pc.metadata,
                            "image_info": pc.image_info,
                            "content_preview": pc.content[:200] + "..." if len(pc.content) > 200 else pc.content
                        }
                        for pc in all_page_contents
                    ]
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata_list, f, indent=2, ensure_ascii=False)
                    logger.info(f"💾 Metadata saved to: {metadata_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to save metadata: {e}")
            
            logger.info("🎉 PDF processing with metadata completed successfully!")
            return all_page_contents
        
        except Exception as e:
            logger.error(f"❌ PDF processing failed: {e}")
            raise

    def prepare_for_weaviate(self, page_contents: List[PageContent]) -> List[Dict[str, Any]]:
        """
        Prepare processed pages for Weaviate storage
        
        Args:
            page_contents: List of PageContent objects
        
        Returns:
            List of dictionaries ready for Weaviate import
        """
        weaviate_objects = []
        
        for pc in page_contents:
            # Create Weaviate object
            weaviate_obj = {
                "content": pc.content,
                "properties": {
                    # Flatten metadata for Weaviate
                    **{k: v for k, v in pc.metadata.items() if isinstance(v, (str, int, float, bool))},
                    # Convert lists to comma-separated strings
                    "topics": ", ".join(pc.metadata.get("topics", [])) if isinstance(pc.metadata.get("topics"), list) else str(pc.metadata.get("topics", "")),
                }
            }
            
            weaviate_objects.append(weaviate_obj)
        
        return weaviate_objects

    def get_pdf_processing_info(self, api_key: str, pdf_path: str, subject: str, class_name: str, chapter: str, board: str, topics: List[str], filename: str):
        """Main function"""
        try:
            # Configuration with metadata
            output_file = "eemm102_extracted_content.md"
            metadata_file = "eemm102_metadata.json"
            
            # PDF metadata
            pdf_metadata = {
                "subject": subject,
                "class_name": class_name,
                "chapter": chapter,
                "board": board,
                "topics": topics,
                "filename": filename
            }
            
            # Process PDF with metadata
            page_contents = self.process_pdf_with_vision_and_metadata(
                api_key=api_key,
                pdf_path=pdf_path,
                output_file=output_file,
                metadata_file=metadata_file,
                **pdf_metadata
            )

            return page_contents
            
            # # Prepare for Weaviate
            # weaviate_objects = self.prepare_for_weaviate(page_contents)

            # # Save Weaviate-ready data
            # weaviate_file = "eemm102_weaviate_ready.json"
            # with open(weaviate_file, 'w', encoding='utf-8') as f:
            #     json.dump(weaviate_objects, f, indent=2, ensure_ascii=False)
            # logger.info(f"💾 Weaviate-ready data saved to: {weaviate_file}")
            
            # # Show statistics
            # logger.info("\n📊 Processing Statistics:")
            # logger.info(f"   Total pages processed: {len(page_contents)}")
            # logger.info(f"   Total content length: {sum(len(pc.content) for pc in page_contents)} characters")
            # logger.info(f"   Average content per page: {sum(len(pc.content) for pc in page_contents) // len(page_contents)} characters")
            
            # # Show metadata sample
            # if page_contents:
            #     sample_metadata = page_contents[0].metadata
            #     logger.info(f"\n📋 Sample page metadata:")
            #     for key, value in list(sample_metadata.items())[:10]:  # Show first 10 fields
            #         logger.info(f"   {key}: {value}")
            
        except Exception as e:
            logger.error(f"❌ Main execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
