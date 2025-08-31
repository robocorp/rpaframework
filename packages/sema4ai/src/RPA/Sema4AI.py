import json
import logging
import os
import platform
from copy import copy
from typing import Optional, List
from urllib.parse import urljoin, urlparse

try:
    import sema4ai_http
except ImportError:
    sema4ai_http = None


class Agent:
    """Represents a Sema4ai agent."""

    def __init__(self, id: str, name: str, description: Optional[str] = None, mode: Optional[str] = None):
        self.id = id
        self.name = name
        self.description = description
        self.mode = mode


class Conversation:
    """Represents a Sema4ai conversation."""

    def __init__(self, id: str, name: str, agent_id: str):
        self.id = id
        self.name = name
        self.agent_id = agent_id


class MessageResponse:
    """Represents a message response from an agent."""

    def __init__(self, conversation_id: str, response: str, agent_name: str, agent_id: str):
        self.conversation_id = conversation_id
        self.response = response
        self.agent_name = agent_name
        self.agent_id = agent_id


class Sema4aiException(Exception):
    """Exception raised when the Sema4ai client encounters an error."""
    pass


class _AgentAPIClient:
    """Internal API client for Sema4ai agents."""

    PID_FILE_NAME = "agent-server.pid"

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """Initialize the AgentServerClient."""
        if sema4ai_http is None:
            raise ImportError("sema4ai-actions package is required for Sema4ai functionality")

        self.api_key = api_key if api_key != "LOCAL" else None

        # Use provided URL or discover it
        if api_url:
            self.api_url = self._normalize_api_url(api_url)
            self.is_v2 = "v2" in self.api_url
        else:
            self.api_url = self._get_api_url()
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

    def _get_api_url(self) -> str:
        """Determine the correct API URL by checking environment variable or agent-server.pid file."""
        # Try to get URL from environment variable first
        api_url = self._try_get_url_from_environment()
        if api_url:
            return api_url

        # Try to get URL from PID file as fallback
        api_url = self._try_get_url_from_pid_file()
        if api_url:
            return api_url

        # No working API server found
        raise Sema4aiException("Could not connect to agent server")

    def _try_get_url_from_environment(self) -> Optional[str]:
        env_url = os.getenv("SEMA4AI_API_V1_URL")
        if not env_url:
            return None
        return self._test_api_endpoints(env_url)

    def _try_get_url_from_pid_file(self) -> Optional[str]:
        pid_file_path = self._get_pid_file_path()
        try:
            if not os.path.exists(pid_file_path):
                return None

            with open(pid_file_path, "r") as f:
                server_info = json.loads(f.read())
                base_url = server_info.get("base_url")
                if base_url:
                    for version in ["v1", "v2"]:
                        endpoint_url = f"{base_url}/api/public/{version}"
                        result = self._test_api_endpoints(endpoint_url)
                        if result:
                            return result
                return None
        except Exception:
            return None

    def _test_api_endpoints(self, base_url: str) -> Optional[str]:
        """Test different API endpoint versions to find a working one."""
        test_endpoint = f"{base_url}/agents"
        if "v2" in base_url:
            test_endpoint += "/"

        if self._is_url_accessible(test_endpoint):
            return base_url
        return None

    def _is_url_accessible(self, url: str) -> bool:
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in ("http", "https"):
                return False

            headers = (
                {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
            )
            sema4ai_http.get(url, headers=headers, timeout=1).raise_for_status()
            return True
        except Exception:
            return False

    def _get_pid_file_path(self) -> str:
        """Get the path to the agent-server.pid file based on the operating system."""
        if platform.system() == "Windows":
            local_app_data = os.environ.get("LOCALAPPDATA")
            if not local_app_data:
                local_app_data = os.path.join(
                    os.path.expanduser("~"), "AppData", "Local"
                )
            return os.path.join(
                local_app_data,
                "sema4ai",
                "sema4ai-studio",
                self.PID_FILE_NAME,
            )
        else:
            return os.path.join(
                os.path.expanduser("~"),
                ".sema4ai",
                "sema4ai-studio",
                self.PID_FILE_NAME,
            )

    def request(self, path: str, method: str = "GET", json_data: Optional[dict] = None,
                headers: Optional[dict] = None):
        """Make an API request with common error handling."""
        url = self.api_url
        if not url.endswith("/"):
            url += "/"
        url = urljoin(url, path)

        parsed_url = urlparse(self.api_url)
        if self.is_v2 and parsed_url.scheme == "http" and not url.endswith("/"):
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
            raise Sema4aiException(error_msg)

        return response

    def get_all_agents(self) -> List[Agent]:
        """Get all available agents."""
        response = self.request("agents")
        agents_data = response.json()

        # Handle paginated response
        if isinstance(agents_data, dict) and "data" in agents_data:
            agents_data = agents_data["data"]

        return [Agent(
            id=agent["id"],
            name=agent["name"],
            description=agent.get("description"),
            mode=agent.get("mode")
        ) for agent in agents_data]

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get an agent by name."""
        agents = self.get_all_agents()
        return next((agent for agent in agents if agent.name == name), None)

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
            id=conv_data["id"],
            name=conv_data["name"],
            agent_id=agent_id
        )

    def send_message(self, conversation_id: str, agent_id: str, message: str) -> str:
        """Send a message to an agent and get the response."""
        endpoint = f"agents/{agent_id}/conversations/{conversation_id}/messages"
        response = self.request(
            endpoint,
            method="POST",
            json_data={"content": message}
        )

        response_json = response.json()

        # Handle different response formats
        messages = []
        if isinstance(response_json, dict):
            if "data" in response_json:
                messages = response_json["data"]
            elif "messages" in response_json:
                messages = response_json["messages"]
            elif "content" in response_json:
                return response_json.get("content", "")
        elif isinstance(response_json, list):
            messages = response_json

        if messages:
            for msg in reversed(messages):
                if msg.get("role") == "agent":
                    return msg.get("content", "")

            # If no agent message found, return the last message content
            if isinstance(messages[-1], dict) and "content" in messages[-1]:
                return messages[-1]["content"]

            raise Sema4aiException("No agent response found in conversation messages")

        return str(response_json)


class Sema4AI:
    """Library to support `Sema4ai <https://sema4.ai>`_ services.

    Library is **not** included in the `rpaframework` package, so in order to use it
    you have to add `rpaframework-sema4ai` with the desired version in your
    *conda.yaml* file.

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Sema4AI

        *** Tasks ***
        Ask Agent Simple
            ${response}    Ask Agent    My Agent    Hello, what can you do?    LOCAL
            Log    ${response}

        Ask Agent With ID
            ${response}    Ask Agent    agent_name=My Agent    message=Hello!    api_key=LOCAL    agent_id=agent_123
            Log    ${response}

    **Python example usage**

    .. code-block:: python

        from RPA.Sema4AI import Sema4AI

        sema4ai = Sema4AI()
        response = sema4ai.ask_agent(
            agent_name="My Agent",
            message="Hello, what can you do?",
            api_key="LOCAL"
        )
        print(response.response)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._client = None

    def ask_agent(
        self,
        message: str,
        api_key: str,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_api_endpoint: Optional[str] = None,
        conversation_id: Optional[str] = None,
        conversation_name: Optional[str] = None
    ) -> MessageResponse:
        """Ask an agent a question and get a response.

        This is the primary method for interacting with Sema4ai agents. You can either
        let the library find the agent by name or bypass the search by providing the agent_id
        and agent_api_endpoint.

        :param message: The message content to send
        :param api_key: The API key for the Sema4 API. Use "LOCAL" if in Studio or SDK
        :param agent_name: The name of the agent (required if agent_id not provided)
        :param agent_id: Optional agent ID to bypass agent name lookup
        :param agent_api_endpoint: Optional agent API endpoint URL (required if agent_id is provided).
            Supports multiple formats:
            - Direct API: https://api.sema4.ai/v1
            - Tenant URL: https://your-tenant.sema4ai.work/tenants/tenant-id
            - Base domain: https://your-tenant.sema4ai.work
        :param conversation_id: Optional conversation ID for continuing existing conversations
        :param conversation_name: Optional name for new conversation (used if conversation_id not provided)
        :return: MessageResponse object containing conversation ID, response, agent name, and agent ID

        Robot Framework example:

        .. code-block:: robotframework

            # Simple usage - find agent by name
            ${response}    Ask Agent    Hello!    LOCAL    agent_name=My Agent
            Log    Response: ${response.response}
            Log    Conversation ID: ${response.conversation_id}

            # Bypass agent lookup with agent_id and endpoint (cloud/tenant)
            ${response}    Ask Agent    Hello!    your_api_key
            ...    agent_id=agent_123
            ...    agent_api_endpoint=https://your-tenant.sema4ai.work/tenants/tenant-id

            # Continue existing conversation
            ${response}    Ask Agent    How are you?    LOCAL
            ...    agent_name=My Agent    conversation_id=${response.conversation_id}

        Python example:

        .. code-block:: python

            sema4ai = Sema4ai()

            # Simple usage
            response = sema4ai.ask_agent("Hello!", "LOCAL", agent_name="My Agent")
            print(f"Response: {response.response}")

            # Bypass agent lookup (cloud/tenant)
            response = sema4ai.ask_agent(
                "Hello!", "your_api_key",
                agent_id="agent_123",
                agent_api_endpoint="https://your-tenant.sema4ai.work/tenants/tenant-id"
            )

            # Continue conversation
            response = sema4ai.ask_agent(
                "How are you?", "LOCAL",
                agent_name="My Agent",
                conversation_id=response.conversation_id
            )
        """
        # Validate parameters
        if agent_id and not agent_api_endpoint:
            raise Sema4aiException("agent_api_endpoint is required when agent_id is provided")
        if agent_api_endpoint and not agent_id:
            raise Sema4aiException("agent_id is required when agent_api_endpoint is provided")
        if not agent_id and not agent_name:
            raise Sema4aiException("Either agent_name or agent_id (with agent_api_endpoint) must be provided")

        # If agent_id and endpoint are provided, use a custom client
        if agent_id and agent_api_endpoint:
            self.logger.info(f"Using provided agent_id: {agent_id} with endpoint: {agent_api_endpoint}")
            client = _AgentAPIClient(api_key=api_key, api_url=agent_api_endpoint)
            # Use agent_name if provided, otherwise use agent_id as fallback name
            display_name = agent_name if agent_name else agent_id
            agent = Agent(id=agent_id, name=display_name)
        else:
            # Use standard client and find the agent by name
            self.logger.info(f"Looking up agent by name: {agent_name}")
            client = _AgentAPIClient(api_key=api_key)
            agent = client.get_agent_by_name(agent_name)
            if not agent:
                # Get available agents for error message
                all_agents = client.get_all_agents()
                available_names = [a.name for a in all_agents]
                raise Sema4aiException(
                    f"Agent '{agent_name}' not found. Available agents: {', '.join(available_names)}"
                )

        # Create conversation if needed
        if not conversation_id:
            if not conversation_name:
                conversation_name = f"Conversation with {agent.name}"

            conversation = client.create_conversation(
                agent_id=agent.id,
                conversation_name=conversation_name
            )
            conversation_id = conversation.id

        # Send the message
        response_text = client.send_message(
            conversation_id=conversation_id,
            agent_id=agent.id,
            message=message
        )

        result = MessageResponse(
            conversation_id=conversation_id,
            response=response_text,
            agent_name=agent.name,
            agent_id=agent.id
        )

        self.logger.info(f"Agent response received: {response_text[:100]}...")
        return result