from typing import Optional

from . import (
    LibraryContext,
    keyword,
)


class AppsScriptKeywords(LibraryContext):
    """Class for Google Apps Script API

    For more information about Google Apps Script API link_.

    .. _link: https://developers.google.com/apps-script/api
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "apps script"])
    def init_apps_script(
        self,
        service_account: str = None,
        credentials: str = None,
        use_robocorp_vault: Optional[bool] = None,
        scopes: list = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Apps Script client

        :param service_account: file path to service account file
        :param credentials: file path to credentials file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param scopes: list of extra authentication scopes
        :param token_file: file path to token file
        """
        apps_scopes = ["script.projects", "drive.scripts", "script.external_request"]
        if scopes:
            apps_scopes += scopes
        self.service = self.init_service(
            service_name="script",
            api_version="v1",
            scopes=apps_scopes,
            service_account_file=service_account,
            credentials_file=credentials,
            use_robocorp_vault=use_robocorp_vault,
            token_file=token_file,
        )

    @keyword(tags=["apps script"])
    def run_script(
        self, script_id: str, function_name: str, parameters: dict = None
    ) -> None:
        """Run the Google Apps Script function

        :param script_id: Google Script identifier
        :param function_name: name of the script function
        :param parameters: script function parameters as a dictionary
        :raises AssertionError: thrown when Google Script returns errors

        Example:

        .. code-block:: robotframework

            &{params}=    Create Dictionary  formid=aaad4232  formvalues=1,2,3
            ${response}=  Run Script    abc21397283712da  submit_form   ${params}
            Log Many   ${response}
        """
        request = {
            "function": function_name,
        }
        if parameters:
            request["parameters"] = [parameters]
        response = (
            self.service.scripts()
            .run(
                body=request,
                scriptId=script_id,
            )
            .execute()
        )
        if "error" in response.keys():
            raise AssertionError(response["error"])
        return response
