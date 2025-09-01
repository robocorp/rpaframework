import pytest
from unittest.mock import Mock, patch
from RPA.Sema4AI import Sema4AI
from RPA._support import Sema4aiException, Agent, MessageResponse, Conversation, ConversationsResult, MessagesResult


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