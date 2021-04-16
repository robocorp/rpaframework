from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class AppsScriptKeywords(LibraryContext):
    """Class for Google Apps Script API

    **Note:** The Apps Script API does not work with _service accounts_

    Following steps are needed to authenticate and use the service:

    1. enable Apps Script API in the Cloud Platform project (GCP)
    2. create OAuth credentials so API can be authorized (download ``credentials.json``
       which is needed to initialize service)
    3. the Google Script needs to be linked to Cloud Platform project number
    4. Google Script needs to have necessary OAuth scopes to access app
       which is being scripted
    5. necessary authentication scopes and credentials.json are needed
       to initialize service and run scripts

    For more information about Google Apps Script API link_.

    .. _link: https://developers.google.com/apps-script/api
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_apps_script(
        self,
        scopes: list = None,
        token_file: str = None,
        service_account: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Sheets client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        apps_scopes = ["script.projects"] + scopes if scopes else []
        self.service = self.init_service(
            "script",
            "v1",
            apps_scopes,
            service_account,
            use_robocloud_vault,
            token_file,
        )

    @keyword
    def run_script(self, script_id: str, function_name: str, parameters: dict) -> None:
        """Run the Google Apps Script

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
            "parameters": [parameters],
        }
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
