import logging
from typing import Optional
from robot.api.deco import keyword
import openai


class OpenAI:
    """Library to support `OpenAI <https://openai.com>`_ service.

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocorp.Vault
        Library    RPA.OpenAI

        *** Tasks ***
        Create a text completion
            ${secrets}   Get Secret   secret_name=OpenAI
            Authorize To OpenAI   api_key=${secrets}[key]
            ${completion}    Completion Create
            ...     Write a tagline for an ice cream shop
            ...     temperature=0.6
            Log   ${completion}

    **Python example usage**

    .. code-block:: python

        from RPA.Robocorp.Vault import Vault
        from RPA.OpenAI import OpenAI

        secrets = Vault().get_secret("OpenAI")
        baselib = OpenAI()
        baselib.authorize_to_openai(secrets["key"])

        result = baselib.completion_create(
            Create a tagline for icecream shop',
            temperature=0.6,
        )
        print(result)
    """

    ROBOT_LIBRARY_SCOPE = "Global"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    @keyword
    def authorize_to_openai(self, api_key: str) -> None:
        """Keyword for authorize to OpenAI with your API key obtained from your account.

        :param api_key: Your OpenAI API key

        Robot Framework example:

        .. code-block:: robotframework

            ${secrets}   Get Secret   secret_name=OpenAI
            Authorize To OpenAI   api_key=${secrets}[key]

        Python example:

        .. code-block:: python

            secrets = Vault().get_secret("OpenAI")
            baselib = OpenAI()
            baselib.authorize_to_openai(secrets["key"])

        """
        openai.api_key = api_key

    @keyword
    def completion_create(
        self,
        prompt: str,
        model: Optional[str] = "text-davinci-003",
        temperature: Optional[int] = 0.7,
        max_tokens: Optional[int] = 256,
        top_probability: Optional[int] = 1,
        frequency_penalty: Optional[int] = 0,
        presence_penalty: Optional[int] = 0,
        result_format: Optional[str] = "string",
    ) -> None:
        """Keyword for creating text completions in OpenAI.
        Keyword returns a text string.

        :param prompt: Text submitted to OpenAI for creating natural language.
        :param model: OpenAI's model to use in the completion.
        :param temperature: What sampling temperature to use.
        Higher values means the model will take more risks..
        :param max_tokens: The maximum number of tokens to generate in the completion..
        :param top_probability: Controls diversity via nucleus sampling. 0.5 means half
        of all likelihood-weighted options are considered.
        :param frequency_penalty: Number between -2.0 and 2.0. Positive values penalize
        new tokens based on their existing frequency in the text so far.
        :param presence_penalty: Number between -2.0 and 2.0. Positive values penalize
        new tokens based on whether they appear in the text so far.
        :param result_format: Result format (string / json). Return just a string or
        the default JSON response.

        Robot Framework example:

        .. code-block:: robotframework

            ${response}  Completion Create
            ...     Write a tagline for an icecream shop.
            ...     temperature=0.6
            Log     ${response}

        Python example:

        .. code-block:: python

            result = baselib.completion_create(
                'Create a tagline for icecream shop',
                temperature=0.6,
            )
            print(result)

        """
        response = openai.Completion.create(
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_probability,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
        self.logger.info(response)
        if result_format == "string":
            text = response["choices"][0]["text"].strip()
            return text
        if result_format == "json":
            return response
        else:
            return None

    @keyword
    def image_create(
        self,
        prompt: str,
        size: Optional[str] = "512x512",
        num_images: Optional[int] = 1,
        result_format: Optional[str] = "list",
    ) -> None:
        """Keyword for creating one or more images in OpenAI.
        Keyword returns a list of urls for the images created.

        :param prompt: A text description of the desired image(s).
        The maximum length is 1000 characters.
        :param size: Size of the files to be created. 256x256, 512x512, 1024x1024
        :param num_images: The number of images to generate. Must be between 1 and 10.
        :param result_format: Result format (list / json).

        Robot Framework example:

        .. code-block:: robotframework

            ${images}    Image Create
            ...   Cartoon style picture of a cute monkey skateboarding.
            ...   size=256x256
            ...   num_images=2
            FOR    ${url}    IN    @{images}
                Log    ${url}
            END

        Python example:

        .. code-block:: python

            images = baselib.image_create(
                'Cartoon style picture of a cute monkey skateboarding',
                size='256x256',
                num_images=2,
            )
            for url in images:
                print(url)

        """
        response = openai.Image.create(prompt=prompt, size=size, n=num_images)
        self.logger.info(response)
        urls = []
        if result_format == "list":
            for _url in response["data"]:
                urls.append(_url["url"])
                self.logger.info(_url)
            return urls
        if result_format == "json":
            return response
        else:
            return None

    @keyword
    def image_create_variation(
        self,
        src_image: str,
        size: Optional[str] = "512x512",
        num_images: Optional[int] = 1,
        result_format: Optional[str] = "list",
    ) -> None:
        """Keyword for creating one or more variations of a image. Keyword
        returns a list of urls for the images created.
        Source file must be a valid PNG file, less than 4MB, and square.

        :param src_image: The image to use as the basis for the variation(s).
        Must be a valid PNG file, less than 4MB, and square.
        :param size: The size of the generated images.
        Must be one of 256x256, 512x512, or 1024x1024.
        :param num_images: The number of images to generate. Must be between 1 and 10
        :param result_format: Result format (list / json).

        Robot Framework example:

        .. code-block:: robotframework

            ${variations}   Image Create Variation
            ...     source_image.png
            ...     size=256x256
            ...     num_images=2
            FOR    ${url}    IN    @{variations}
                Log    ${url}
            END

        Python example:

        .. code-block:: python

            variations = baselib.image_create_variation(
                'source_image.png',
                size='256x256',
                num_images=2,
            )
            for url in variations:
                print(url)

        """
        with open(src_image, "rb") as image_file:
            response = openai.Image.create_variation(
                image=image_file, n=num_images, size=size
            )
        self.logger.info(response)

        urls = []
        if result_format == "list":
            for _url in response["data"]:
                urls.append(_url["url"])
                self.logger.info(_url)
            return urls
        if result_format == "json":
            return response
        else:
            return None
