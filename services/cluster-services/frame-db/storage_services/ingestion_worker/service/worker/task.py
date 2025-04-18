from .env import get_env_settings, exit_on_failure, exit_on_success
from .completion_notify import wrap_notify_failure, wrap_notify_success
from .pausers import Pausers
from .source import Source

from .pythreads import pythread

import os
import time

import json
import logging
logging = logging.getLogger("MainLogger")

env_settings = get_env_settings()

class Task :

    def __init__(self):

        logging.info("Initializing task")
       
        #read job type
        self.source_type = env_settings.source_type
        self.source = Source(self.source_type)

        logging.info("Task successfully initialized")

        self.threads = []
    
    @pythread
    def run_events_listner(self):

        for event in Pausers.ListenForEvents():

            logging.info("Received event {}".format(event))

            if event['type'] == "pause":
                self.source.pause(event)
            if event['type'] == "resume":
                self.source.resume(event)
            if event['type'] == "stop":
                stopData = self.source.stop()
                self.exit_with_success(stopData)
    
    
    def exit_with_success(self, success_data):

        try:
            wrap_notify_success(success_data)
            logging.info("Finished task successfully, sent completed notification")
            exit_on_success()
        except Exception as e:
            logging.error(e)
            logging.error("Stopping Task successfully, but notification failed")
            exit_on_success()
    
    @pythread
    def run_health_check(self):

        while True :
            try:
                time.sleep(30)
                for idx, thread_tuple in enumerate(self.threads) :
                    thread, name = thread_tuple
                    if not thread.is_alive() :
                        if name == "events":
                            new_wrapper = self.run_events_listner(self)
                            self.threads[idx] = (new_wrapper, "events")

                            logging.warning("Event listner thread had failed, restarted")

                    logging.info("Completed health checks")

            except Exception as e:

                logging.error("Failed to run health check, restarting after 30 seconds")
                logging.error(e)

                time.sleep(30)
    

    def __default_exit_on_error(self, e, message):
        logging.error(message)
        logging.error(e)

        wrap_notify_failure({"errData" : message, "python_exception" : str(e)})

        exit_on_failure()

    
    def run_task(self):
        
        try:
            logging.info("Task run started")

            #start threads:
            wrapper_pause = self.run_events_listner(self)

            self.threads.extend([(wrapper_pause, "events")])

            #run the health-checker
            self.run_health_check(self)

            #call the runner
            ret, data = self.source.run_task()
            if not ret :
                self.__default_exit_on_error("ErrJobRunFailed", data)
            
            logging.info("Task function returned")
            
            #successful exit
            wrap_notify_success(data)
            logging.info("Job exiting successfully.")
            exit_on_success()

        except Exception as e :
            self.__default_exit_on_error(e, "Failed to run job")