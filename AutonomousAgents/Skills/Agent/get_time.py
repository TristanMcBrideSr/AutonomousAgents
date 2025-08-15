
from datetime import datetime
from HoloAI import HoloLink

holoLink = HoloLink()

def get_current_time():
    """
    Description: "Get the current time in HH:MM format."
    Additional Information: "This function returns the current time formatted as hour:minute."
    """
    holoLink.calledActions(__name__, locals())
    return datetime.now().strftime('%H:%M')
