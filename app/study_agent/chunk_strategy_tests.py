"""
Unit tests for Document Chunking Strategies
"""
import unittest
import logging
import pdb
from typing import List
from chunk_strategy import DocumentChunker

class TestDocumentChunking(unittest.TestCase):
    """Test cases for document chunking strategies"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.chunker = DocumentChunker()
        logging.basicConfig(level=logging.INFO)
    
    def test_specific_fractions_content(self):
        """Test the chunking with the specific fractions content"""
        content = """# Chapter 2: Fractions

Tamanna is a student of Grade 5. She has two chocolates of different sizes. She says that 1/3 of one of her chocolates is bigger than 1/2 of the other chocolate. Is that correct? Explain why this is so.

[Illustration: Two chocolate bars. The first is divided into two equal parts, with one part labeled "Identify 1/2 of the chocolate". The second is divided into three equal parts, with one part labeled "Identify 1/3 of the chocolate".]

When can we say that 1/2 of something is greater than 1/3 of something?

To compare two fractions of two wholes, the wholes from which the fractions are derived must be the same.

## Playing with a Grid

[Illustration: Three grids labeled A, B, and C. Each grid is a 6x8 rectangle divided into equal squares.]

* Shade 1/8 of Grid A in red.
* Shade 1/6 of Grid B in blue.
* Shade 1/12 of Grid C in yellow.
* Do you see 1/3 in any of the grids? Mark it."""
        
        print("\n=== Testing Specific Fractions Content ===")
        chunks = self.chunker.chunk_by_headings(content)
        
        # Should create 2 chunks
        self.assertEqual(len(chunks), 2, f"Expected 2 chunks, got {len(chunks)}")
        
        # First chunk should start with "# Chapter 2: Fractions"
        self.assertTrue(chunks[0].startswith("# Chapter 2: Fractions"), 
                       f"First chunk should start with main heading")
        
        # Second chunk should start with "## Playing with a Grid"
        self.assertTrue(chunks[1].startswith("## Playing with a Grid"), 
                       f"Second chunk should start with subheading")
        
        # Print results for visual inspection
        for i, chunk in enumerate(chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(f"Length: {len(chunk)} characters")
            print(f"First line: {chunk.split(chr(10))[0]}")
            print(f"Content preview: {chunk[:100]}...")
        
        return chunks
    
    def test_empty_content(self):
        """Test chunking with empty content"""
        chunks = self.chunker.chunk_by_headings("")
        self.assertEqual(chunks, [""], "Empty content should return list with empty string")
        
        chunks = self.chunker.chunk_by_headings("   ")
        self.assertEqual(chunks, ["   "], "Whitespace-only content should return as-is")
    
    def test_no_headings(self):
        """Test content without any headings"""
        content = "This is just plain text without any headings.\nIt should return as a single chunk."
        chunks = self.chunker.chunk_by_headings(content)
        
        self.assertEqual(len(chunks), 1, "Content without headings should return single chunk")
        self.assertEqual(chunks[0].strip(), content.strip())
    
    def test_only_h1_headings(self):
        """Test content with only H1 headings"""
        content = """# First Heading
Content under first heading.

# Second Heading
Content under second heading.

# Third Heading
Content under third heading."""
        
        chunks = self.chunker.chunk_by_headings(content)
        self.assertEqual(len(chunks), 3, "Should create 3 chunks for 3 H1 headings")
        
        for i, chunk in enumerate(chunks):
            self.assertTrue(chunk.startswith(f"# {['First', 'Second', 'Third'][i]} Heading"), 
                           f"Chunk {i+1} should start with correct heading")
    
    def test_only_h2_headings(self):
        """Test content with only H2 headings"""
        content = """## First Section
Content under first section.

## Second Section
Content under second section."""
        
        chunks = self.chunker.chunk_by_headings(content)
        self.assertEqual(len(chunks), 2, "Should create 2 chunks for 2 H2 headings")
    
    def test_mixed_headings(self):
        """Test content with mixed H1 and H2 headings"""
        content = """# Main Chapter
Introduction to the chapter.

## First Section
Content of first section.

## Second Section
Content of second section.

# Another Chapter
New chapter content.

## Sub Section
Sub section content."""
        
        chunks = self.chunker.chunk_by_headings(content)
        self.assertEqual(len(chunks), 5, "Should create 5 chunks for mixed headings")
        
        # Check that chunks start with correct headings
        expected_starts = ["# Main Chapter", "## First Section", "## Second Section", 
                          "# Another Chapter", "## Sub Section"]
        
        for i, (chunk, expected) in enumerate(zip(chunks, expected_starts)):
            self.assertTrue(chunk.startswith(expected), 
                           f"Chunk {i+1} should start with '{expected}'")
    
    def test_headings_with_content_before(self):
        """Test content that has text before the first heading"""
        content = """This is some introductory text before any headings.
It should be included in the first chunk.

# First Heading
Content under first heading.

