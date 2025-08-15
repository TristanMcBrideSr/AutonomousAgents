
from datetime import datetime
from HoloAI import HoloLink

holoLink = HoloLink()

def get_current_date():
    """
    Description: "Get the current date in DD-MM-YYYY format."
    Additional Information: "This function returns the current date formatted as day-month-year."
    """
    #print("Fetching the current date")
    
    holoLink.calledActions(__name__, locals())
    return datetime.now().strftime('%d-%B-%Y')