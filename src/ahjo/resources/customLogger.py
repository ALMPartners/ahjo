import logging
from logging import Handler
# from logging.handlers import RotatingFileHandler
import win32evtlog
import win32evtlogutil
import re

class customHandler(Handler):

    def __init__(self):
        Handler.__init__(self)
    
    def emit(self, x: logging.LogRecord):
        # print(x.name) # nimi = Ahjo
        # print(x.msg) # viest = [2023-10-12 12:12:12,123] Successfully loaded ahjo_actions
        # print(x.args) # args = ()
        # print(x.levelname) # lvlname = INFO
        # print(x.levelno) # 20
        # print(x.pathname) # C:\Git\ahjo\src\ahjo\action.py
        # print(x.filename) # action.py
        # print(x.module) # action
        # print(x.exc_info) # None
        # print(x.exc_text) # None
        # print(x.stack_info) # None
        # print(x.lineno) # 225
        # print(x.funcName) # import_actions
        # print(x.created) # 1697626681.6447659
        # print(x.msecs) # 644.0
        # print(x.relativeCreated) # 1280.8003425598145
        # print(x.thread) # 7748
        # print(x.threadName) # MainThread
        # print(x.processName) # MainProcess
        # print(x.process) # 21800

        # If message is not empty and not only dashes, then send it to Windows Event Log
        if x.msg and x.msg != '' and not bool(re.search('^[-]*+$', x.msg)):
            msg = re.sub("^([\[]).*?([\]])", "", x.msg).lstrip() # remove timestamps from the start of message
            winLevels = {
                "DEBUG": win32evtlog.EVENTLOG_INFORMATION_TYPE,
                "INFO": win32evtlog.EVENTLOG_INFORMATION_TYPE,
                "WARNING": win32evtlog.EVENTLOG_WARNING_TYPE,
                "ERROR": win32evtlog.EVENTLOG_ERROR_TYPE,
                "CRITICAL": win32evtlog.EVENTLOG_ERROR_TYPE
            }
            level = winLevels[x.levelname]
            win32evtlogutil.ReportEvent(
                x.name,
                9876,
                eventCategory=0,
                eventType=level,
                strings=[msg]
            )