"""Sema4ai Agent API client library."""

import asyncio
import hashlib
import logging
import time
from functools import partial
from typing import Optional
from robocorp import log

from RPA._support import (
    Agent,
    Conversation,
    MessageResponse,
    ConversationsResult,
    MessagesResult,
    Sema4aiException,
    _AgentAPIClient,
    timed_method,
)

# Export public classes for easier imports
__all__ = [
    "Sema4AI",
    "Sema4aiException",
    "Agent",
    "Conversation",
    "MessageResponse",
    "ConversationsResult",
    "MessagesResult",
]


class Sema4AI:
    """Sema4ai Agent API client.

    This library provides keywords for interacting with Sema4.ai Agent API,
    allowing you to send messages to agents, retrieve conversations, and
    manage agent interactions programmatically.

    Example usage in Robot Framework:

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Sema4AI

        *** Variables ***
        ${API_KEY}         %{SEMA4AI_API_KEY}
        ${API_ENDPOINT}    https://api.sema4.ai/v1

        *** Tasks ***
        Chat With Agent
            ${response}=    Ask Agent
            ...    message=What is the weather today?
            ...    agent_api_key=${API_KEY}
            ...    agent_api_endpoint=${API_ENDPOINT}
            ...    agent_name=Weather Assistant
            Log    Response: ${response.response}

    Example usage in Python:

    .. code-block:: python

        from RPA.Sema4AI import Sema4AI

        client = Sema4AI()
        response = client.ask_agent(
            message="What is the weather today?",
            agent_api_key="your-api-key",
            agent_api_endpoint="https://api.sema4.ai/v1",
            agent_name="Weather Assistant"
        )
        print(f"Response: {response.response}")
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._client_cache: dict = {}

    def _get_client(
        self, agent_api_key: str, agent_api_endpoint: str
    ) -> _AgentAPIClient:
        """Get or create a cached API client for the given credentials.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :return: Cached or new _AgentAPIClient instance
        """
        # Create a hash key from credentials for caching
        cache_key = hashlib.sha256(
            f"{agent_api_key}:{agent_api_endpoint}".encode()
        ).hexdigest()[:16]

        if cache_key not in self._client_cache:
            self._client_cache[cache_key] = _AgentAPIClient(
                agent_api_key=agent_api_key, api_url=agent_api_endpoint
            )
        return self._client_cache[cache_key]

    def _validate_agent_params(
        self, agent_id: Optional[str], agent_name: Optional[str]
    ) -> None:
        """Validate that agent identification parameters are valid.

        :param agent_id: The agent ID
        :param agent_name: The agent name
        :raises ValueError: If neither or both parameters are provided
        """
        if not agent_id and not agent_name:
            raise ValueError("Either agent_id or agent_name must be provided")
        if agent_id and agent_name:
            raise ValueError(
                "Cannot provide both agent_id and agent_name - use only one"
            )

    def _resolve_agent(
        self,
        client: _AgentAPIClient,
        agent_id: Optional[str],
        agent_name: Optional[str],
    ) -> Agent:
        """Resolve agent from either agent_id or agent_name.

        :param client: The API client to use for lookups
        :param agent_id: The agent ID (if provided)
        :param agent_name: The agent name (if provided)
        :return: Agent object with resolved information
        :raises Sema4aiException: If agent_name is provided but not found
        """
        if agent_id:
            return Agent(agent_id=agent_id, agent_name=agent_id)

        agent = client.get_agent_by_name(agent_name)
        if not agent:
            all_agents = client.get_all_agents()
            available_names = [a.agent_name for a in all_agents]
            raise Sema4aiException(
                f"Agent '{agent_name}' not found. Available agents: {', '.join(available_names)}"
            )
        return agent

    def _resolve_agent_id(
        self,
        client: _AgentAPIClient,
        agent_id: Optional[str],
        agent_name: Optional[str],
    ) -> str:
        """Resolve agent ID from either agent_id or agent_name.

        :param client: The API client to use for lookups
        :param agent_id: The agent ID (if provided)
        :param agent_name: The agent name (if provided)
        :return: The resolved agent ID
        :raises Sema4aiException: If agent_name is provided but not found
        """
        if agent_id:
            return agent_id
        return self._resolve_agent(client, agent_id, agent_name).agent_id

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
        conversation_name: Optional[str] = None,
    ) -> MessageResponse:
        """Ask an agent a question and get a response.

        :param message: The message content to send
        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :param conversation_id: Optional conversation ID for continuing existing conversations
        :param conversation_name: Optional name for new conversation
        :return: MessageResponse object containing conversation ID, response, agent name,
            agent ID, and execution time

        Example:

        .. code-block:: python

            response = client.ask_agent(
                message="Hello, what can you help me with?",
                agent_api_key="your-api-key",
                agent_api_endpoint="https://api.sema4.ai/v1",
                agent_name="My Assistant"
            )
            print(f"Agent replied: {response.response}")
            print(f"Conversation ID: {response.conversation_id}")
        """
        start_time = time.time()

        self._validate_agent_params(agent_id, agent_name)
        client = self._get_client(agent_api_key, agent_api_endpoint)
        agent = self._resolve_agent(client, agent_id, agent_name)

        # Create conversation if needed
        if not conversation_id:
            if not conversation_name:
                conversation_name = f"Conversation with {agent.agent_name}"

            conversation = client.create_conversation(
                agent_id=agent.agent_id, conversation_name=conversation_name
            )
            conversation_id = conversation.conversation_id

        # Send the message
        response_text = client.send_message(
            conversation_id=conversation_id, agent_id=agent.agent_id, message=message
        )

        execution_time = round(time.time() - start_time, 3)

        return MessageResponse(
            conversation_id=conversation_id,
            response=response_text,
            agent_name=agent.agent_name,
            agent_id=agent.agent_id,
            execution_time=execution_time,
        )

    @log.suppress_variables()
    @timed_method
    def get_conversations(
        self,
        agent_api_key: str,
        agent_api_endpoint: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> ConversationsResult:
        """Get all conversations for an agent.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :return: ConversationsResult containing list of Conversation objects and execution time

        Example:

        .. code-block:: python

            result = client.get_conversations(
                agent_api_key="your-api-key",
                agent_api_endpoint="https://api.sema4.ai/v1",
                agent_name="My Assistant"
            )
            for conversation in result:
                print(f"Conversation: {conversation.name} (ID: {conversation.conversation_id})")
        """
        self._validate_agent_params(agent_id, agent_name)
        client = self._get_client(agent_api_key, agent_api_endpoint)
        target_agent_id = self._resolve_agent_id(client, agent_id, agent_name)

        return client.get_conversations(target_agent_id)

    @log.suppress_variables()
    @timed_method
    def get_messages(
        self,
        agent_api_key: str,
        agent_api_endpoint: str,
        conversation_id: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> MessagesResult:
        """Get all messages in a conversation.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param conversation_id: The conversation ID
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :return: MessagesResult containing list of message dictionaries and execution time

        Example:

        .. code-block:: python

            result = client.get_messages(
                agent_api_key="your-api-key",
                agent_api_endpoint="https://api.sema4.ai/v1",
                conversation_id="conv-123",
                agent_name="My Assistant"
            )
            for message in result:
                print(f"{message.get('role')}: {message.get('content')}")
        """
        self._validate_agent_params(agent_id, agent_name)
        client = self._get_client(agent_api_key, agent_api_endpoint)
        target_agent_id = self._resolve_agent_id(client, agent_id, agent_name)

        return client.get_messages(target_agent_id, conversation_id)

    # Async methods for non-blocking operations

    @log.suppress_variables()
    @timed_method
    async def ask_agent_async(
        self,
        message: str,
        agent_api_key: str,
        agent_api_endpoint: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_name: Optional[str] = None,
    ) -> MessageResponse:
        """Async version of ask_agent for non-blocking operations.

        This method runs the synchronous ask_agent in a thread pool executor,
        allowing for concurrent agent conversations without blocking the event loop.

        :param message: The message content to send
        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :param conversation_id: Optional conversation ID for continuing existing conversations
        :param conversation_name: Optional name for new conversation
        :return: MessageResponse object containing conversation ID, response, agent name,
            agent ID, and execution time

        Example:

        .. code-block:: python

            import asyncio
            from RPA.Sema4AI import Sema4AI

            async def main():
                client = Sema4AI()
                response = await client.ask_agent_async(
                    message="Hello!",
                    agent_api_key="your-api-key",
                    agent_api_endpoint="https://api.sema4.ai/v1",
                    agent_name="My Assistant"
                )
                print(f"Response: {response.response}")

            asyncio.run(main())
        """
        func = partial(
            self.ask_agent,
            message=message,
            agent_api_key=agent_api_key,
            agent_api_endpoint=agent_api_endpoint,
            agent_id=agent_id,
            agent_name=agent_name,
            conversation_id=conversation_id,
            conversation_name=conversation_name,
        )
        return await asyncio.to_thread(func)

    @log.suppress_variables()
    @timed_method
    async def get_conversations_async(
        self,
        agent_api_key: str,
        agent_api_endpoint: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> ConversationsResult:
        """Async version of get_conversations for non-blocking operations.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :return: ConversationsResult containing list of Conversation objects and execution time

        Example:

        .. code-block:: python

            import asyncio
            from RPA.Sema4AI import Sema4AI

            async def main():
                client = Sema4AI()
                result = await client.get_conversations_async(
                    agent_api_key="your-api-key",
                    agent_api_endpoint="https://api.sema4.ai/v1",
                    agent_name="My Assistant"
                )
                for conv in result:
                    print(f"Conversation: {conv.name}")

            asyncio.run(main())
        """
        func = partial(
            self.get_conversations,
            agent_api_key=agent_api_key,
            agent_api_endpoint=agent_api_endpoint,
            agent_id=agent_id,
            agent_name=agent_name,
        )
        return await asyncio.to_thread(func)

    @log.suppress_variables()
    @timed_method
    async def get_messages_async(
        self,
        agent_api_key: str,
        agent_api_endpoint: str,
        conversation_id: str,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> MessagesResult:
        """Async version of get_messages for non-blocking operations.

        :param agent_api_key: The API key for authentication
        :param agent_api_endpoint: The agent API endpoint URL
        :param conversation_id: The conversation ID
        :param agent_id: The agent ID (either agent_id or agent_name must be provided)
        :param agent_name: The agent name (either agent_id or agent_name must be provided)
        :return: MessagesResult containing list of message dictionaries and execution time

        Example:

        .. code-block:: python

            import asyncio
            from RPA.Sema4AI import Sema4AI

            async def main():
                client = Sema4AI()
                result = await client.get_messages_async(
                    agent_api_key="your-api-key",
                    agent_api_endpoint="https://api.sema4.ai/v1",
                    conversation_id="conv-123",
                    agent_name="My Assistant"
                )
                for msg in result:
                    print(f"{msg.get('role')}: {msg.get('content')}")

            asyncio.run(main())
        """
        func = partial(
            self.get_messages,
            agent_api_key=agent_api_key,
            agent_api_endpoint=agent_api_endpoint,
            conversation_id=conversation_id,
            agent_id=agent_id,
            agent_name=agent_name,
        )
        return await asyncio.to_thread(func)
