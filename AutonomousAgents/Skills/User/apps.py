import threading
import logging
import subprocess
import os
from HoloAI import HoloLink

logger = logging.getLogger(__name__)

APP_NAME_MAP = {
    "vs code": "code",
    "vs studio": "devenv",
    "vs insiders": "code - insiders",
    "word": "winword",
    "powerpoint": "powerpnt",
    "explorer": "iexplore",
}


class AppManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AppManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        self._initComponents()
        self.initialized = True

    def _initComponents(self):
        self.holoLink = HoloLink()
        self.nameMap = APP_NAME_MAP.copy()
        self.actionMap = {
            "open": self._openApp,
            "close": self._closeApp,
        }

    def _metaData(self):
        return {
            "className": f"{self.__class__.__name__}",
            "description": "Open and close applications on the computer"
        }

    def executeAction(self, ctx: str) -> str:
        """
        Description: Executes the requested action for application management based on context.
        """
        self.holoLink.calledActions(self, locals())
        try:
            ctxLower = ctx.lower()
            actionKey = next((key for key in self.actionMap if key in ctxLower), None)
            if not actionKey:
                return None
            args = ctxLower.replace(actionKey, "", 1).strip()
            return self.actionMap[actionKey](args)
        except Exception as e:
            logger.error(f"Error executing {self.__class__.__name__.lower()}Action '{ctx}':", exc_info=True)
            return f"Error: {e}"

    def _normalizeAppName(self, appName: str) -> str:
        app = appName.lower()
        return next((replacement for key, replacement in self.nameMap.items() if key in app), appName)

    def _openApp(self, appName: str) -> str:
        app = self._normalizeAppName(appName)
        try:
            os.startfile(app)
            return f"Opened {app}"
        except Exception as e:
            logger.error(f"Error opening {app}:", exc_info=True)
            return f"An error occurred while trying to open {app}: {e}"

    def _closeApp(self, appName: str) -> str:
        app = self._normalizeAppName(appName)
        if not app.lower().endswith('.exe'):
            app += '.exe'
        try:
            subprocess.run(
                ["taskkill", "/f", "/im", app],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return f"Closed {app}"
        except Exception as e:
            logger.error(f"Error closing {app}:", exc_info=True)
            return f"An error occurred while trying to close {app}: {e}"
