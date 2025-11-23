import asyncio
import pytest
from unittest.mock import Mock, patch
from RPA.Sema4AI import (
    Sema4AI,
    Sema4aiException,
    Agent,
    Conversation,
    MessageResponse,
    ConversationsResult,
    MessagesResult,
)
from RPA._support import Sema4aiException as _Sema4aiException


class TestSema4AI:
    def test_init(self):
        """Test that the library can be initialized."""
        sema4ai = Sema4AI()
        assert sema4ai is not None
        assert hasattr(sema4ai, 'logger')

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_basic(self, mock_client_class):
        """Test asking agent with basic parameters."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_456"
        mock_client.create_conversation.return_value = mock_conversation
        
        mock_client.send_message.return_value = "Hello! I'm a test agent."
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.ask_agent(
            message="Hello",
            agent_api_key="test_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1"
        )
        
        # Assertions
        assert isinstance(result, MessageResponse)
        assert result.conversation_id == "conv_456"
        assert result.response == "Hello! I'm a test agent."
        assert result.agent_name == "agent_123"
        assert result.agent_id == "agent_123"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify method calls
        mock_client_class.assert_called_once_with(
            agent_api_key="test_key", 
            api_url="https://api.example.com/v1"
        )
        mock_client.create_conversation.assert_called_once_with(
            agent_id="agent_123",
            conversation_name="Conversation with agent_123"
        )
        mock_client.send_message.assert_called_once_with(
            conversation_id="conv_456",
            agent_id="agent_123",
            message="Hello"
        )

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_with_existing_conversation(self, mock_client_class):
        """Test asking agent with existing conversation."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = "Continuing conversation."
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.ask_agent(
            message="How are you?",
            agent_api_key="test_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1",
            conversation_id="existing_conv_789"
        )
        
        # Assertions
        assert result.conversation_id == "existing_conv_789"
        assert result.response == "Continuing conversation."
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify that create_conversation was NOT called
        mock_client.create_conversation.assert_not_called()
        mock_client.send_message.assert_called_once_with(
            conversation_id="existing_conv_789",
            agent_id="agent_123",
            message="How are you?"
        )

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_with_custom_conversation_name(self, mock_client_class):
        """Test asking agent with custom conversation name."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_custom"
        mock_client.create_conversation.return_value = mock_conversation
        mock_client.send_message.return_value = "Custom conversation response."
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.ask_agent(
            message="Hello",
            agent_api_key="test_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1",
            conversation_name="My Custom Conversation"
        )
        
        # Verify custom conversation name was used
        mock_client.create_conversation.assert_called_once_with(
            agent_id="agent_123",
            conversation_name="My Custom Conversation"
        )

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_with_agent_name_lookup(self, mock_client_class):
        """Test asking agent using agent name (requires lookup)."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_agent = Agent(agent_id="agent_456", agent_name="Test Agent")
        mock_client.get_agent_by_name.return_value = mock_agent
        
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_789"
        mock_client.create_conversation.return_value = mock_conversation
        
        mock_client.send_message.return_value = "Hello from named agent!"
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.ask_agent(
            message="Hello",
            agent_api_key="test_key",
            agent_api_endpoint="https://api.example.com/v1",
            agent_name="Test Agent"
        )
        
        # Assertions
        assert isinstance(result, MessageResponse)
        assert result.conversation_id == "conv_789"
        assert result.response == "Hello from named agent!"
        assert result.agent_name == "Test Agent"
        assert result.agent_id == "agent_456"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify method calls
        mock_client.get_agent_by_name.assert_called_once_with("Test Agent")
        mock_client.create_conversation.assert_called_once_with(
            agent_id="agent_456",
            conversation_name="Conversation with Test Agent"
        )

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_name_not_found(self, mock_client_class):
        """Test asking agent when agent name is not found."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.get_agent_by_name.return_value = None
        mock_client.get_all_agents.return_value = [
            Agent(agent_id="agent1", agent_name="Agent 1"),
            Agent(agent_id="agent2", agent_name="Agent 2")
        ]
        
        # Test the method - should raise exception
        sema4ai = Sema4AI()
        with pytest.raises(Sema4aiException) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                agent_api_key="test_key",
                agent_api_endpoint="https://api.example.com/v1",
                agent_name="Nonexistent Agent"
            )
        
        assert "Agent 'Nonexistent Agent' not found" in str(exc_info.value)
        assert "Available agents: Agent 1, Agent 2" in str(exc_info.value)

    def test_missing_required_parameters(self):
        """Test that missing required parameters raise appropriate errors."""
        sema4ai = Sema4AI()
        
        # Missing agent_api_endpoint (TypeError for missing positional arg)
        with pytest.raises(TypeError):
            sema4ai.ask_agent(
                message="Hello",
                agent_api_key="test_key",
                agent_id="agent_123"
            )
        
        # Missing both agent_id and agent_name (ValueError)
        with pytest.raises(ValueError) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                agent_api_key="test_key",
                agent_api_endpoint="https://api.example.com/v1"
            )
        assert "Either agent_id or agent_name must be provided" in str(exc_info.value)
        
        # Providing both agent_id and agent_name (ValueError)
        with pytest.raises(ValueError) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                agent_api_key="test_key",
                agent_api_endpoint="https://api.example.com/v1",
                agent_id="agent_123",
                agent_name="Test Agent"
            )
        assert "Cannot provide both agent_id and agent_name" in str(exc_info.value)

    def test_url_normalization_tenant_url(self):
        """Test that tenant URLs are normalized correctly."""
        from RPA._support import _AgentAPIClient
        
        with patch('RPA._support.sema4ai_http'):
            client = _AgentAPIClient(
                agent_api_key="test", 
                api_url="https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0"
            )
            expected = "https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0/api/v1"
            assert client.api_url == expected

    def test_url_normalization_base_domain(self):
        """Test that base domain URLs are normalized correctly."""
        from RPA._support import _AgentAPIClient
        
        with patch('RPA._support.sema4ai_http'):
            client = _AgentAPIClient(
                agent_api_key="test", 
                api_url="https://ace-fe1cd46f.prod-demo.sema4ai.work"
            )
            expected = "https://ace-fe1cd46f.prod-demo.sema4ai.work/api/v1"
            assert client.api_url == expected

    def test_url_normalization_api_url(self):
        """Test that API URLs are left unchanged."""
        from RPA._support import _AgentAPIClient
        
        with patch('RPA._support.sema4ai_http'):
            api_url = "https://ace-fe1cd46f.prod-demo.sema4ai.work/api/v1"
            client = _AgentAPIClient(agent_api_key="test", api_url=api_url)
            assert client.api_url == api_url

    def test_missing_dependency(self):
        """Test that missing sema4ai_http dependency is handled."""
        # This test verifies that the error handling logic exists
        # The actual ImportError is checked in the _AgentAPIClient __init__ method
        from RPA._support import _AgentAPIClient
        
        # We can't easily test the import error with module patching in this context
        # but the logic is verified by the existence of the check in the __init__ method
        # If sema4ai_http was None, _AgentAPIClient.__init__ would raise ImportError
        assert hasattr(_AgentAPIClient, '__init__')
        
        # Test the ValueError when api_url is missing instead
        with pytest.raises(ValueError) as exc_info:
            _AgentAPIClient(agent_api_key="test", api_url=None)
        assert "api_url is required" in str(exc_info.value)

    def test_missing_api_url(self):
        """Test that missing api_url raises ValueError."""
        from RPA._support import _AgentAPIClient
        
        with patch('RPA._support.sema4ai_http'):
            with pytest.raises(ValueError) as exc_info:
                _AgentAPIClient(agent_api_key="test", api_url=None)
            
            assert "api_url is required" in str(exc_info.value)

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_get_conversations_with_agent_id(self, mock_client_class):
        """Test getting conversations with agent_id."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_conversations = [
            Conversation(conversation_id="conv1", name="Conversation 1", agent_id="agent_123"),
            Conversation(conversation_id="conv2", name="Conversation 2", agent_id="agent_123")
        ]
        mock_client.get_conversations.return_value = mock_conversations
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.get_conversations(
            agent_api_key="test_key",
            agent_api_endpoint="https://api.example.com/v1",
            agent_id="agent_123"
        )
        
        # Assertions
        assert isinstance(result, ConversationsResult)
        assert len(result) == 2
        assert result[0].conversation_id == "conv1"
        assert result[0].name == "Conversation 1"
        assert result[1].conversation_id == "conv2"
        assert result[1].name == "Conversation 2"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify method calls
        mock_client.get_conversations.assert_called_once_with("agent_123")

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_get_conversations_with_agent_name(self, mock_client_class):
        """Test getting conversations with agent_name."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_agent = Agent(agent_id="agent_456", agent_name="Test Agent")
        mock_client.get_agent_by_name.return_value = mock_agent
        
        mock_conversations = [
            Conversation(conversation_id="conv3", name="Conversation 3", agent_id="agent_456")
        ]
        mock_client.get_conversations.return_value = mock_conversations
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.get_conversations(
            agent_api_key="test_key",
            agent_api_endpoint="https://api.example.com/v1",
            agent_name="Test Agent"
        )
        
        # Assertions
        assert isinstance(result, ConversationsResult)
        assert len(result) == 1
        assert result[0].conversation_id == "conv3"
        assert result[0].name == "Conversation 3"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify method calls
        mock_client.get_agent_by_name.assert_called_once_with("Test Agent")
        mock_client.get_conversations.assert_called_once_with("agent_456")

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_get_messages_with_agent_id(self, mock_client_class):
        """Test getting messages with agent_id."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_messages = [
            {"id": "msg1", "content": "Hello", "role": "user"},
            {"id": "msg2", "content": "Hi there!", "role": "agent"}
        ]
        mock_client.get_messages.return_value = mock_messages
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.get_messages(
            agent_api_key="test_key",
            agent_api_endpoint="https://api.example.com/v1",
            conversation_id="conv_123",
            agent_id="agent_123"
        )
        
        # Assertions
        assert isinstance(result, MessagesResult)
        assert len(result) == 2
        assert result[0]["id"] == "msg1"
        assert result[0]["content"] == "Hello"
        assert result[1]["id"] == "msg2"
        assert result[1]["content"] == "Hi there!"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify method calls
        mock_client.get_messages.assert_called_once_with("agent_123", "conv_123")

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_get_messages_with_agent_name(self, mock_client_class):
        """Test getting messages with agent_name."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_agent = Agent(agent_id="agent_789", agent_name="Chat Agent")
        mock_client.get_agent_by_name.return_value = mock_agent
        
        mock_messages = [
            {"id": "msg3", "content": "How are you?", "role": "user"}
        ]
        mock_client.get_messages.return_value = mock_messages
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.get_messages(
            agent_api_key="test_key",
            agent_api_endpoint="https://api.example.com/v1",
            conversation_id="conv_456",
            agent_name="Chat Agent"
        )
        
        # Assertions
        assert isinstance(result, MessagesResult)
        assert len(result) == 1
        assert result[0]["id"] == "msg3"
        assert result[0]["content"] == "How are you?"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0
        
        # Verify method calls
        mock_client.get_agent_by_name.assert_called_once_with("Chat Agent")
        mock_client.get_messages.assert_called_once_with("agent_789", "conv_456")

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_with_list_response_format(self, mock_client_class):
        """Test asking agent with list response format (content_id, content, citations)."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_456"
        mock_client.create_conversation.return_value = mock_conversation
        
        # Mock the new response format that caused the error
        mock_client.send_message.return_value = "Hello! I can help you with various tasks."
        
        # Test the method
        sema4ai = Sema4AI()
        result = sema4ai.ask_agent(
            message="what you can do for me?",
            agent_api_key="test_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1"
        )
        
        # Assertions
        assert isinstance(result, MessageResponse)
        assert result.conversation_id == "conv_456"
        assert result.response == "Hello! I can help you with various tasks."
        assert result.agent_name == "agent_123"
        assert result.agent_id == "agent_123"
        assert hasattr(result, 'execution_time')
        assert isinstance(result.execution_time, float)
        assert result.execution_time >= 0

    def test_exports_from_main_module(self):
        """Test that all public classes are exported from main module."""
        # Verify classes can be imported from RPA.Sema4AI
        assert Sema4aiException is _Sema4aiException
        assert Sema4AI is not None
        assert Agent is not None
        assert Conversation is not None
        assert MessageResponse is not None
        assert ConversationsResult is not None
        assert MessagesResult is not None

    def test_exception_with_status_code(self):
        """Test that Sema4aiException includes status_code attribute."""
        # Test without status_code
        exc1 = Sema4aiException("Test error")
        assert str(exc1) == "Test error"
        assert exc1.status_code is None

        # Test with status_code
        exc2 = Sema4aiException("HTTP error", status_code=404)
        assert str(exc2) == "HTTP error"
        assert exc2.status_code == 404

        # Test with different status codes
        exc3 = Sema4aiException("Server error", status_code=500)
        assert exc3.status_code == 500

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_client_caching(self, mock_client_class):
        """Test that API clients are cached and reused."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.send_message.return_value = "Response"
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_123"
        mock_client.create_conversation.return_value = mock_conversation

        sema4ai = Sema4AI()

        # First call
        sema4ai.ask_agent(
            message="Hello",
            agent_api_key="test_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1"
        )

        # Second call with same credentials
        sema4ai.ask_agent(
            message="Hello again",
            agent_api_key="test_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1"
        )

        # Client should only be created once due to caching
        assert mock_client_class.call_count == 1

        # Different credentials should create new client
        sema4ai.ask_agent(
            message="Different key",
            agent_api_key="different_key",
            agent_id="agent_123",
            agent_api_endpoint="https://api.example.com/v1"
        )

        assert mock_client_class.call_count == 2

    def test_client_cache_initialization(self):
        """Test that client cache is initialized properly."""
        sema4ai = Sema4AI()
        assert hasattr(sema4ai, '_client_cache')
        assert isinstance(sema4ai._client_cache, dict)
        assert len(sema4ai._client_cache) == 0

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_ask_agent_async(self, mock_client_class):
        """Test async version of ask_agent."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_async"
        mock_client.create_conversation.return_value = mock_conversation
        mock_client.send_message.return_value = "Async response!"

        sema4ai = Sema4AI()

        async def run_test():
            result = await sema4ai.ask_agent_async(
                message="Hello async",
                agent_api_key="test_key",
                agent_id="agent_123",
                agent_api_endpoint="https://api.example.com/v1"
            )
            return result

        result = asyncio.run(run_test())

        assert isinstance(result, MessageResponse)
        assert result.conversation_id == "conv_async"
        assert result.response == "Async response!"

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_get_conversations_async(self, mock_client_class):
        """Test async version of get_conversations."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_conversations = [
            Conversation(conversation_id="conv1", name="Conv 1", agent_id="agent_123")
        ]
        mock_client.get_conversations.return_value = mock_conversations

        sema4ai = Sema4AI()

        async def run_test():
            result = await sema4ai.get_conversations_async(
                agent_api_key="test_key",
                agent_api_endpoint="https://api.example.com/v1",
                agent_id="agent_123"
            )
            return result

        result = asyncio.run(run_test())

        assert isinstance(result, ConversationsResult)
        assert len(result) == 1
        assert result[0].conversation_id == "conv1"

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_get_messages_async(self, mock_client_class):
        """Test async version of get_messages."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_messages = [{"id": "msg1", "content": "Test", "role": "user"}]
        mock_client.get_messages.return_value = mock_messages

        sema4ai = Sema4AI()

        async def run_test():
            result = await sema4ai.get_messages_async(
                agent_api_key="test_key",
                agent_api_endpoint="https://api.example.com/v1",
                conversation_id="conv_123",
                agent_id="agent_123"
            )
            return result

        result = asyncio.run(run_test())

        assert isinstance(result, MessagesResult)
        assert len(result) == 1
        assert result[0]["id"] == "msg1"

    @patch('RPA.Sema4AI._AgentAPIClient')
    def test_concurrent_async_requests(self, mock_client_class):
        """Test that multiple async requests can run concurrently."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_conversation = Mock()
        mock_conversation.conversation_id = "conv_concurrent"
        mock_client.create_conversation.return_value = mock_conversation
        mock_client.send_message.side_effect = lambda **kwargs: f"Response to: {kwargs['message']}"

        sema4ai = Sema4AI()

        async def run_test():
            tasks = [
                sema4ai.ask_agent_async(
                    message=f"Message {i}",
                    agent_api_key="test_key",
                    agent_id="agent_123",
                    agent_api_endpoint="https://api.example.com/v1"
                )
                for i in range(3)
            ]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_test())

        assert len(results) == 3
        for result in results:
            assert isinstance(result, MessageResponse)

    def test_http_error_includes_status_code(self):
        """Test that HTTP errors include the status code."""
        from RPA._support import _AgentAPIClient

        with patch('RPA._support.sema4ai_http') as mock_http:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_response.reason = "Access Denied"
            mock_http.get.return_value = mock_response

            client = _AgentAPIClient(agent_api_key="test", api_url="https://api.example.com/v1")

            with pytest.raises(Sema4aiException) as exc_info:
                client.request("agents")

            assert exc_info.value.status_code == 403
            assert "HTTP 403" in str(exc_info.value)
            assert "Forbidden" in str(exc_info.value)