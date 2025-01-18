import re

class CommandParser:
    def __init__(self):
        self.signal_activate_pattern = r'^signal:activate (?P<signal_name>\w+)\[(?P<data>.+?)\]$'
        self.signal_exists_pattern = r'^signal:exists (?P<signal_name>\w+)$'
        
        self.command_exists_pattern = r'^command:exists (?P<command_name>\w+)$'
        self.command_run_pattern = r'^command:run (?P<dict_data>\{.*\})$'
        
        self.api_version_pattern = r'^api:version$'
        self.api_command_pattern = r'^api:command (?P<command_name>\w+)$'

    def parse(self, input_line):
        patterns = [
            (self.signal_activate_pattern, self.handle_signal_activate),
            (self.signal_exists_pattern, self.handle_signal_exists),
            (self.command_exists_pattern, self.handle_command_exists),
            (self.command_run_pattern, self.handle_command_run),
            (self.api_version_pattern, self.handle_api_version),
            (self.api_command_pattern, self.handle_api_command),
        ]
        
        for pattern, handler in patterns:
            match = re.match(pattern, input_line)
            if match:
                handler(match)
                return
        
        print("Invalid command.")

    def handle_signal_activate(self, match):
        signal_name = match.group('signal_name')
        data = match.group('data')
        print(f"Activating signal '{signal_name}' with data: {data}")

    def handle_signal_exists(self, match):
        signal_name = match.group('signal_name')
        print(f"Checking if signal '{signal_name}' exists")

    def handle_command_exists(self, match):
        command_name = match.group('command_name')
        print(f"Checking if command '{command_name}' exists")

    def handle_command_run(self, match):
        dict_data = match.group('dict_data')
        print(f"Running command with data: {dict_data}")

    def handle_api_version(self, match):
        print("Fetching API version")

    def handle_api_command(self, match):
        command_name = match.group('command_name')
        print(f"Executing API command '{command_name}'")

parser = CommandParser()

parser.parse("signal:activate signalName[data]")
parser.parse("signal:exists signalName")
parser.parse("command:exists commandName")
parser.parse("command:run {\"key\": \"value\"}")
parser.parse("api:version")
parser.parse("api:command commandName")
