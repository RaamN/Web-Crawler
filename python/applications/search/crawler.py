#!/usr/bin/python

import logging
import logging.handlers
import os
import sys
import argparse
import uuid

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "../..")))

from spacetime_local.frame import frame
from applications.search.crawler_frame import CrawlerFrame

logger = None

class Simulation(object):
    '''
    classdocs
    '''
    def __init__(self, address, port):
        '''
        Constructor
        '''
        frame_c = frame(address = "http://" + address + ":" + str(port) + "/", time_step = 1000)
        frame_c.attach_app(CrawlerFrame(frame_c))

        frame_c.run_async()
        frame.loop()

def SetupLoggers():
    global logger
    logger = logging.getLogger()
    logging.info("testing before")
    logger.setLevel(logging.DEBUG)

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    clog = logging.StreamHandler()
    clog.addFilter(logging.Filter(name='CRAWLER'))
    clog.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
    clog.setLevel(logging.DEBUG)
    logger.addHandler(clog)

if __name__== "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', type=str, help='Address of the distributing server')
    parser.add_argument('-p', '--port', type=int, help='Port used by the distributing server')
    args = parser.parse_args()
    SetupLoggers()
    sim = Simulation(args.address, args.port)
