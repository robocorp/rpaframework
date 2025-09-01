"""Sema4ai Agent API client library."""

import logging
import time
from typing import Optional
from robocorp import log

from RPA._support import (
    Agent,
    MessageResponse,
    ConversationsResult,
    MessagesResult,
    Sema4aiException,
    _AgentAPIClient,
    timed_method
)


class Sema4AI:
    """Sema4ai Agent API client."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._client = None

    @log.suppress_variables()
    @timed_method
    def ask_agent(
        self,
        message: str,
        agent_api_key: str,
        agent_api_endpoint: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_name: Optional[str] = None
    ) -> MessageResponse:
        """Ask an agent a question and get a response.

        :param message: The message content to send
        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :param conversation_id: Optional conversation ID for continuing existing conversations
        :param conversation_name: Optional name for new conversation
        :return: MessageResponse object containing conversation ID, response, agent name, agent ID, and execution time
        """
        start_time = time.time()

        # Validate parameters
        if not agent_id and not agent_name:
            raise ValueError("Either agent_id or agent_name must be provided")
        if agent_id and agent_name:
            raise ValueError("Cannot provide both agent_id and agent_name - use only one")

        client = _AgentAPIClient(agent_api_key=agent_api_key, api_url=agent_api_endpoint)

        # Get agent information
        if agent_id:
            # Use provided agent_id directly
            agent = Agent(agent_id=agent_id, agent_name=agent_id)
        else:
            # Look up agent by name
            agent = client.get_agent_by_name(agent_name)
            if not agent:
                # Get available agents for error message
                all_agents = client.get_all_agents()
                available_names = [a.agent_name for a in all_agents]
                raise Sema4aiException(
                    f"Agent '{agent_name}' not found. Available agents: {', '.join(available_names)}"
                )

        # Create conversation if needed
        if not conversation_id:
            if not conversation_name:
                conversation_name = f"Conversation with {agent.agent_name}"

            conversation = client.create_conversation(
                agent_id=agent.agent_id,
                conversation_name=conversation_name
            )
            conversation_id = conversation.conversation_id

        # Send the message
        response_text = client.send_message(
            conversation_id=conversation_id,
            agent_id=agent.agent_id,
            message=message
        )

        execution_time = round(time.time() - start_time, 3)

        return MessageResponse(
            conversation_id=conversation_id,
            response=response_text,
            agent_name=agent.agent_name,
            agent_id=agent.agent_id,
            execution_time=execution_time
        )

    @log.suppress_variables()
    @timed_method
    def get_conversations(
        self,
        agent_api_key: str,
        agent_api_endpoint: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> ConversationsResult:
        """Get all conversations for an agent.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :return: List of Conversation objects
        """
        # Validate parameters
        if not agent_id and not agent_name:
            raise ValueError("Either agent_id or agent_name must be provided")
        if agent_id and agent_name:
            raise ValueError("Cannot provide both agent_id and agent_name - use only one")

        client = _AgentAPIClient(agent_api_key=agent_api_key, api_url=agent_api_endpoint)

        # Get agent information
        if agent_id:
            # Use provided agent_id directly
            target_agent_id = agent_id
        else:
            # Look up agent by name
            agent = client.get_agent_by_name(agent_name)
            if not agent:
                # Get available agents for error message
                all_agents = client.get_all_agents()
                available_names = [a.agent_name for a in all_agents]
                raise Sema4aiException(
                    f"Agent '{agent_name}' not found. Available agents: {', '.join(available_names)}"
                )
            target_agent_id = agent.agent_id

        return client.get_conversations(target_agent_id)

    @log.suppress_variables()
    @timed_method
    def get_messages(
        self,
        agent_api_key: str,
        agent_api_endpoint: str,
        conversation_id: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> MessagesResult:
        """Get all messages in a conversation.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param conversation_id: The conversation ID
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :return: List of message dictionaries
        """
        # Validate parameters
        if not agent_id and not agent_name:
            raise ValueError("Either agent_id or agent_name must be provided")
        if agent_id and agent_name:
            raise ValueError("Cannot provide both agent_id and agent_name - use only one")

        client = _AgentAPIClient(agent_api_key=agent_api_key, api_url=agent_api_endpoint)

        # Get agent information
        if agent_id:
            # Use provided agent_id directly
            target_agent_id = agent_id
        else:
            # Look up agent by name
            agent = client.get_agent_by_name(agent_name)
            if not agent:
                # Get available agents for error message
                all_agents = client.get_all_agents()
                available_names = [a.agent_name for a in all_agents]
                raise Sema4aiException(
                    f"Agent '{agent_name}' not found. Available agents: {', '.join(available_names)}"
                )
            target_agent_id = agent.agent_id

        return client.get_messages(target_agent_id, conversation_id)
