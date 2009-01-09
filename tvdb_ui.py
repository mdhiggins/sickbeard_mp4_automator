"""Stores included user interfaces for Tvdb
"""

from tvdb_api import tvdb_userabort

class BaseUI:
    """Default non-interactive UI, which auto-selects first results
    """
    def __init__(self, log):
        self.log = log

    def selectSeries(self, allSeries):
        return allSeries[0]
        

class ConsoleUI(BaseUI):
    """Interactivly allows the user to select a show from a console based UI
    """
    
    def _displaySeries(self, allSeries):
        """Helper function, lists series with corresponding ID
        """
        print "TVDB Search Results:"
        for i in range(len(allSeries[:6])): # list first 6 search results
            i_show = i + 1 # Start at more human readable number 1 (not 0)
            self.log.debug('Showing allSeries[%s] = %s)' % (i_show, allSeries[i]))
            print "%s -> %s (tvdb id: %s)" % (
                i_show,
                allSeries[i]['name'].encode("UTF-8","ignore"),
                allSeries[i]['sid'].encode("UTF-8","ignore")
            )
    
    def selectSeries(self, allSeries):
        while True: # return breaks this loop
            try:
                print "Enter choice (first number, ? for help):"
                ans = raw_input()
            except KeyboardInterrupt:
                raise tvdb_userabort("User aborted (^c keyboard interupt)")

            self.log.debug('Got choice of: %s' % (ans))
            try:
                selected_id = int(ans) - 1 # The human entered 1 as first result, not zero
                self.log.debug('Trying to return ID: %d' % (selected_id))
                return allSeries[ selected_id ]
            except ValueError: # Input was not number
                if ans == "q":
                    self.log.debug('Got quit command (q)')
                    raise tvdb_userabort("User aborted ('q' quit command)")
                elif ans == "?":
                    print "## Help"
                    print "# Enter the number that corresponds to the correct show."
                    print "# ? - this help"
                    print "# q - abort tvnamer"
                else:
                    self.log.debug('Unknown keypress %s' % (ans))
            #end try
        #end while not valid_input
        