from threading import Thread


class ThreadWrapper(Thread):

    def __init__(self, function, arguments) :

        Thread.__init__(self)
        self.function = function
        self.args = arguments['args']
        self.kwargs = arguments['kwargs']

    
    def run(self):
        self.function(*self.args, **self.kwargs)


class PyThread():

    def __init__(self, function):
        self.function = function
    
    def runner(self):

        thread_wrapper = ThreadWrapper(self.function, {'args' : self.args, 'kwargs' : self.kwargs})

        thread_wrapper.start()
        return thread_wrapper

    
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        thread_wrapper = self.runner()
        return thread_wrapper
        


