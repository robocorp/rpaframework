import pytest
from unittest.mock import Mock, patch, MagicMock
from RPA.Sema4ai import Sema4ai, Sema4aiException, Agent, MessageResponse


class TestSema4ai:
    def test_init(self):
        """Test that the library can be initialized."""
        sema4ai = Sema4ai()
        assert sema4ai is not None
        assert hasattr(sema4ai, 'logger')

    @patch('RPA.Sema4ai._AgentAPIClient')
    def test_ask_agent_with_agent_name(self, mock_client_class):
        """Test asking agent by name."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_agent = Agent(id="agent_123", name="Test Agent")
        mock_client.get_agent_by_name.return_value = mock_agent
        
        mock_conversation = Mock()
        mock_conversation.id = "conv_456"
        mock_client.create_conversation.return_value = mock_conversation
        
        mock_client.send_message.return_value = "Hello! I'm a test agent."
        
        # Test the method
        sema4ai = Sema4ai()
        result = sema4ai.ask_agent(
            message="Hello",
            api_key="LOCAL",
            agent_name="Test Agent"
        )
        
        # Assertions
        assert isinstance(result, MessageResponse)
        assert result.conversation_id == "conv_456"
        assert result.response == "Hello! I'm a test agent."
        assert result.agent_name == "Test Agent"
        assert result.agent_id == "agent_123"
        
        # Verify method calls
        mock_client.get_agent_by_name.assert_called_once_with("Test Agent")
        mock_client.create_conversation.assert_called_once_with(
            agent_id="agent_123",
            conversation_name="Conversation with Test Agent"
        )
        mock_client.send_message.assert_called_once_with(
            conversation_id="conv_456",
            agent_id="agent_123",
            message="Hello"
        )

    @patch('RPA.Sema4ai._AgentAPIClient')
    def test_ask_agent_with_agent_id_bypass(self, mock_client_class):
        """Test asking agent with agent_id bypass."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_conversation = Mock()
        mock_conversation.id = "conv_456"
        mock_client.create_conversation.return_value = mock_conversation
        
        mock_client.send_message.return_value = "Hello! I'm bypassed."
        
        # Test the method
        sema4ai = Sema4ai()
        result = sema4ai.ask_agent(
            message="Hello",
            api_key="LOCAL",
            agent_id="agent_123",  # Bypass agent lookup
            agent_api_endpoint="https://api.sema4.ai/v1"
        )
        
        # Assertions
        assert isinstance(result, MessageResponse)
        assert result.conversation_id == "conv_456"
        assert result.response == "Hello! I'm bypassed."
        assert result.agent_name == "agent_123"  # Should use agent_id as name when no agent_name provided
        assert result.agent_id == "agent_123"
        
        # Verify that client was created with custom URL
        mock_client_class.assert_called_once_with(
            api_key="LOCAL", 
            api_url="https://api.sema4.ai/v1"
        )
        mock_client.create_conversation.assert_called_once_with(
            agent_id="agent_123",
            conversation_name="Conversation with agent_123"
        )

    @patch('RPA.Sema4ai._AgentAPIClient')
    def test_ask_agent_with_existing_conversation(self, mock_client_class):
        """Test asking agent with existing conversation."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_agent = Agent(id="agent_123", name="Test Agent")
        mock_client.get_agent_by_name.return_value = mock_agent
        mock_client.send_message.return_value = "Continuing conversation."
        
        # Test the method
        sema4ai = Sema4ai()
        result = sema4ai.ask_agent(
            message="How are you?",
            api_key="LOCAL",
            agent_name="Test Agent",
            conversation_id="existing_conv_789"
        )
        
        # Assertions
        assert result.conversation_id == "existing_conv_789"
        assert result.response == "Continuing conversation."
        
        # Verify that create_conversation was NOT called
        mock_client.create_conversation.assert_not_called()
        mock_client.send_message.assert_called_once_with(
            conversation_id="existing_conv_789",
            agent_id="agent_123",
            message="How are you?"
        )

    @patch('RPA.Sema4ai._AgentAPIClient')
    def test_ask_agent_agent_not_found(self, mock_client_class):
        """Test asking agent when agent is not found."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        mock_client.get_agent_by_name.return_value = None
        mock_client.get_all_agents.return_value = [
            Agent(id="agent1", name="Agent 1"),
            Agent(id="agent2", name="Agent 2")
        ]
        
        # Test the method - should raise exception
        sema4ai = Sema4ai()
        with pytest.raises(Sema4aiException) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                api_key="LOCAL",
                agent_name="Nonexistent Agent"
            )
        
        assert "Agent 'Nonexistent Agent' not found" in str(exc_info.value)
        assert "Available agents: Agent 1, Agent 2" in str(exc_info.value)

    def test_agent_id_without_endpoint_validation(self):
        """Test that agent_id requires agent_api_endpoint."""
        sema4ai = Sema4ai()
        with pytest.raises(Sema4aiException) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                api_key="LOCAL",
                agent_id="agent_123"  # Missing agent_api_endpoint
            )
        
        assert "agent_api_endpoint is required when agent_id is provided" in str(exc_info.value)

    def test_endpoint_without_agent_id_validation(self):
        """Test that agent_api_endpoint requires agent_id."""
        sema4ai = Sema4ai()
        with pytest.raises(Sema4aiException) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                api_key="LOCAL",
                agent_api_endpoint="https://api.sema4.ai/v1"  # Missing agent_id
            )
        
        assert "agent_id is required when agent_api_endpoint is provided" in str(exc_info.value)

    def test_missing_both_agent_name_and_id(self):
        """Test that either agent_name or agent_id must be provided."""
        sema4ai = Sema4ai()
        with pytest.raises(Sema4aiException) as exc_info:
            sema4ai.ask_agent(
                message="Hello",
                api_key="LOCAL"
                # Missing both agent_name and agent_id
            )
        
        assert "Either agent_name or agent_id (with agent_api_endpoint) must be provided" in str(exc_info.value)

    def test_url_normalization_tenant_url(self):
        """Test that tenant URLs are normalized correctly."""
        from RPA.Sema4ai import _AgentAPIClient
        
        with patch('RPA.Sema4ai.sema4ai_http'):
            client = _AgentAPIClient(api_key="test", api_url="https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0")
            expected = "https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0/api/v1"
            assert client.api_url == expected

    def test_url_normalization_base_domain(self):
        """Test that base domain URLs are normalized correctly."""
        from RPA.Sema4ai import _AgentAPIClient
        
        with patch('RPA.Sema4ai.sema4ai_http'):
            client = _AgentAPIClient(api_key="test", api_url="https://ace-fe1cd46f.prod-demo.sema4ai.work")
            expected = "https://ace-fe1cd46f.prod-demo.sema4ai.work/api/v1"
            assert client.api_url == expected

    def test_url_normalization_api_url(self):
        """Test that API URLs are left unchanged."""
        from RPA.Sema4ai import _AgentAPIClient
        
        with patch('RPA.Sema4ai.sema4ai_http'):
            api_url = "https://ace-fe1cd46f.prod-demo.sema4ai.work/api/v1"
            client = _AgentAPIClient(api_key="test", api_url=api_url)
            assert client.api_url == api_url

    @patch('RPA.Sema4ai.sema4ai_http', None)
    def test_missing_dependency(self):
        """Test that missing sema4ai_http dependency is handled."""
        with pytest.raises(ImportError) as exc_info:
            from RPA.Sema4ai import _AgentAPIClient
            _AgentAPIClient()
        
        assert "sema4ai-actions package is required" in str(exc_info.value)