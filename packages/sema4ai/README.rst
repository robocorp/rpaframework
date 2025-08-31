###############
RPA.Sema4ai
###############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Sema4ai`_ is a platform for building and deploying AI actions and workflows.

The **rpaframework-sema4ai** package provides a Python library for integrating
with Sema4ai agents in your Robot Framework automation projects. This library
allows you to communicate with Sema4ai agents directly from your automation scripts.

.. _Sema4ai: https://sema4.ai

************
Installation
************

The recommended installation method is `uv`_:

.. code-block:: bash

    uv add rpaframework-sema4ai

After installation the library can be directly imported inside
`Robot Framework`_:

.. code-block:: robotframework

    *** Settings ***
    Library    RPA.Sema4ai

.. _uv: https://github.com/astral-sh/uv
.. _Robot Framework: https://robotframework.org

***************
Example usage
***************

Robot Framework
===============

.. code-block:: robotframework

    *** Settings ***
    Library    RPA.Sema4ai

    *** Tasks ***
    Ask Agent Simple
        ${response}    Ask Agent    Hello, what can you do?    LOCAL    agent_name=My Agent
        Log    Agent said: ${response.response}
        Log    Conversation ID: ${response.conversation_id}

    Ask Agent With Agent ID Bypass (Cloud)
        # If you know the agent ID and endpoint, you can bypass the name lookup
        ${response}    Ask Agent    Hello!    your_api_key    
        ...    agent_id=agent_123    
        ...    agent_api_endpoint=https://your-tenant.sema4ai.work/tenants/tenant-id
        Log    ${response.response}

    Continue Conversation
        # First message
        ${response1}    Ask Agent    What's the weather like?    LOCAL    agent_name=My Agent
        
        # Continue the same conversation
        ${response2}    Ask Agent    What about tomorrow?    LOCAL    
        ...    agent_name=My Agent    
        ...    conversation_id=${response1.conversation_id}
        Log    ${response2.response}

Python
======

.. code-block:: python

    from RPA.Sema4ai import Sema4ai

    # Initialize the library
    sema4ai = Sema4ai()

    # Simple usage - find agent by name
    response = sema4ai.ask_agent(
        message="Hello, what can you do?",
        api_key="LOCAL",  # Use "LOCAL" for Sema4ai Studio/SDK
        agent_name="My Agent"
    )
    print(f"Agent response: {response.response}")
    print(f"Conversation ID: {response.conversation_id}")

    # Bypass agent lookup with agent_id and endpoint (cloud/tenant)
    response = sema4ai.ask_agent(
        message="Hello!",
        api_key="your_api_key",
        agent_id="agent_123",  # Skip name-to-ID lookup
        agent_api_endpoint="https://your-tenant.sema4ai.work/tenants/tenant-id"
    )

    # Continue existing conversation
    response2 = sema4ai.ask_agent(
        message="How are you?",
        api_key="LOCAL",
        agent_name="My Agent",
        conversation_id=response.conversation_id
    )

********************
Authentication
********************

The library supports two authentication modes:

Local Development (Sema4ai Studio/SDK)
=======================================

When running in Sema4ai Studio or with the Sema4ai SDK, use ``"LOCAL"`` as the API key:

.. code-block:: python

    response = sema4ai.ask_agent("Hello", "LOCAL", agent_name="My Agent")

Cloud Deployment
================

When deploying to the cloud or connecting to Sema4ai Enterprise, you need to provide your API key and potentially the endpoint URL.

Getting Your API Key
---------------------

1. Log into your Sema4ai Control Room
2. Navigate to your Workspace
3. Click the "API Keys" tab
4. Create a new API key
5. Copy the generated Bearer Token

Basic Cloud Usage
-----------------

For basic cloud usage with agent name lookup:

.. code-block:: python

    response = sema4ai.ask_agent("Hello", "your-api-key-here", agent_name="My Agent")

Enterprise/Tenant Setup
-----------------------

For Sema4ai Enterprise with tenant-specific URLs, you have two options:

**Option 1: Using Agent Name (requires endpoint discovery)**

.. code-block:: python

    # This works if your environment provides the endpoint automatically
    response = sema4ai.ask_agent("Hello", "your-api-key", agent_name="My Agent")

**Option 2: Using Direct Agent ID (recommended for tenant environments)**

.. code-block:: python

    # Direct agent access with tenant URL
    response = sema4ai.ask_agent(
        "Hello", 
        "your-api-key",
        agent_id="agent_123",
        agent_api_endpoint="https://your-tenant.sema4ai.work/tenants/tenant-id"
    )

Supported Endpoint Formats
---------------------------

The library automatically normalizes different endpoint URL formats:

.. code-block:: python

    # All of these work and are converted to the proper API format
    
    # 1. Tenant URL (most common for Enterprise) - gets normalized to include /api/v1
    endpoint = "https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0"
    # Becomes: https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0/api/v1
    
    # 2. Base domain
    endpoint = "https://ace-fe1cd46f.prod-demo.sema4ai.work"
    # Becomes: https://ace-fe1cd46f.prod-demo.sema4ai.work/api/v1
    
    # 3. Direct API URL (no changes)
    endpoint = "https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/tenant-id/api/v1"

Troubleshooting
---------------

**HTTP 404 Error**: This usually means one of the following:

1. **Missing agent_api_endpoint parameter** when using agent_id:
   
   .. code-block:: python
   
       # Wrong - will use local endpoint discovery
       response = sema4ai.ask_agent("Hello", "api_key", agent_id="agent_123")
       
       # Correct - provide the endpoint
       response = sema4ai.ask_agent(
           "Hello", "api_key", 
           agent_id="agent_123",
           agent_api_endpoint="https://your-tenant.sema4ai.work/tenants/tenant-id"
       )

2. **Incorrect endpoint URL format** - make sure you're using the complete tenant URL from your Control Room

3. **Agent ID doesn't exist** at the specified endpoint

4. **Incorrect API key** or insufficient permissions

********************
Performance Tips
********************

Agent ID Bypass
================

If you know the agent ID and endpoint (which you can get from the first call's response), 
you can bypass the agent name lookup for better performance in subsequent calls:

.. code-block:: python

    # First call - discovers agent ID (local environment)
    response = sema4ai.ask_agent("Hello", "LOCAL", agent_name="My Agent")
    agent_id = response.agent_id  # Save this for future use
    
    # For cloud/tenant environments, you need the endpoint URL
    # Subsequent calls - bypass lookup for better performance
    response = sema4ai.ask_agent(
        "Another message", "your-api-key", 
        agent_id=agent_id,
        agent_api_endpoint="https://your-tenant.sema4ai.work/tenants/tenant-id"
    )

Conversation Management
=======================

Reuse conversation IDs to maintain context across multiple messages:

.. code-block:: python

    # Start conversation
    response1 = sema4ai.ask_agent("What's 2+2?", "LOCAL", agent_name="My Agent")
    
    # Continue conversation with context
    response2 = sema4ai.ask_agent(
        "What about if we multiply that by 3?", 
        "LOCAL",
        agent_name="My Agent",
        conversation_id=response1.conversation_id
    )

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Sema4ai.rst