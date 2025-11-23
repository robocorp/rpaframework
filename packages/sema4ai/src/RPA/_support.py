"""Internal support classes and utilities for the Sema4AI library."""

import time
import functools
from copy import copy
from typing import Optional, List
from urllib.parse import urljoin
from pydantic import BaseModel, Field

try:
    import sema4ai_http
except ImportError:
    sema4ai_http = None


class Agent(BaseModel):
    """Represents a Sema4ai agent."""
    agent_id: str = Field(description="The unique identifier of the agent")
    agent_name: str = Field(description="The name of the agent")
    description: Optional[str] = Field(default=None, description="Description of the agent")
    mode: Optional[str] = Field(default=None, description="The mode of the agent")

    def __dir__(self):
        """Custom dir() to only show relevant fields and methods."""
        return [
            'agent_id',
            'agent_name',
            'description',
            'mode',
            'dict',
            'json',
            'model_dump',
            'model_dump_json'
        ]


class Conversation(BaseModel):
    """Represents a Sema4ai conversation."""
    conversation_id: str = Field(description="The unique identifier of the conversation")
    name: str = Field(description="The name of the conversation")
    agent_id: str = Field(description="The ID of the agent this conversation belongs to")

    def __dir__(self):
        """Custom dir() to only show relevant fields and methods."""
        return [
            'conversation_id',
            'name',
            'agent_id',
            'dict',
            'json',
            'model_dump',
            'model_dump_json'
        ]


class MessageResponse(BaseModel):
    """Represents a message response from an agent."""
    conversation_id: str = Field(description="The ID of the conversation this response belongs to")
    response: str = Field(description="The response text from the agent")
    agent_name: str = Field(description="The name of the agent that provided the response")
    agent_id: str = Field(description="The ID of the agent that provided the response")
    execution_time: float = Field(description="Execution time in seconds, rounded to 3 decimal places")

    def __dir__(self):
        """Custom dir() to only show relevant fields and methods."""
        return [
            'conversation_id',
            'response',
            'agent_name',
            'agent_id',
            'execution_time',
            'dict',
            'json',
            'model_dump',
            'model_dump_json'
        ]


class TimedResult(BaseModel):
    """Base class for results that include execution time."""
    execution_time: float = Field(description="Execution time in seconds, rounded to 3 decimal places")

    def __dir__(self):
        """Custom dir() to only show relevant fields and methods."""
        return [
            'execution_time',
            'dict',
            'json',
            'model_dump',
            'model_dump_json'
        ]


class ConversationsResult(TimedResult):
    """Result container for get_conversations with execution time."""
    conversations: List[Conversation] = Field(description="List of conversations")

    def __dir__(self):
        """Custom dir() to only show relevant fields and methods."""
        return [
            'conversations',
            'execution_time',
            'dict',
            'json',
            'model_dump',
            'model_dump_json'
        ]

    def __iter__(self):
        """Allow iteration over conversations."""
        return iter(self.conversations)

    def __len__(self):
        """Allow len() on conversations."""
        return len(self.conversations)

    def __getitem__(self, index):
        """Allow indexing into conversations."""
        return self.conversations[index]


class MessagesResult(TimedResult):
    """Result container for get_messages with execution time."""
    messages: List[dict] = Field(description="List of message dictionaries")

    def __dir__(self):
        """Custom dir() to only show relevant fields and methods."""
        return [
            'messages',
            'execution_time',
            'dict',
            'json',
            'model_dump',
            'model_dump_json'
        ]

    def __iter__(self):
        """Allow iteration over messages."""
        return iter(self.messages)

    def __len__(self):
        """Allow len() on messages."""
        return len(self.messages)

    def __getitem__(self, index):
        """Allow indexing into messages."""
        return self.messages[index]


