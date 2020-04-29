import logging
import platform

if platform.system() == "Windows":
    import win32com.client


class OfficeApplication:
    """Parent class for Microsoft Office applications."""

    def __init__(self, application_name: str = None) -> None:
        self.logger = logging.getLogger(__name__)
        if platform.system() != "Windows":
            self.logger.warning(
                "OfficeApplication requires Windows dependencies to work."
            )
            return
        if application_name is None or application_name not in [
            "Word",
            "Excel",
            "Outlook",
            "Powerpoint",
        ]:
            self.logger.warning("Application name is needed")
            return
        self.application_name = application_name
        self.app = None

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open Microsoft application.

        :param visible: show Word window if True, defaults to False
        :param display_alerts: show alert popups if True, defaults to False
        """
        self.app = win32com.client.gencache.EnsureDispatch(
            f"{self.application_name}.Application"
        )

        self.logger.debug("%s.Application launched", self.application_name)
        self.logger.debug(self.app)
        if hasattr(self.app, "Visible"):
            self.app.Visible = visible
        # show eg. file overwrite warning or not
        if hasattr(self.app, "DisplayAlerts"):
            self.app.DisplayAlerts = display_alerts

    def close_document(self, save_changes: bool = False) -> None:
        if hasattr(self, "app") and self.app is not None:
            self.app.ActiveDocument.Close(save_changes)

    def quit_application(self, save_changes: bool = False) -> None:
        if hasattr(self, "app") and self.app is not None:
            self.close_document(save_changes)
            self.app.Quit()
            self.app = None
