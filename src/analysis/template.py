import ipc
from backend import Record

def someAnalysis(evt, type, key, keyword=None):
    """An example for an analysis module. Please document here in the docstring:

    - what the module is doing
    - what arguments need to be passed
    - what the module returns (adds to the event variable)
    - who the authors are

    Args:
        :evt:       The event variable
        :type(str): The event type
        :key(str):  The event key

    Kwargs:
        :keyword(type): Kewyword description (default = None)

    :Authors: 
        Name (email), 
        Name (email)
    """

    # ADD YOUR CODE HERE
    # 
    # something = ....
    
    evt["analysis"]["something_new - " + key] = Record("something_new - " + key, something, unit=some_unit)
