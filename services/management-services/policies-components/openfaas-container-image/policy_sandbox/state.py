

class InMemoryDefaultStateBackend:
    def __init__(self) -> None:
        self.init_state = None
    
    def get_internal(self) -> dict:
        return self.init_state
    
    def set(self, key, value):
        self.init_state[key] = value
    
    def get(self, key, default):
        return self.init_state.get(key, default)
    
    def flush(self):
        self.init_state.clear()
    
    def set_init_state(self, init_state: dict):
        self.init_state = init_state
    
    def remove(self, key):
        if key in self.init_state:
            del self.init_state[key]


class StateManager:
    def __init__(self, init_state: dict, backend) -> None:
        self.backend = backend
        self.backend.set_init_state(init_state)
    
    def __setitem__(self, key, value):
        self.backend.set(key, value)
    
    def __getitem__(self, key):
        return self.backend.get(key, None)
    
    def get(self, key, default):
        return self.backend.get(key, default)
    
    def __delitem__(self, key):
        self.backend.remove(key)
    
    def clear(self):
        self.backend.flush()