def timed_method(func):
    """Decorator to add execution timing to methods."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = round(time.time() - start_time, 3)

        # If the result already has execution_time (like MessageResponse), use it as-is
        if hasattr(result, 'execution_time'):
            return result

        # For other results, we need to wrap them based on type
        if isinstance(result, list):
            # Check if it's a list of Conversation objects or dict objects
            if result and isinstance(result[0], Conversation):
                return ConversationsResult(conversations=result, execution_time=execution_time)
            return MessagesResult(messages=result, execution_time=execution_time)

        # For other types, just add execution_time attribute
        if hasattr(result, '__dict__'):
            result.execution_time = execution_time

        return result

    return wrapper


class Sema4aiException(Exception):
    """Exception raised when the Sema4ai client encounters an error.

    Attributes:
        status_code: HTTP status code if the error was from an HTTP response.
    """

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class _AgentAPIClient:
    """Internal API client for Sema4ai agents."""

    def __init__(self, agent_api_key: Optional[str] = None, api_url: str = None):
        """Initialize the AgentServerClient."""
        if sema4ai_http is None:
            raise ImportError("sema4ai-actions package is required for Sema4ai functionality")

        if not api_url:
            raise ValueError("api_url is required")

        self.api_key = agent_api_key if agent_api_key != "LOCAL" else None
        self.api_url = self._normalize_api_url(api_url)
        self.is_v2 = "v2" in self.api_url

    def _normalize_api_url(self, url: str) -> str:
        """Normalize different URL formats to the standard API base URL.

        Handles:
        - Direct API URLs: https://api.sema4.ai/v1 -> https://api.sema4.ai/v1
        - Tenant URLs: https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0
          -> https://ace-fe1cd46f.prod-demo.sema4ai.work/tenants/338745d3-001b-415e-aade-34713cf88fb0/api/v1
        - Base URLs: https://ace-fe1cd46f.prod-demo.sema4ai.work -> https://ace-fe1cd46f.prod-demo.sema4ai.work/api/v1
        """
        url = url.rstrip('/')

        # If it's already an API URL, return as-is
        if '/api/v' in url:
            return url

        # If it contains /tenants/, keep the full tenant path and add API path
        if '/tenants/' in url:
            # Keep the full tenant URL and add API path
            return f"{url}/api/v1"

        # If it's just a base domain, add the API path
        return f"{url}/api/v1"

    def request(self, path: str, method: str = "GET", json_data: Optional[dict] = None,
                headers: Optional[dict] = None):
        """Make an API request with common error handling."""
        url = self.api_url
        if not url.endswith("/"):
            url += "/"
        url = urljoin(url, path)

        if self.is_v2 and not url.endswith("/"):
            url += "/"

        request_headers = copy(headers) if headers else {}

        if self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"

        if method == "GET":
            response = sema4ai_http.get(url, json=json_data, headers=request_headers)
        elif method == "POST":
            response = sema4ai_http.post(url, json=json_data, headers=request_headers)
        elif method == "DELETE":
            response = sema4ai_http.delete(url, headers=request_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code not in (200, 201):
            error_msg = f"HTTP {response.status_code}"
            if response.text:
                error_msg += f": {response.text}"
            else:
                error_msg += f": {response.reason or 'Unknown error'}"
            # Add URL information for debugging
            error_msg += f" (URL: {url})"
            raise Sema4aiException(error_msg, status_code=response.status_code)

        return response

    def get_all_agents(self) -> List[Agent]:
        """Get all available agents."""
        response = self.request("agents")
        agents_data = response.json()

        # Handle paginated response
        if isinstance(agents_data, dict) and "data" in agents_data:
            agents_data = agents_data["data"]

        return [Agent(
            agent_id=agent["id"],
            agent_name=agent["name"],
            description=agent.get("description"),
            mode=agent.get("mode")
        ) for agent in agents_data]

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get an agent by name."""
        agents = self.get_all_agents()
        return next((agent for agent in agents if agent.agent_name == name), None)

    def create_conversation(self, agent_id: str, conversation_name: str) -> Conversation:
        """Create a new conversation."""
        endpoint = f"agents/{agent_id}/conversations"
        response = self.request(
            endpoint,
            method="POST",
            json_data={"name": conversation_name}
        )
        conv_data = response.json()
        return Conversation(
            conversation_id=conv_data["id"],
            name=conv_data["name"],
            agent_id=agent_id
        )

    def _extract_response_content(self, response_json) -> str:
        """Extract content string from various API response formats.

        Args:
            response_json: The JSON response from the API

        Returns:
            str: The extracted content string

        Raises:
            Sema4aiException: If no valid content is found
        """
        # Handle direct content in dict
        if isinstance(response_json, dict) and "content" in response_json:
            return str(response_json.get("content", ""))

        # Extract messages from different wrapper formats
        messages = self._extract_messages_from_response(response_json)

        if messages:
            # Try to find content in messages
            content = self._find_content_in_messages(messages)
            if content is not None:
                return str(content)

            raise Sema4aiException("No valid response content found in messages")

        # Final fallbacks for edge cases
        if isinstance(response_json, list) and len(response_json) > 0:
            return str(response_json[0])

        return str(response_json) if response_json else ""

    def _extract_messages_from_response(self, response_json) -> list:
        """Extract messages list from different response wrapper formats."""
        if isinstance(response_json, dict):
            if "data" in response_json:
                return response_json["data"]
            if "messages" in response_json:
                return response_json["messages"]
        if isinstance(response_json, list):
            return response_json

        return []

    def _find_content_in_messages(self, messages: list) -> Optional[str]:
        """Find and extract content from messages list.

        Tries multiple strategies:
        1. Look for agent role messages with content
        2. Look for any message with content field
        3. Fallback to string conversion of first message
        """
        if not messages:
            return None

        # Strategy 1: Look for agent role messages first
        for msg in reversed(messages):
            if (isinstance(msg, dict) and
                msg.get("role") == "agent" and
                "content" in msg):
                return msg.get("content", "")

        # Strategy 2: Look for any message with content field
        for msg in reversed(messages):
            if isinstance(msg, dict) and "content" in msg:
                return msg.get("content", "")

        # Strategy 3: Convert first message to string as fallback
        if len(messages) > 0:
            return str(messages[0])

        return None

    def send_message(self, conversation_id: str, agent_id: str, message: str) -> str:
        """Send a message to an agent and get the response."""
        endpoint = f"agents/{agent_id}/conversations/{conversation_id}/messages"
        response = self.request(
            endpoint,
            method="POST",
            json_data={"content": message}
        )

        response_json = response.json()
        return self._extract_response_content(response_json)

    def get_conversations(self, agent_id: str) -> List[Conversation]:
        """Get all conversations for an agent."""
        endpoint = f"agents/{agent_id}/conversations"
        response = self.request(endpoint)
        conversations_data = response.json()

        # Handle paginated response
        if isinstance(conversations_data, dict) and "data" in conversations_data:
            conversations_data = conversations_data["data"]

        return [Conversation(
            conversation_id=conv["id"],
            name=conv["name"],
            agent_id=agent_id
        ) for conv in conversations_data]

    def get_messages(self, agent_id: str, conversation_id: str) -> List[dict]:
        """Get all messages in a conversation."""
        endpoint = f"agents/{agent_id}/conversations/{conversation_id}/messages"
        response = self.request(endpoint)
        messages_data = response.json()

        # Handle paginated response
        if isinstance(messages_data, dict) and "data" in messages_data:
            messages_data = messages_data["data"]

        return messages_data
