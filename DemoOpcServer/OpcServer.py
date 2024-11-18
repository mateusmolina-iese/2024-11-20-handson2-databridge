import asyncio
import logging
import uuid
import random

from enum import Enum
from aiohttp import web

from asyncua import Server, ua, Node
from asyncua.server.users import UserRole, User
from asyncua.ua.uaprotocol_auto import EUInformation
from asyncua.common.structures104 import new_enum

# class for User Management (login via username and password)
class UserManager:
    def __init__(self, valid_username, valid_password):
        self.valid_username = valid_username
        self.valid_password = valid_password

    def get_user(self, iserver, username=None, password=None, certificate=None):
        # Check if the provided credentials match the valid credentials
        if username == self.valid_username and password == self.valid_password:
            return User(role=UserRole.User)
        return None
    

class MachineStateEnum(Enum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2
    IDLE = 3


# Method to set up variable nodes
async def setup_variable_nodes(parent, idx):
    # Create a folder object of FolderType
    folder_obj = await parent.add_object(idx, "MyFolder", objecttype=ua.ObjectIds.FolderType)

    # Create the first object node under the folder
    obj1 = await folder_obj.add_object(idx, "MyObject")

    # Add variables of different types to this object with different NodeId types
    var1 = await obj1.add_variable(idx, "Var1", 42)  # Integer
    # Float
    var2 = await obj1.add_variable(f"ns={idx};s=MyStringNodeIdVar2", "Var2", 3.14)
    guid_id = str(uuid.uuid4())
    # Boolean
    var3 = await obj1.add_variable(f"ns={idx};g={guid_id}", "Var3", True)
    # String
    var4 = await obj1.add_variable(f"ns={idx};b=MyBinaryNodeIdVar4", "Var4", "Hello World")

    # Set the variables to be writable
    await var1.set_writable()
    await var2.set_writable()
    await var3.set_writable()
    await var4.set_writable()

    # Create the second, empty object node under the folder
    # await folder_obj.add_object(idx, "EmptyObject")

    return folder_obj


# Method to add a complete temperature object with a temperature variable and EUInformation
async def add_temperature_object(parent, idx) -> Node:
    # Create a new object for the temperature
    temp_obj = await parent.add_object(idx, "TemperatureObject")

    # Add a temperature variable
    temp_var = await temp_obj.add_variable(idx, "Temperature", 25.0, varianttype=ua.VariantType.Float)
    await temp_var.set_writable()

    # Create EUInformation for the temperature unit (e.g., degrees Celsius)
    eu_info = EUInformation()
    eu_info.DisplayName = ua.LocalizedText("Celsius")
    eu_info.Description = ua.LocalizedText("Degrees Celsius")
    eu_info.UnitId = 4408652  # UnitId for degrees Celsius as per OPC UA standard

    # Add EUInformation as a PropertyType to the temperature variable
    eu_var = await temp_var.add_property(idx, "Unit", eu_info)
    await eu_var.set_writable()

    return temp_obj


async def add_dynamic_object(parent, idx) -> Node:
    # Create a new object
    dynamic_obj = await parent.add_object(idx, "DynamicObject")

    # Add a node with localized text
    localized_text_node = await dynamic_obj.add_variable(idx, "LocalizedText", ua.LocalizedText("Initial Text", "en"))
    await localized_text_node.set_writable()

    # Add a node with a float value
    float_node = await dynamic_obj.add_variable(idx, "DynamicFloat", 0.0)
    await float_node.set_writable()

    # Function to update the float value every 100ms
    async def update_float_value():
        while True:
            # Random float value for demonstration
            new_value = random.uniform(0.0, 100.0)
            await float_node.write_value(new_value)
            await asyncio.sleep(0.1)  # 100ms

    # Start the coroutine to update the float value
    asyncio.create_task(update_float_value())

    return dynamic_obj


async def add_enum_node(server, parent, idx) -> Node:
    # Create the enumeration data type
    enumeration = await new_enum(server, idx, "MachineStateEnum", [
        "STOPPED",
        "RUNNING",
        "PAUSED",
        "IDLE"
    ])

    # Create a new object
    enum_obj = await parent.add_object(idx, "EnumObject")

    # Add a node with the enumeration data type
    enum_node = await enum_obj.add_variable(idx, "MachineState", MachineStateEnum.STOPPED.value, datatype=enumeration.nodeid)
    await enum_node.set_writable()
    await enum_node.set_value(0)

    return enum_obj


async def start_http_server():
    app = web.Application()
    app.router.add_get('/health', lambda request: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()


async def main():
    ###########   OPC Server Setup   ###########
    logging.basicConfig(level=logging.INFO)

    # Define valid username and password
    valid_username = "test"
    valid_password = "test"

    # Create the server with the custom UserManager
    server = Server(user_manager=UserManager(valid_username, valid_password))
    await server.init()

    # Register a new namespace
    uri = "https://htw-berlin.de"
    idx = await server.register_namespace(uri)

    # create an object calles OpcTest
    opc_test = await server.nodes.objects.add_object(idx, "OpcTest")

    # Call the method to set up variable nodes
    await setup_variable_nodes(opc_test, idx)

    # Add the temperature object with a single line
    await add_temperature_object(opc_test, idx)

    # Add dynamic object with localized text and dynamic float node
    await add_dynamic_object(opc_test, idx)

    # Add an enumeration node
    await add_enum_node(server, opc_test, idx)

    # Start the HTTP server for health checks
    await start_http_server()

    # Start the server
    async with server:
        print("Server started at {}".format(server.endpoint))
        # Run the server indefinitely
        stop_event = asyncio.Event()
        await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
