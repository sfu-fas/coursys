from ..table import Table

class FakeReport():
    """ This report doesn't connect to DB2. It just returns a block
        of preset data. """
    
    def __init__(self, logger):
        self.artifacts = []
        self.logger = logger
        pass

    def run(self):
        ft = Table()

        self.logger.log("Generating fake report data!")
        
        ft.append_column("EMPLID")
        ft.append_column("Deliciousness")
        ft.append_column("Belafonte Ranking")
        ft.append_row(["301008183", "High", "99"])
        ft.append_row(["123456789", "Medium", "1"])
        ft.append_row(["123456788", "Low", "123"])
        ft.append_row(["123456787", "Caliente", "333"])
        
        self.artifacts.append(ft)
