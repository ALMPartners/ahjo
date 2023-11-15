from logging import Handler, LogRecord
import win32evtlog
import win32evtlogutil
import re

class winEventHandler(Handler):
    """
    Custom logging handler for sending messages to Windows Event Log.
    """
    def __init__(self):
        Handler.__init__(self)
        self.logToWindowsEventLog = False
    
    def emit(self, x: LogRecord):
        """
        Emit a record.
        """
        if self.logToWindowsEventLog:
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