#                                                                                   #
#   This file defines simple questions to test the performance of the OPACA LLM.    #
#   The questions should only invoke exactly ONE action                             #
#                                                                                   #
#   The current testing environment which should deployed on the OPACA Platform:    #
#   - rkader2811/smart-office                                                       #
#   - rkader2811/warehouse                                                          #
#   - rkader2811/music-platform                                                     #
#   - rkader2811/calculator                                                         #
#                                                                                   #
from models import EvalTool, EvalToolParam, EvalMatch

simple_questions = [
    {
        "input": "Please tell me the name of the room with id 1.",
        "output": "The answer should have successfully determined that the name of the room with id 1 is 'Experience Hub'.",
        "tools": [
            EvalTool(name="GetRoomName", args=[EvalToolParam(key="room_id", value=1)])
        ]
    },
    {
        "input": "What is the name of room 7?",
        "output": "The answer should have successfully determined that the name of the room with id 7 is 'Robot Development Space'.",
        "tools": [
            EvalTool(name="GetRoomName", args=[EvalToolParam(key="room_id", value=7)])
        ]
    },
    {
        "input": "Give me the id of the Server Room",
        "output": "The answer should have successfully determined that id of the server room is 13.",
        "tools": [
            EvalTool(name="GetRoomId", args=[EvalToolParam(key="room_name", value="Server", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "What are the room names and their ids?",
        "output": "The answer should include a list of rooms including the ids 1 to 13 and 100 alongside their names.",
        "tools": [
            EvalTool(name="GetRooms")
        ]
    },
    {
        "input": "What is the highest room id?",
        "output": "The answer should have successfully determined that the highest room id is 100.",
        "tools": [
            EvalTool(name="GetRoomIds")
        ]
    },
    {
        "input": "How many bathrooms are there?",
        "output": "The answer should have successfully determined that there are 3 bathrooms in the system: 'Bathroom Women', 'Bathroom Men', and 'Bathroom Uni'.",
        "tools": [
            EvalTool(name="GetRoomNames", id=0, alternatives=[[1]]),
            EvalTool(name="GetRooms", id=1, alternatives=[[0]])
        ]
    },
    {
        "input": "Is the room 2 free?",
        "output": "The answer should tell the user that room 2 is currently available.",
        "tools": [
            EvalTool(name="CheckAvailability", args=[EvalToolParam(key="room_id", value=2)])
        ]
    },
    {
        "input": "Can I book room 3?",
        "output": "The answer should tell the user that room 3 is not available for booking.",
        "tools": [
            EvalTool(name="CheckAvailability", args=[EvalToolParam(key="room_id", value=3)])
        ]
    },
    {
        "input": "I just checked and room 4 is currently free. Book it for me!",
        "output": "The answer should tell the user that it has booked room 4.",
        "tools": [
            EvalTool(name="BookRoom", args=[EvalToolParam(key="room_id", value=4)])
        ]
    },
    {
        "input": "Can I make coffee?",
        "output": "The answer should check the status of the coffee machine. The available status can be 'making coffee...', 'unavailable', 'available', 'cleaning', or 'coffee ready!'. The answer should then tell the user if a new cup of coffee can be made, or if the coffee machine is currently in service or unavailable.",
        "tools": [
            EvalTool(name="CheckCoffeeMachineStatus")
        ]
    },
    {
        "input": "Please check the status of the coffee machine.",
        "output": "The answer should check the status of the coffee machine. The available status can be 'making coffee...', 'unavailable', 'available', 'cleaning', or 'coffee ready!'.",
        "tools": [
            EvalTool(name="CheckCoffeeMachineStatus")
        ]
    },
    {
        "input": "What are the available desks?",
        "output": "The answer should provide the user with a list of 1 to 10, each being the number of a specific desk.",
        "tools": [
            EvalTool(name="GetDesks")
        ]
    },
    {
        "input": "Does desk number 17 exist?",
        "output": "The answer should tell the user, that desk number 17 does not exist.",
        "tools": [
            EvalTool(name="GetDesks")
        ]
    },
    {
        "input": "I want to book desk 2, is it available?",
        "output": "The answer should confirm that desk 2 is available for booking.",
        "tools": [
            EvalTool(name="IsFree", args=[EvalToolParam(key="desk", value=2)])
        ]
    },
    {
        "input": "I think desk 7 might be occupied, am I right?",
        "output": "The answer should confirm the user by saying that desk 7 is occupied.",
        "tools": [
            EvalTool(name="IsFree", args=[EvalToolParam(key="desk", value=7)])
        ]
    },
    {
        "input": "Book me desk 6",
        "output": "The answer should confirm the booking of desk 6 to the user.",
        "tools": [
            EvalTool(name="BookDesk", args=[EvalToolParam(key="desk", value=6)])
        ]
    },
    {
        "input": "Try to book desk 3 and tell me what happened.",
        "output": "The answer should inform the user, that the booking was not successful. The reasons can include either the desk not being available at the moment, or an invalid desk number.",
        "tools": [
            EvalTool(name="BookDesk", args=[EvalToolParam(key="desk", value=3)])
        ]
    },
    {
        "input": "What is the current status of the system?",
        "output": "The answer should tell the user, that a full system check was performed, which yielded the following results: - Thermostat: Damaged, - Air Quality Monitor: Functioning, - Security Camera: Damaged, - Network Router: Functioning, - HVAC System Controller: Functioning.",
        "tools": [
            EvalTool(name="RunFullSystemCheck")
        ]
    },
    {
        "input": "Perform a system check",
        "output": "The answer should tell the user, that a full system check was performed, which yielded the following results: - Thermostat: Damaged, - Air Quality Monitor: Functioning, - Security Camera: Damaged, - Network Router: Functioning, - HVAC System Controller: Functioning.",
        "tools": [
            EvalTool(name="RunFullSystemCheck")
        ]
    },
    {
        "input": "Something seems off about device 0, can you check?",
        "output": "The answer should confirm that device 0, the thermostat, was found to be damaged.",
        "tools": [
            EvalTool(name="CheckDeviceHealth", args=[EvalToolParam(key="device_id", value=0)])
        ]
    },
    {
        "input": "Is device 4 functioning properly?",
        "output": "The answer should tell the user that device 4, the HVAC System Controller, is functioning properly.",
        "tools": [
            EvalTool(name="CheckDeviceHealth", args=[EvalToolParam(key="device_id", value=4)])
        ]
    },
    {
        "input": "For how long has the system been up?",
        "output": "The answer should give the timespan of how long the system has been up. This value can be given as a unix timestamp.",
        "tools": [
            EvalTool(name="GetSystemUptime")
        ]
    },
    {
        "input": "How much time has been passed since the last reboot?",
        "output": "The answer should give the timespan of how long the system has been up since the last reboot. This value can be given as a unix timestamp.",
        "tools": [
            EvalTool(name="GetSystemUptime")
        ]
    },
    {
        "input": "What are the devices in the system?",
        "output": "The answer should include a list of all the devices in the system: - Thermostat (id 0), - Air Quality Monitor (id 1), - Security Camera (id 2), - Network Router (id 3), - HVAC System Controller (id 4)",
        "tools": [
            EvalTool(name="ListActiveDevices")
        ]
    },
    {
        "input": "What are the ids and names of the devices in the system?",
        "output": "The answer should include a list of all the devices and their ids in the system: - Thermostat (id 0), - Air Quality Monitor (id 1), - Security Camera (id 2), - Network Router (id 3), - HVAC System Controller (id 4)",
        "tools": [
            EvalTool(name="ListActiveDevices")
        ]
    },
    {
        "input": "What is the id of the network router?",
        "output": "The answer should tell the user the id of the network router is 3.",
        "tools": [
            EvalTool(name="GetDeviceId", args=[EvalToolParam(key="device_name", value="router", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "How is the thermostat identified within the system?",
        "output": "The answer should tell the user the id of the thermostat is 0.",
        "tools": [
            EvalTool(name="GetDeviceId", args=[EvalToolParam(key="device_name", value="thermostat", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "Make a report of the system and show it to me.",
        "output": "The answer should include a detailed report of the system devices, their operational status, the system status, error logs, and upcoming maintenances.",
        "tools": [
            EvalTool(name="GenerateReport")
        ]
    },
    {
        "input": "Can you give me the latest report of the system?",
        "output": "The answer should include a detailed report of the system devices, their operational status, the system status, error logs, and upcoming maintenances.",
        "tools": [
            EvalTool(name="GenerateReport")
        ]
    },
    {
        "input": "Can you tell me how the network is currently doing?",
        "output": "The answer should tell the user, that the network is currently functioning properly.",
        "tools": [
            EvalTool(name="CheckNetworkStatus")
        ]
    },
    {
        "input": "How is our network doing?",
        "output": "The answer should tell the user, that the network is currently functioning properly.",
        "tools": [
            EvalTool(name="CheckNetworkStatus")
        ]
    },
    {
        "input": "Please restart the device 3",
        "output": "The answer should confirm that device 3 has been restarted.",
        "tools": [
            EvalTool(name="RestartDevice", args=[EvalToolParam(key="device_id", value=3)])
        ]
    },
    {
        "input": "Try to restart device 4, but tell me what happened.",
        "output": "The answer should confirm that device 4 has been restarted.",
        "tools": [
            EvalTool(name="RestartDevice", args=[EvalToolParam(key="device_id", value=4)])
        ]
    },
    {
        "input": "I want to order something to eat, what are my options?",
        "output": "The answer should have retrieved a list of snacks. The full list of snacks should include 'chips', 'nuts', 'chocolate bar', 'gummy bears', 'apples', and 'ice'. Nothing should have been ordered yet.",
        "tools": [
            EvalTool(name="GetSnackInventory")
        ]
    },
    {
        "input": "Please schedule a cleaning day for the kitchen on 1st of February 2025.",
        "output": "The answer should confirm that a cleaning day has been scheduled on the 1st of February 2025.",
        "tools": [
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-02-01")])
        ]
    },
    {
        "input": "Rent the fridge space with id 62 for 6 hours.",
        "output": "The answer should decline the request, since the available method to reserve a fridge space does only allow to specify a duration of days.",
        "tools": []
    },
    {
        "input": "Rent the fridge space with id 62 for 2 days.",
        "output": "The answer should confirm that the fridge space with the id 62 was successfully rented for a duration of 2 days.",
        "tools": [
            EvalTool(name="ReserveFridgeSpace", args=[EvalToolParam(key="space_id", value=62), EvalToolParam(key="duration", value=2)])
        ]
    },
    {
        "input": "The dishwasher is once again not working... let someone know to fix this damn thing!",
        "output": "The answer should confirm is has reported a kitchen issue by calling the necessary action. The action itself does not return a confirmation, so the answer might indicate that it is unable to confirm whether the issue has been acknowledged or not.",
        "tools": [
            EvalTool(name="ReportKitchenIssue", args=[EvalToolParam(key="issue_description", value="issue", match=EvalMatch.NONE)])
        ]
    },
    {
        "input": "Is it just me or is the water in the kitchen dirty?",
        "output": "The answer should tell the user, that it has checked the water filter status. Based on the status, which can be 'Clean', 'Slightly used', 'Dirty', or 'Dysfunctional'. If the status is 'Clean', the answer should tell the user that the water should be safe to drink. Otherwise, the answer should tell the user, that the water filter should be checked and changed and that the water might not be safe to drink.",
        "tools": [
            EvalTool(name="CheckWaterFilterStatus")
        ]
    },
    {
        "input": "Remind me, what did I want to buy at the store?",
        "output": "The answer should have checked the current grocery list. This list includes: 'bread', 'tomato', 'pasta', 'water', 'juice'",
        "tools": [
            EvalTool(name="GetGroceryList")
        ]
    },
    {
        "input": "It is too dark in room 4, please change that.",
        "output": "The answer should tell the user, that it has turned on the lights in room 4.",
        "tools": [
            EvalTool(name="TurnOnLights", args=[EvalToolParam(key="room_id", value=4)])
        ]
    },
    {
        "input": "Can you tell me which rooms exist in this office building?",
        "output": "The answer should tell the user every existing room, which includes: 'Experience Hub', 'Conference Room', 'Management Office', 'Focus Space', 'Design Thinking Space', 'Co-Working Space', 'Robot Development Space', 'Robot Testing Area', 'Bathroom Women', 'Bathroom Men', 'Bathroom Uni', 'Kitchen', 'Server Room', 'VIP Room'.",
        "tools": [
            EvalTool(name="GetRooms", id=0, alternatives=[[1]]),
            EvalTool(name="GetRoomNames", id=1, alternatives=[[0]]),
        ]
    },
    {
        "input": "Give me every available data for room 10.",
        "output": "The answer should give information about room 10 for its temperature, co2 level, humidity, noise leve, and the sensor battery level.",
        "tools": [
            EvalTool(name="GetCompleteInfo", args=[EvalToolParam(key="room_id", value=10)])
        ]
    },
    {
        "input": "I need to order four computer mouses.",
        "output": "The answer should confirm that an order has been placed for 4 computer mouses. The id of the order should be given within the answer. The id number should be positive or 0, both are valid order ids.",
        "tools": [
            EvalTool(name="MakeOrder", args=[EvalToolParam(key="item", value="mouse", match=EvalMatch.PARTIAL), EvalToolParam(key="amount", value=4)])
        ]
    },
    {
        "input": "In which zone can I find a fax-machine?",
        "output": "The answer should tell the user, that the item 'fax-machine' can be found in 'zone-C'.",
        "tools": [
            EvalTool(name="GetItemLocation", args=[EvalToolParam(key="item", value="fax-machine")])
        ]
    },
    {
        "input": "What items can be found in 'zone-B'?",
        "output": "The answer should have identified the items in 'zone-B' to be 'box', 'wrap', 'tape', 'rope', 'strap'.",
        "tools": [
            EvalTool(name="GetInventory", args=[EvalToolParam(key="zone", value="zone-B")])
        ]
    },
    {
        "input": "Is there a way I can write an email to the warehouse?",
        "output": "The answer should tell the user, that the e-mail address to contact the warehouse is 'Warehouse@mail.com'.",
        "tools": [
            EvalTool(name="GetWarehouseEmail")
        ]
    },
    {
        "input": "What are the sizes of each zone?",
        "output": "The answer should tell the user the following sizes: ('zone-A', 2000), ('zone-B', 1000), ('zone-C', 750), ('zone-D', 750), ('zone-E', 500). It should also tell the user, that the sizes are given as square meters.",
        "tools": [
            EvalTool(name="GetWarehouseZoneSizes")
        ]
    },
    {
        "input": "What is the location second logistic robot?",
        "output": "The answer should tell the user, that logistic robot 2 is currently located in 'zone-C'.",
        "tools": [
            EvalTool(name="GetZone")
        ]
    },
    {
        "input": "Is the first logistic robot carrying something at the moment?",
        "output": "The answer should tell the user, that the logistic robot 1 has items within its inventory, which include: 'ball', 'shovel', 'towel'. Therefore, it should tell the user, that the logistic robot 1 is in fact carrying items.",
        "tools": [
            EvalTool(name="GetInventory")
        ]
    },
    {
        "input": "Please start playing the track 7",
        "output": "The answer should confirm to the user, that the track with id 7 is now currently playing.",
        "tools": [
            EvalTool(name="PlayTrack", args=[EvalToolParam(key="track_id", value=7)])
        ]
    },
    {
        "input": "Please set the volume down to 3",
        "output": "The answer should confirm that the current volume level has been set to 3.",
        "tools": [
            EvalTool(name="AdjustVolume", args=[EvalToolParam(key="volume", value=3)])
        ]
    },
    {
        "input": "What is 42 to the power of 4?",
        "output": "The answer should include the result for the calculation of 42 to the power of 4, which is 3,111,696.",
        "tools": [
            EvalTool(name="Power", args=[EvalToolParam(key="base", value=42), EvalToolParam(key="exp", value=4)])
        ]
    },
    {
        "input": "What is the sine of 2.857?",
        "output": "The answer should tell the sine of 2.857, which is roughly 0.2807665132504996. If the result is approximately this value, the answer can be seen as fulfilled.",
        "tools": [
            EvalTool(name="Sin", args=[EvalToolParam(key="a", value=2.857)])
        ]
    },
    {
        "input": "What would I get, if I subtract twelve from one hundred and four?",
        "output": "The answer should tell the user the result of 104 minus 12, which is 92, or ninety-two.",
        "tools": [
            EvalTool(name="Subtract", args=[EvalToolParam(key="a", value=104), EvalToolParam(key="b", value=12)])
        ]
    },
]
