from typing import Tuple
import json


class AIOSv1PolicyRule():

    def __init__(self, id: str, init_settings: dict, init_params: dict) -> None:
    
        self.init_settings = init_settings
        self.matches = {}
      
        self.counter = 0

    def eval(self, parameters: dict, input: dict, state: dict) -> Tuple[bool, dict]:
        try:

            print('I am inside the function', parameters, input, state)

            return True, input

        except Exception as e:
          
            return False, str(e)

    def on_parameter_update(self, parameter: str, value):
        pass

    def flush(self):
        self.matches.clear()
