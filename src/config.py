class IDatabaseConfig:
    def __init__(self, **kwargs):
        self.database = kwargs.get("database")
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.hostname = ""
        self.port = 0
        self.socketAddress = ""
