from core.communication.protocol import Protocol
from core.communication.wifi.tcp.protocols.tcp_json_protocol import TCP_JSON_Protocol, TCP_JSON_Message
from core.communication.wifi.wifi_connection import WIFI_Connection
from core.communication.wifi.data_link import DataLink, Command, generateDataDict, generateCommandDict
from utils.callbacks import Callback, callback_handler, CallbackContainer
from utils.events import event_handler
from utils.logging_utils import Logger

# === GLOBAL VARIABLES =================================================================================================
logger = Logger("WIFI INTERFACE")


# ======================================================================================================================
@callback_handler
class WIFI_Interface_Callbacks:
    connected: CallbackContainer
    disconnected: CallbackContainer
    sync: CallbackContainer
    rx: CallbackContainer


@event_handler
class WIFI_Interface_Events:
    ...


class Stream:
    parameters: list
    connection: object
    interval: float


# ======================================================================================================================
class WIFI_Interface:
    name: str
    id: str
    device_class: str
    device_type: str
    device_revision: str

    uid: bytes
    data: dict[str, (dict, DataLink)]
    commands: dict[str, (dict, Command)]

    connection: WIFI_Connection

    streams: list[Stream]  # TODO: Could be removed. Not used

    connected: bool

    callbacks: WIFI_Interface_Callbacks

    protocol: Protocol = TCP_JSON_Protocol

    # === INIT =========================================================================================================
    def __init__(self, interface_type: str = 'wifi', device_class: str = None, device_type: str = None,
                 device_revision: str = None,
                 device_name: str = None, device_id: str = None):
        # Read the device config file

        self.device_class = device_class
        self.device_type = device_type
        self.device_revision = device_revision
        self.name = device_name
        self.id = device_id
        self.connected = False

        self.callbacks = WIFI_Interface_Callbacks()
        # --- WIFI ---
        # Add the WI-FI connection with the pre-configured address and name
        if interface_type == 'wifi':
            self.connection = WIFI_Connection(id=device_id)
        else:
            raise Exception("Not implemented yet")

        # Configure the WI-FI connection
        self.connection.callbacks.connected.register(self._connected_callback)
        self.connection.callbacks.disconnected.register(self._disconnected_callback)
        self.connection.callbacks.rx.register(self._rx_callback)

        # --- PARAMETERS ---
        # Set up the parameters
        self.data = {}  # TODO: Where to get the parameters from? Import them from a certain python file for this board?

        # --- COMMANDS ---
        self.commands = {}

    # === METHODS ======================================================================================================
    def start(self):
        logger.info("start WIFI Interface")
        self.connection.start()

    # ------------------------------------------------------------------------------------------------------------------
    def close(self):
        self.connection.close()

    # ------------------------------------------------------------------------------------------------------------------
    def sendEventMessage(self):
        ...

    # ------------------------------------------------------------------------------------------------------------------

    def sendStreamMessage(self, data):
        msg = TCP_JSON_Message()
        msg.source = self.id
        msg.address = 0
        msg.type = 'stream'
        msg.data = data

        self._wifi_send(msg)

    # ------------------------------------------------------------------------------------------------------------------
    def addCommands(self, commands):
        if isinstance(commands, Command):
            self.commands[commands.identifier] = commands
        elif isinstance(commands, list):
            assert all(isinstance(command, Command) for command in commands)
            for command in commands:
                self.commands[command.identifier] = command
        elif isinstance(commands, dict):
            for command_identifier, command in commands.items():
                assert (isinstance(command, Command))
                self.commands[command_identifier] = command

    # ------------------------------------------------------------------------------------------------------------------
    def addCommand(self, identifier: str, callback: (callable, Callback), arguments: list[str], description: str):
        self.commands[identifier] = Command(identifier=identifier, callback=callback, arguments=arguments,
                                            description=description)

    # === PRIVATE METHODS ==============================================================================================
    def _wifi_send(self, message):
        self.connection.send(message)

    # ------------------------------------------------------------------------------------------------------------------
    def _connected_callback(self):
        self._sendDeviceIdentification()
        self.connected = True
        for callback in self.callbacks.connected:
            callback(self)

    # ------------------------------------------------------------------------------------------------------------------
    def _disconnected_callback(self):
        self.connected = False
        for callback in self.callbacks.disconnected:
            callback(self)

    # ------------------------------------------------------------------------------------------------------------------
    def _rx_callback(self, message, *args, **kwargs):

        # Handle the message
        self._handleRxMessage(message)

    # ------------------------------------------------------------------------------------------------------------------
    def _handleRxMessage(self, message: TCP_JSON_Message):
        # Make sure the message is of the correct type. If this is not the case, the communication channels are not
        # configured correctly
        # assert (isinstance(message, self.protocol.Message))
        # # Check if the message has the correct command
        # assert (message.type in self.protocol.allowed_types)
        # Handle the message based on the issued command
        if message.type == 'write':
            self._handler_writeMessage(message)
        elif message.type == 'read':
            self._handler_readMessage(message)
        elif message.type == 'function':
            self._handler_functionMessage(message)
        elif message.type == 'event':
            self._handlerEventMessage(message)


        self.callbacks.rx.call(message)
    # ------------------------------------------------------------------------------------------------------------------
    def _handler_writeMessage(self, message: TCP_JSON_Message):
        # Go over the entries in the data dictionary
        return
        raise NotImplementedError("Writing is not finished yet. Response is missing")


        # for entry, value in message.data.items():
        #
        #     # Check if the entry is also in the parameters dict
        #     if entry not in self.data:
        #         logger.warning(f"Received parameter {entry}, which is not a valid entry.")
        #         continue
        #
        #     # Check if the entry is a parameter or a dict (group of parameters).
        #     # TODO: We only allow one level of grouping for now
        #
        #     # The entry is a parameter
        #     if isinstance(self.data[entry], DataLink):
        #         self.data[entry].set(value)
        #         logger.debug(f"Set parameter {entry} to value {value}.")
        #
        #     # The entry is a group of parameters
        #     elif isinstance(self.data[entry], dict) and isinstance(value, dict):
        #         for sub_entry, sub_value in value.items():
        #             if not sub_entry in self.data[entry]:
        #                 logger.warning(f"Received parameter {entry}:{sub_entry}, which is not a valid entry.")
        #                 continue
        #             if not (isinstance(self.data[entry][sub_entry], DataLink)):
        #                 logger.warning(f"Cannot set parameter {sub_entry}: Grouping level exceeds allowed level of: 1")
        #             self.data[entry][sub_entry].set(sub_value)
        #             logger.debug(f"Set parameter {entry}:{sub_entry} to value {sub_value}.")
        #     else:
        #         print("OH NOOO")

    # ------------------------------------------------------------------------------------------------------------------
    def _handler_readMessage(self, data):
        logger.warning("Read messages are not implemented yet")

    # ------------------------------------------------------------------------------------------------------------------
    def _handler_functionMessage(self, message: TCP_JSON_Message):
        # Check for the function name

        if not 'function' in message.data:
            logger.warning("Received function message without function name")
            return

        function_name = message.data['function']

        # Check if the function is in the commands
        if not function_name in self.commands:
            logger.warning(f"Received function {function_name}, which is not a valid entry.")

        # Check if 'input' is in the data
        if not 'input' in message.data:
            logger.warning(f"Received function {function_name} without input")
            return

        value = message.data['input']

        output = None
        error = None

        try:
            output = self.commands[function_name].execute(value)
            success = True
        except Exception as e:
            logger.warning(f"Error executing function {function_name}: {e}")
            success = False
            error = str(e)

        if message.request_response is not None:
            # This is more important than request ack and leads to a response message. The sender is requesting a response
            response_message = TCP_JSON_Message()
            response_message.address = ''
            response_message.source = ''
            response_message.type = 'response'
            response_message.request_id = message.id
            response_message.data['output'] = output
            response_message.data['error'] = error
            response_message.data['success'] = success

            self._wifi_send(response_message)

        else:
            response_message = None


    # ------------------------------------------------------------------------------------------------------------------
    def _handlerEventMessage(self, message):
        if message.data['event'] == 'sync':
            for callback in self.callbacks.sync:
                callback(message.data)

        # TODO Add response if wanted

    # ------------------------------------------------------------------------------------------------------------------
    def _sendDeviceIdentification(self):
        msg = TCP_JSON_Message()
        msg.source = self.id
        msg.address = ''
        msg.type = 'event'

        msg.data = {
            'event': 'device_identification',
            'device_class': self.device_class,
            'device_type': self.device_type,
            'device_name': self.name,
            'device_id': self.id,
            'address': self.id,
            'revision': self.device_revision,
            'data': generateDataDict(self.data),
            'commands': generateCommandDict(self.commands)
        }

        self._wifi_send(msg)
