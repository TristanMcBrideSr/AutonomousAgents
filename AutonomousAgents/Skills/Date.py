
from datetime import datetime
from HoloLink import ArgumentParser

argParser = ArgumentParser()

def getDate():
    """
    Description: "Get the current date in DD-MM-YYYY format."
    Additional Information: "This function returns the current date formatted as day-month-year."
    """
    argParser.printArgs(__name__, locals())
    return datetime.now().strftime('%d-%B-%Y')