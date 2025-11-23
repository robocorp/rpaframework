rpaframework-sema4ai
====================

This library enables Sema4.ai Agent API integration for `RPA Framework`_
libraries, allowing you to communicate with AI agents in your automation workflows.

.. _RPA Framework: https://rpaframework.org

Installation
------------

.. code-block:: bash

    pip install rpaframework-sema4ai

Requirements
------------

- Python 3.10 or higher
- A Sema4.ai account with API access
- Agent API key and endpoint URL

Features
--------

- **Ask Agent**: Send messages to AI agents and receive responses
- **Conversation Management**: Create and continue conversations with agents
- **Message History**: Retrieve conversation history and messages
- **Async Support**: Non-blocking async methods for concurrent operations
- **Client Caching**: Efficient reuse of API clients across multiple requests

Usage Examples
--------------

Robot Framework
~~~~~~~~~~~~~~~

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
        Log    Conversation ID: ${response.conversation_id}

    Continue Conversation
        ${response}=    Ask Agent
        ...    message=What about tomorrow?
        ...    agent_api_key=${API_KEY}
        ...    agent_api_endpoint=${API_ENDPOINT}
        ...    agent_name=Weather Assistant
        ...    conversation_id=${PREV_CONVERSATION_ID}
        Log    Response: ${response.response}

    List Conversations
        ${conversations}=    Get Conversations
        ...    agent_api_key=${API_KEY}
        ...    agent_api_endpoint=${API_ENDPOINT}
        ...    agent_name=Weather Assistant
        FOR    ${conv}    IN    @{conversations}
            Log    ${conv.name} (ID: ${conv.conversation_id})
        END

Python
~~~~~~

.. code-block:: python

    from RPA.Sema4AI import Sema4AI

    client = Sema4AI()

    # Send a message to an agent
    response = client.ask_agent(
        message="What is the weather today?",
        agent_api_key="your-api-key",
        agent_api_endpoint="https://api.sema4.ai/v1",
        agent_name="Weather Assistant"
    )
    print(f"Response: {response.response}")
    print(f"Conversation ID: {response.conversation_id}")
    print(f"Execution time: {response.execution_time}s")

    # Continue the conversation
    followup = client.ask_agent(
        message="What about tomorrow?",
        agent_api_key="your-api-key",
        agent_api_endpoint="https://api.sema4.ai/v1",
        agent_name="Weather Assistant",
        conversation_id=response.conversation_id
    )
    print(f"Follow-up: {followup.response}")

    # Get all conversations for an agent
    conversations = client.get_conversations(
        agent_api_key="your-api-key",
        agent_api_endpoint="https://api.sema4.ai/v1",
        agent_name="Weather Assistant"
    )
    for conv in conversations:
        print(f"Conversation: {conv.name} (ID: {conv.conversation_id})")

    # Get messages in a conversation
    messages = client.get_messages(
        agent_api_key="your-api-key",
        agent_api_endpoint="https://api.sema4.ai/v1",
        conversation_id=response.conversation_id,
        agent_name="Weather Assistant"
    )
    for msg in messages:
        print(f"{msg.get('role')}: {msg.get('content')}")

Async Python
~~~~~~~~~~~~

For non-blocking operations in async contexts:

.. code-block:: python

    import asyncio
    from RPA.Sema4AI import Sema4AI

    async def main():
        client = Sema4AI()

        # Concurrent agent requests
        tasks = [
            client.ask_agent_async(
                message=f"Question {i}",
                agent_api_key="your-api-key",
                agent_api_endpoint="https://api.sema4.ai/v1",
                agent_name="My Assistant"
            )
            for i in range(3)
        ]
        responses = await asyncio.gather(*tasks)

        for i, response in enumerate(responses):
            print(f"Response {i}: {response.response}")

    asyncio.run(main())

API Reference
-------------

Sema4AI Class
~~~~~~~~~~~~~

**ask_agent(message, agent_api_key, agent_api_endpoint, agent_id=None, agent_name=None, conversation_id=None, conversation_name=None)**
    Send a message to an agent and receive a response.

    - ``message``: The message content to send
    - ``agent_api_key``: API key for authentication
    - ``agent_api_endpoint``: The agent API endpoint URL
    - ``agent_id``: Agent ID (use either agent_id or agent_name)
    - ``agent_name``: Agent name (use either agent_id or agent_name)
    - ``conversation_id``: Optional, for continuing existing conversations
    - ``conversation_name``: Optional, name for new conversations

    Returns: ``MessageResponse`` object with ``conversation_id``, ``response``, ``agent_name``, ``agent_id``, and ``execution_time``

**get_conversations(agent_api_key, agent_api_endpoint, agent_id=None, agent_name=None)**
    Get all conversations for an agent.

    Returns: ``ConversationsResult`` containing list of ``Conversation`` objects

**get_messages(agent_api_key, agent_api_endpoint, conversation_id, agent_id=None, agent_name=None)**
    Get all messages in a conversation.

    Returns: ``MessagesResult`` containing list of message dictionaries

**Async variants**: ``ask_agent_async``, ``get_conversations_async``, ``get_messages_async``

Response Objects
~~~~~~~~~~~~~~~~

**MessageResponse**
    - ``conversation_id``: ID of the conversation
    - ``response``: Text response from the agent
    - ``agent_name``: Name of the responding agent
    - ``agent_id``: ID of the responding agent
    - ``execution_time``: Time taken in seconds

**ConversationsResult**
    - ``conversations``: List of Conversation objects
    - ``execution_time``: Time taken in seconds
    - Supports iteration and indexing

**MessagesResult**
    - ``messages``: List of message dictionaries
    - ``execution_time``: Time taken in seconds
    - Supports iteration and indexing

**Conversation**
    - ``conversation_id``: Unique conversation identifier
    - ``name``: Conversation name
    - ``agent_id``: ID of the associated agent

Error Handling
--------------

.. code-block:: python

    from RPA.Sema4AI import Sema4AI, Sema4aiException

    client = Sema4AI()

    try:
        response = client.ask_agent(
            message="Hello",
            agent_api_key="your-api-key",
            agent_api_endpoint="https://api.sema4.ai/v1",
            agent_name="NonExistent Agent"
        )
    except Sema4aiException as e:
        print(f"Error: {e}")
        if e.status_code:
            print(f"HTTP Status: {e.status_code}")
    except ValueError as e:
        print(f"Validation error: {e}")

Configuration
-------------

The library supports multiple URL formats for the API endpoint:

- Direct API URL: ``https://api.sema4.ai/v1``
- Tenant URL: ``https://ace-xxxxx.prod-demo.sema4ai.work/tenants/GUID``
- Base URL: ``https://ace-xxxxx.prod-demo.sema4ai.work``

All formats are automatically normalized to the correct API endpoint.

License
-------

Apache License 2.0