## Sub Heading
Content under sub heading."""
        
        chunks = self.chunker.chunk_by_headings(content)
        self.assertEqual(len(chunks), 3, "Should create 3 chunks")
        
        # First chunk should contain the introductory text
        self.assertTrue("introductory text" in chunks[0], 
                       "First chunk should contain introductory text")
    
    def test_headings_without_content(self):
        """Test headings that have no content after them"""
        content = """# Empty Heading 1

# Empty Heading 2

## Empty Sub Heading"""
        
        chunks = self.chunker.chunk_by_headings(content)
        self.assertEqual(len(chunks), 3, "Should create chunks even for empty headings")
    
    def test_complex_educational_content(self):
        """Test with complex educational content structure"""
        content = """# Chapter 5: Geometry

Introduction to geometry concepts for Grade 5 students.

## Basic Shapes

### Triangles
A triangle has three sides and three angles.

### Rectangles  
A rectangle has four sides with opposite sides equal.

## Area and Perimeter

### Calculating Area
Area is the space inside a shape.

### Calculating Perimeter
Perimeter is the distance around a shape.

# Chapter 6: Measurements

Different types of measurements.

## Length Measurements
Using rulers and measuring tapes."""
        
        chunks = self.chunker.chunk_by_headings(content)
        
        # Should split on # and ## but not ###
        expected_chunk_count = 6  # 2 main chapters + 4 sections
        self.assertEqual(len(chunks), expected_chunk_count, 
                        f"Expected {expected_chunk_count} chunks for complex content")
    
    def test_special_characters_in_headings(self):
        """Test headings with special characters"""
        content = """# Chapter 1: Numbers & Operations

Basic arithmetic operations.

## Addition & Subtraction
Learn to add and subtract.

## Multiplication × Division
Learn to multiply and divide."""
        
        chunks = self.chunker.chunk_by_headings(content)
        self.assertEqual(len(chunks), 3, "Should handle special characters in headings")
    
    def test_real_world_page_content(self):
        """Test with actual page content from JSON file"""
        content = """# Chapter 2: Fractions

Tamanna is a student of Grade 5. She has two chocolates of different sizes. She says that 1/3 of one of her chocolates is bigger than 1/2 of the other chocolate. Is that correct? Explain why this is so.

[Illustration: Two chocolate bars. The first is divided into two equal parts, with one part labeled "Identify 1/2 of the chocolate". The second is divided into three equal parts, with one part labeled "Identify 1/3 of the chocolate".]

When can we say that 1/2 of something is greater than 1/3 of something?

To compare two fractions of two wholes, the wholes from which the fractions are derived must be the same.

## Playing with a Grid

[Illustration: Three grids labeled A, B, and C. Each grid is a 6x8 rectangle divided into equal squares.]

* Shade 1/8 of Grid A in red.
* Shade 1/6 of Grid B in blue.
* Shade 1/12 of Grid C in yellow.
* Do you see 1/3 in any of the grids? Mark it."""
        pdb.set_trace()
        chunks = self.chunker.chunk_by_headings_advanced(content)
        pdb.set_trace()  # Debugging line to inspect chunks
        # Assertions
        self.assertEqual(len(chunks), 2, "Should create exactly 2 chunks")
        
        # Check first chunk
        first_chunk = chunks[0]
        self.assertTrue(first_chunk.startswith("# Chapter 2: Fractions"))
        self.assertIn("Tamanna is a student", first_chunk)
        self.assertIn("wholes from which the fractions are derived", first_chunk)
        self.assertNotIn("## Playing with a Grid", first_chunk)
        
        # Check second chunk  
        second_chunk = chunks[1]
        self.assertTrue(second_chunk.startswith("## Playing with a Grid"))
        self.assertIn("Shade 1/8 of Grid A", second_chunk)
        self.assertIn("Do you see 1/3 in any of the grids", second_chunk)
        
        # Verify no content is lost
        combined_content = "\n\n".join(chunks)
        original_words = set(content.split())
        combined_words = set(combined_content.split())
        missing_words = original_words - combined_words
        self.assertEqual(len(missing_words), 0, f"No words should be lost in chunking. Missing: {missing_words}")
        
        print(f"\n=== Real World Content Test Results ===")
        print(f"Original length: {len(content)} characters")
        print(f"Number of chunks: {len(chunks)}")
        print(f"Chunk 1 length: {len(chunks[0])} chars, starts with: {chunks[0][:50]}...")
        print(f"Chunk 2 length: {len(chunks[1])} chars, starts with: {chunks[1][:50]}...")


def run_specific_test():
    """Run the specific test for the fractions content"""
    test_case = TestDocumentChunking()
    test_case.setUp()
    pdb.set_trace() 
    print("Running specific test for fractions content...")
    result = test_case.test_real_world_page_content()
    pdb.set_trace()  # Debugging line to inspect result
    
    print("\nExpected behavior:")
    print("- Should create 2 chunks")
    print("- Chunk 1: Everything from '# Chapter 2: Fractions' to before '## Playing with a Grid'")
    print("- Chunk 2: Everything from '## Playing with a Grid' to the end")
    
    return result


def run_all_tests():
    """Run all unit tests"""
    print("Running all document chunking tests...\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDocumentChunking)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "specific":
        # Run only the specific test
        run_specific_test()
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)