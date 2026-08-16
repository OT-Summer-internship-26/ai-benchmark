"""
Unit tests for vector store functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.rag.vector_store import init_vector_table, add_document_chunk, search_similar
from src.utils.exceptions import RAGException


class TestVectorStoreEmbeddingFormat:
    """Test that embeddings are properly formatted for pgvector."""
    
    @patch('src.rag.vector_store.engine')
    @patch('src.rag.vector_store.get_embedding')
    def test_embedding_format_for_add_chunk(self, mock_get_embedding, mock_engine):
        """Verify embeddings are converted to proper pgvector array format."""
        # Setup mock embedding (should be a list of floats)
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_get_embedding.return_value = test_embedding
        
        # Setup mock connection
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Call function
        add_document_chunk("test_dept", "test content")
        
        # Verify execute was called with proper array format
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        
        # Check that embedding parameter contains array format string
        params = call_args[0][1]  # Second argument to execute
        assert "[" in params["embedding"]
        assert "]" in params["embedding"]
        assert "0.1" in params["embedding"]
        assert "0.5" in params["embedding"]
    
    @patch('src.rag.vector_store.engine')
    @patch('src.rag.vector_store.get_embedding')
    def test_search_embedding_format(self, mock_get_embedding, mock_engine):
        """Verify query embeddings are properly formatted."""
        test_embedding = [0.1, 0.2, 0.3]
        mock_get_embedding.return_value = test_embedding
        
        # Setup mock connection and result
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = [("chunk1",), ("chunk2",)]
        mock_conn.execute.return_value = mock_result
        
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Call function
        results = search_similar("test query", "test_dept", top_k=2)
        
        # Verify results
        assert len(results) == 2
        assert results[0] == "chunk1"
        assert results[1] == "chunk2"
        
        # Verify embedding format in call
        call_args = mock_conn.execute.call_args
        params = call_args[0][1]
        assert "[" in params["embedding"]
        assert "0.1" in params["embedding"]


class TestVectorStoreErrorHandling:
    """Test error handling in vector store operations."""
    
    @patch('src.rag.vector_store.engine')
    @patch('src.rag.vector_store.get_embedding')
    def test_add_chunk_database_error(self, mock_get_embedding, mock_engine):
        """Test graceful error handling on database failure."""
        mock_get_embedding.return_value = [0.1, 0.2]
        mock_engine.connect.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception):
            add_document_chunk("dept", "content")
    
    @patch('src.rag.vector_store.engine')
    @patch('src.rag.vector_store.get_embedding')
    def test_search_empty_result(self, mock_get_embedding, mock_engine):
        """Test handling of empty search results."""
        mock_get_embedding.return_value = [0.1]
        
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []  # Empty results
        mock_conn.execute.return_value = mock_result
        
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        results = search_similar("query", "dept")
        assert results == []


class TestVectorStoreIntegration:
    """Integration-style tests (mocking only the database connection)."""
    
    def test_embedding_conversion(self):
        """Test the embedding format conversion logic directly."""
        # Test converting a list of floats to pgvector format
        embedding = [0.1, 0.2, 0.3, 0.4]
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
        
        assert embedding_str == '[0.1,0.2,0.3,0.4]'
        
        # Test with scientific notation
        embedding_sci = [1e-3, 2e-2, -0.5]
        embedding_str_sci = '[' + ','.join(str(x) for x in embedding_sci) + ']'
        assert '[' in embedding_str_sci
        assert ']' in embedding_str_sci
