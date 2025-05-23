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

    ### Room Agent

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

    ### Desk Booking Agent

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

    ### Diagnostics Agent

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
        "input": "I need you to make a maintenance date for device 4 on the first may 2025.",
        "output": "The answer should confirm that a maintenance date has been scheduled for device 4 on the 1st of May 2025.",
        "tools": [
            EvalTool(name="ScheduleMaintenance", args=[EvalToolParam(key="device_id", value=4), EvalToolParam(key="date", value="2025-05-01")])
        ]
    },
    {
        "input": "So I have this broken device, it has id 1, and I think it would be best if we would create a maintenance date for it. The maintenance is mainly a repair, since I think it is not functioning correctly. Anyway, the best date, for me at least, would be the 1st of May 2025. Please take care of that!",
        "output": "The answer should confirm that a maintenance date has been scheduled for device 1 on the 1st of May 2025.",
        "tools": [
            EvalTool(name="ScheduleMaintenance", args=[EvalToolParam(key="device_id", value=1), EvalToolParam(key="date", value="2025-05-01")])
        ]
    },
    {
        "input": "Please tell me the last time device 0 was maintained.",
        "output": "The answer should tell the user the date of the last maintenance of device 0. The date is only required to include the year, month, and day, but not the time.",
        "tools": [
            EvalTool(name="GetLastMaintenanceDate", args=[EvalToolParam(key="device_id", value=0)])
        ]
    },
    {
        "input": "I had some handymen here a couple of weeks ago, but I cannot remember when exactly. I need to know the exact day when they were here, because I need to create a document for our filing system. All I know is that they took care of device 3 and there was no other maintenance done on it since.",
        "output": "The answer should tell the user the date of the last maintenance of device 3. The date is only required to include the year, month, and day, but not the time.",
        "tools": [
            EvalTool(name="GetLastMaintenanceDate", args=[EvalToolParam(key="device_id", value=3)])
        ]
    },

    ### Light Control Agent

    {
        "input": "Please turn on the lights in room 6",
        "output": "The answer should tell the user that the lights have successfully been turned on in room 6.",
        "tools": [
            EvalTool(name="TurnOnLights", args=[EvalToolParam(key="room_id", value=6)])
        ]
    },
    {
        "input": "The sun is going down and I can barely see anything here in room 2 with the lights turned off. Do something about it!",
        "output": "The answer should tell the user that the lights have successfully been turned on in room 2.",
        "tools": [
            EvalTool(name="TurnOnLights", args=[EvalToolParam(key="room_id", value=2)])
        ]
    },
    {
        "input": "Please turn off the lights in room 6",
        "output": "The answer should tell the user that the lights have successfully been turned off in room 6.",
        "tools": [
            EvalTool(name="TurnOffLights", args=[EvalToolParam(key="room_id", value=6)])
        ]
    },
    {
        "input": "The sun is finally coming out. I don't think we need lights anymore here in room 2 and should be saving some energy instead.",
        "output": "The answer should tell the user that the lights have successfully been turned off in room 2.",
        "tools": [
            EvalTool(name="TurnOffLights", args=[EvalToolParam(key="room_id", value=2)])
        ]
    },
    {
        "input": "Set the light intensity of room 4 to 70%.",
        "output": "The answer should tell the user that the light intensity has been set to 70% (or 0.7) in room 4.",
        "tools": [
            EvalTool(name="SetLightIntensity", args=[EvalToolParam(key="room_id", value=4), EvalToolParam(key="intensity", value=0.7)])
        ]
    },
    {
        "input": "I think it is possible to dim the lights in room 7, right? If so, could you please set them to 40% intensity?",
        "output": "The answer should tell the user that the light intensity has been set to 40% (or 0.4) in room 7.",
        "tools": [
            EvalTool(name="SetLightIntensity", args=[EvalToolParam(key="room_id", value=7), EvalToolParam(key="intensity", value=0.4)])
        ]
    },
    {
        "input": "Activate the emergency lights!",
        "output": "The answer should tell the user that the emergency lights have been activated.",
        "tools": [
            EvalTool(name="ActivateEmergencyLights")
        ]
    },
    {
        "input": "We have our yearly safety inspection in the office. In order for everything to be running smoothly and checking that the emergency system is working properly, we need to see if the emergency lights are functional. Call the necessary tool for that.",
        "output": "The answer should tell the user that the emergency lights have been activated.",
        "tools": [
            EvalTool(name="ActivateEmergencyLights")
        ]
    },

    ### Sensor Agent

    {
        "input": "What is the current temperature in room 3?",
        "output": "The answer should tell the user the current temperature in room 3 in Celsius.",
        "tools": [
            EvalTool(name="GetTemperature", args=[EvalToolParam(key="room_id", value=3)])
        ]
    },
    {
        "input": "I just turned on the heaters in room 7 something like 10 minutes ago. Can you tell me what the temperature is now?",
        "output": "The answer should tell the user the current temperature in room 7 in Celsius.",
        "tools": [
            EvalTool(name="GetTemperature", args=[EvalToolParam(key="room_id", value=7)])
        ]
    },
    {
        "input": "What is the co2 level in room 3?",
        "output": "The answer should tell the user the current co2 level in room 3 in ppm.",
        "tools": [
            EvalTool(name="GetCo2Level", args=[EvalToolParam(key="room_id", value=3)])
        ]
    },
    {
        "input": "There are currently a lot of people in room 2 and I need to know the current co2 level in that room, in order to determine whether we need to open the windows, although it is pretty cold outside and I don't want to...",
        "output": "The answer should tell the user the current co2 level in room 2 in ppm.",
        "tools": [
            EvalTool(name="GetCo2Level", args=[EvalToolParam(key="room_id", value=2)])
        ]
    },
    {
        "input": "What is the current humidity in room 3?",
        "output": "The answer should tell the user the current humidity level in room 3.",
        "tools": [
            EvalTool(name="GetHumidity", args=[EvalToolParam(key="room_id", value=3)])
        ]
    },
    {
        "input": "We had some problems with water in room 5 and I need to know whether the room is still too humid. Can you check for me?",
        "output": "The answer should tell the user the current humidity level in room 5.",
        "tools": [
            EvalTool(name="GetHumidity", args=[EvalToolParam(key="room_id", value=5)])
        ]
    },
    {
        "input": "What is the current noise level in room 8?",
        "output": "The answer should tell the user the current noise level in room 8 in decibel.",
        "tools": [
            EvalTool(name="GetNoise", args=[EvalToolParam(key="room_id", value=8)])
        ]
    },
    {
        "input": "So normally I am working in room 2 but there is a lot of noise in that room. Can you tell me what the noise level is?",
        "output": "The answer should tell the user the current noise level in room 2 in decibel.",
        "tools": [
            EvalTool(name="GetNoise", args=[EvalToolParam(key="room_id", value=2)])
        ]
    },
    {
        "input": "What is the battery level of the sensor in room 10?",
        "output": "The answer should tell the user the current battery level of the sensor in room 10 in percent.",
        "tools": [
            EvalTool(name="CheckSensorBattery", args=[EvalToolParam(key="room_id", value=10)])
        ]
    },
    {
        "input": "I haven't looked after the sensor in room 1 in quite a while and I fear that it might be out of power soon if I am not changing its battery soon. Can this be the case?",
        "output": "The answer should include the current battery level of the sensor in room 1 in percent.",
        "tools": [
            EvalTool(name="CheckSensorBattery", args=[EvalToolParam(key="room_id", value=1)])
        ]
    },
    {
        "input": "Can you give me all sensor information for the room 4?",
        "output": "The answer should include information about the sensor in room 4 for its temperature, co2 level, humidity, noise leve, and the sensor battery level.",
        "tools": [
            EvalTool(name="GetCompleteInfo", args=[EvalToolParam(key="room_id", value=4)])
        ]
    },
    {
        "input": "I am currently checking all available information that I can gather about room quality. Next would be room 2. Can you tell me what the temperature, co2 level, humidity, noise level, and the battery level are in the most efficient way?",
        "output": "The answer should include information about the sensor in room 2 for its temperature, co2 level, humidity, noise leve, and the sensor battery level.",
        "tools": [
            EvalTool(name="GetCompleteInfo", args=[EvalToolParam(key="room_id", value=2)])
        ]
    },

    ### Kitchen Agent

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
        "input": "I want to order something to eat, what are my options?",
        "output": "The answer should have retrieved a list of snacks. The full list of snacks should include 'chips', 'nuts', 'chocolate bar', 'gummy bears', 'apples', and 'ice'. Nothing should have been ordered yet.",
        "tools": [
            EvalTool(name="GetSnackInventory")
        ]
    },
    {
        "input": "I heard there are snacks available, but what snacks in particular?",
        "output": "The answer should have retrieved a list of snacks. The full list of snacks should include 'chips', 'nuts', 'chocolate bar', 'gummy bears', 'apples', and 'ice'. Nothing should have been ordered yet.",
        "tools": [
            EvalTool(name="GetSnackInventory")
        ]
    },
    {
        "input": "Order some 'chips' for me please.",
        "output": "The answer should confirm to the user that 'chips' have been ordered. It does not matter whether the answer includes the quantity or not.",
        "tools": [
            EvalTool(name="OrderSnack", args=[EvalToolParam(key="item", value="chips"), EvalToolParam(key="amount", value=1, optional=True)])
        ]
    },
    {
        "input": "I need to order something healthy, maybe some nuts that I can eat at my desk. Actually yes, some nuts would be great. Please do that for me! In any case, I only need one amount of it.",
        "output": "The answer should confirm to the user that 'nuts' have been ordered. The answer should include that only 1 amount of it has been ordered.",
        "tools": [
            EvalTool(name="OrderSnack", args=[EvalToolParam(key="item", value="nuts"), EvalToolParam(key="amount", value=1)])
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
        "input": "I think the kitchen hasn't been cleaned in quite a while. Everywhere are used plates, the dishwasher is clean but the stuff hasn't been taken out yet and even the windows should be cleaned as well. You know what? Can you schedule a cleaning day on the 1st of May 2025 so we don't forget to the clean kitchen? That would be awesome!",
        "output": "The answer should confirm that a cleaning day has been scheduled on the 1st of May 2025.",
        "tools": [
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-05-01")])
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
        "input": "",
        "output": "The answer should confirm that the fridge space with the id 62 was successfully rented for a duration of 2 days.",
        "tools": [
            EvalTool(name="ReserveFridgeSpace", args=[EvalToolParam(key="space_id", value=62), EvalToolParam(key="duration", value=2)])
        ]
    },
    {
        "input": "Get the fridge contents for all spaces. Only call a single tool once to achieve this task!",
        "output": "The answer should include a list of items that are currently stored in the fridge. This is the total list of items: 'sausage', 'chicken breast', 'ground meat', 'cucumber', 'salad', 'bell pepper', 'salami', 'bacon', 'liver sausage', 'gouda cheese', 'parmesan cheese', 'camembert', 'beer', 'mate', 'coca cola', 'butter', 'ketchup', 'mustard', 'olives', 'lasagne', 'eggs'.",
        "tools": [
            EvalTool(name="GetFridgeContents")
        ]
    },
    {
        "input": "Get the fridge contents for the space with the number 61 and tell me what is stored in there.",
        "output": "The answer should give a list of items stored in the fridge space with number 61, which include 'cucumber', 'salad', 'bell pepper'.",
        "tools": [
            EvalTool(name="GetFridgeContents", args=[EvalToolParam(key="space_id", value=61)])
        ]
    },
    {
        "input": "Can you tell me what space ids are available in the fridge?",
        "output": "The answer should return a list of numbers representing the space ids of the fridge. The list should include '60', '61', '62', '63', '64', '65', '66'.",
        "tools": [
            EvalTool(name="GetFridgeSpaceIds")
        ]
    },
    {
        "input": "At some point I would like to rent a fridge space, but I think I need to the proper numbers. Can you tell me what numbers I could use for that?",
        "output": "The answer should return a list of numbers representing the space ids of the fridge. The list should include '60', '61', '62', '63', '64', '65', '66'.",
        "tools": [
            EvalTool(name="GetFridgeSpaceIds")
        ]
    },
    {
        "input": "The dishwasher is once again not working... let someone know to fix this damn thing!",
        "output": "The answer should confirm is has reported a kitchen issue by calling the necessary action.",
        "tools": [
            EvalTool(name="ReportKitchenIssue", args=[EvalToolParam(key="issue_description", value="issue", match=EvalMatch.NONE)])
        ]
    },
    {
        "input": "Could you please report an issue in the kitchen, regarding a broken plate?",
        "output": "The answer should confirm is has reported a kitchen issue by calling the necessary action.",
        "tools": [
            EvalTool(name="ReportKitchenIssue", args=[EvalToolParam(key="issue_description", value="issue", match=EvalMatch.NONE)])
        ]
    },
    {
        "input": "Can you check the current status of the water filter?",
        "output": "The answer should tell the user, that it has checked the water filter status. Based on the status, which can be 'Clean', 'Slightly used', 'Dirty', or 'Dysfunctional'. If the status is 'Clean', the answer should tell the user that the water should be safe to drink. Otherwise, the answer should tell the user, that the water filter should be checked and changed and that the water might not be safe to drink.",
        "tools": [
            EvalTool(name="CheckWaterFilterStatus")
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
        "input": "I have made a grocery list earlier somewhere in here, but I cannot remember what I added to it. Please remind me!",
        "output": "The answer should have checked the current grocery list. This list includes: 'bread', 'tomato', 'pasta', 'water', 'juice'",
        "tools": [
            EvalTool(name="GetGroceryList")
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
        "input": "Hey you, add 'cornflakes' to my grocery list!",
        "output": "The answer should confirm to the user that 'cornflakes' were put on the grocery list.",
        "tools": [
            EvalTool(name="AddToGroceryList", args=[EvalToolParam(key="item", value="cornflakes")])
        ]
    },
    {
        "input": "When I'll be going to the store later, it is really important that I buy enough 'diapers' since I only have 2 left and tomorrow the stores are all closed. Make sure I don't forget!",
        "output": "The answer should confirm to the user that 'diapers' were put on the grocery list.",
        "tools": [
            EvalTool(name="AddToGroceryList", args=[EvalToolParam(key="item", value="diaper", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "Please remove 'bread' from my grocery list. I have decided I will be making my own instead.",
        "output": "The answer should confirm to the user that 'bread' was removed from the grocery list.",
        "tools": [
            EvalTool(name="RemoveFromGroceryList", args=[EvalToolParam(key="item", value="bread")])
        ]
    },
    {
        "input": "I think I added 'water' on my grocery list by mistake. Please remove it.",
        "output": "The answer should confirm to the user that 'water' was removed from the grocery list.",
        "tools": [
            EvalTool(name="RemoveFromGroceryList", args=[EvalToolParam(key="item", value="water")])
        ]
    },

    # Customer Agent

    {
        "input": "Make an order for 'teapot' with an amount of 3.",
        "output": "The answer should confirm that an order has been placed for 3 teapots. The id of the order should be given within the answer. The id will be given in the format 'id-123456', so the prefix 'id', then a hyphen, and finally a unique number.",
        "tools": [
            EvalTool(name="MakeOrder", args=[EvalToolParam(key="item", value="teapot", match=EvalMatch.PARTIAL), EvalToolParam(key="amount", value=3)])
        ]
    },
    {
        "input": "I've heard that you can help me with ordering items from the warehouse? I am currently repairing something in my house and I would need to order 5 'duct tapes' if that is possible. Can you do that for me?",
        "output": "The answer should confirm that an order has been placed for 5 duct tapes. The id of the order should be given within the answer. The id will be given in the format 'id-123456', so the prefix 'id', then a hyphen, and finally a unique number.",
        "tools": [
            EvalTool(name="MakeOrder", args=[EvalToolParam(key="item", value="duct", match=EvalMatch.PARTIAL), EvalToolParam(key="amount", value=5)])
        ]
    },
    {
        "input": "I need you to make multiple orders. I need to order a new sink and also 4 times a towel from the warehouse.",
        "output": "The answer should confirm that two orders has been placed for 1 sink and 4 towels. The ids of the orders should be given within the answer. The id will be given in the format 'id-123456', so the prefix 'id', then a hyphen, and finally a unique number.",
        "tools": [
            EvalTool(name="MakeOrders", args=[EvalToolParam(key="items", value=["sink", "towel"]), EvalToolParam(key="amounts", value=[1, 4])])
        ]
    },
    {
        "input": "I need you to create 3 orders, all regarding the same item. It is always just a single 'keyboard'. Only call one action to accomplish this task!",
        "output": "The answer should confirm that three orders have been created, each for 1 keyboard. The ids of the orders should be given within the answer. The id will be given in the format 'id-123456', so the prefix 'id', then a hyphen, and finally a unique number.",
        "tools": [
            EvalTool(name="MakeOrders", args=[EvalToolParam(key="items", value=["keyboard", "keyboard", "keyboard"]), EvalToolParam(key="amounts", value=[1, 1, 1])])
        ]
    },
    {
        "input": "Please give me the details for order 'id-457132'.",
        "output": "The answer should include details for the order with id 'id-457132', which includes the item 'blue paint' with amount 1.",
        "tools": [
            EvalTool(name="GetOrder", args=[EvalToolParam(key="order_id", value="id-457132")])
        ]
    },
    {
        "input": "A customer called me and wanted to confirm something. Apparently he wanted to order 4 chairs and he isn't sure if he typed in 4 or 7 chairs (he used the numpad for that apparently). Anyway, his order id is 'id-457134'. Could you maybe check that the order is correct and contains the required amount?",
        "output": "The answer should include details for the order with id 'id-457134', which includes the item 'chair' with amount 4, which is the required amount the user has asked about.",
        "tools": [
            EvalTool(name="GetOrder", args=[EvalToolParam(key="order_id", value="id-457134")])
        ]
    },
    {
        "input": "Please get all order within our system.",
        "output": "The answer should include an overview of all orders in the system. It should list at least 4 orders, but there could also be more.",
        "tools": [
            EvalTool(name="GetAllOrders")
        ]
    },
    {
        "input": "I need to check something within our ordering system. For this, it would be really great if you could tell me what orders are currently in the system.",
        "output": "The answer should include an overview of all orders in the system. It should list at least 4 orders, but there could also be more.",
        "tools": [
            EvalTool(name="GetAllOrders")
        ]
    },
    {
        "input": "I need you to cancel order 'id-457132'.",
        "output": "The answer should confirm that the order with id 'id-457132' has been cancelled.",
        "tools": [
            EvalTool(name="CancelOrder", args=[EvalToolParam(key="order_id", value="id-457132")])
        ]
    },
    {
        "input": "I just got a call from one of our customers. He made the order 'id-457134'. Apparently, he had his cat running across his keyboard when he was just before the checkout and the wrong address was entered. Anyway, I already made a new order, but there is still the old order which needs to be cancelled. Do this for me.",
        "output": "The answer should confirm that the order with id 'id-457132' has been cancelled.",
        "tools": [
            EvalTool(name="CancelOrder", args=[EvalToolParam(key="order_id", value="id-457134")])
        ]
    },
    {
        "input": "I have created the order with id 'id-457301' with item 'hairdryer' and amount 2. I need you to add the order into our system.",
        "output": "The answer should confirm that an order with id 'id-457301', item 'hairdryer' and amount 2 has been added to the system.",
        "tools": [
            EvalTool(name="AddOrder", args=[EvalToolParam(key="order", value={"order_id": "id-457301", "item": "hairdryer", "amount": 2})])
        ]
    },
    {
        "input": "Somehow we had a problem with our automatic ordering system and now I need you to fix this. Somehow, an order got created but it was not added to our system properly. One order that was effected is order 'id-457302', concerning three times the item 'pillow'.",
        "output": "The answer should confirm that an order with id 'id-457302', item 'pillow' and amount 3 has been added to the system.",
        "tools": [
            EvalTool(name="AddOrder", args=[EvalToolParam(key="order", value={"order_id": "id-457302", "item": "pillow", "amount": 3})])
        ]
    },
    {
        "input": "I have multiple order that should be added into the system: 1. id: 'id-457303', item: 'industrial glue', amount: 2    2. id: 'id-457304', item: 'pumpkin seeds', amount: 5     3. id: 'id-457305', item: 'water', amount: 10",
        "output": "The answer should confirm that all three orders with the ids 'id-457303', 'id-457304' and 'id-457305' have been added to the system.",
        "tools": [
            EvalTool(name="AddOrders", args=[EvalToolParam(key="orders", value=[{"order_id": "id-457303", "item": "industrial glue", "amount": 2}, {"order_id": "id-457304", "item": "pumpkin seeds", "amount": 5}, {"order_id": "id-457305", "item": "water", "amount": 10}])])
        ]
    },
    {
        "input": "There was some sort of corruption happening in our system and now we need to reorganize all the orders manually. They still exist, but somehow require a readding. Please do that for me. The effected orders are: 1. id: 'id-457306', item: 'industrial glue', amount: 2    2. id: 'id-457307', item: 'pumpkin seeds', amount: 5     3. id: 'id-457308', item: 'water', amount: 10       I want you to only call one tool for this task.",
        "output": "The answer should confirm that all three orders with the ids 'id-457306', 'id-457307' and 'id-457308' have been added to the system.",
        "tools": [
            EvalTool(name="AddOrders", args=[EvalToolParam(key="orders", value=[{"order_id": "id-457306", "item": "industrial glue", "amount": 2}, {"order_id": "id-457307", "item": "pumpkin seeds", "amount": 5}, {"order_id": "id-457308", "item": "water", "amount": 10}])])
        ]
    },

    ### Logistics Robot Agent

    {
        "input": "Can you tell me, where our first logistics robot is currently located?",
        "output": "The answer should tell the user that Logistics Robot 1 is located in 'zone-A'.",
        "tools": [
            EvalTool(name="GetZone")
        ]
    },
    {
        "input": "The warehouse has gotten really big and now all of a sudden robot 1 has a malfunction and is not moving. I need to know where it is so I can drive there and repair this thing... once again.",
        "output": "The answer should tell the user that Logistics Robot 1 is located in 'zone-A'.",
        "tools": [
            EvalTool(name="GetZone")
        ]
    },
    {
        "input": "I need the second robot to move to zone B",
        "output": "The answer should tell the user that Logistics Robot 2 has moved to zone B.",
        "tools": [
            EvalTool(name="MoveToLocation", args=[EvalToolParam(key="zone", value="B", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "The only robot I should be commanding right now is robot 2. Now it is necessary for the robot, in order to fulfill its current task, to be relocated to zone C, where all the necessary items are that it should be picking up, but we can deal with that once the robot is there. Make sure the robot is moved.",
        "output": "The answer should tell the user that Logistics Robot 2 has moved to zone C.",
        "tools": [
            EvalTool(name="MoveToLocation", args=[EvalToolParam(key="zone", value="C", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "Can you tell me what robot 1 is currently carrying?",
        "output": "The answer should tell the user that Logistics Robot 1 is carrying a 'ball', 'shovel', and 'towel'.",
        "tools": [
            EvalTool(name="GetInventory")
        ]
    },
    {
        "input": "I just gave the first robot a command to pickup some stuff. I just want to make sure it is doing what it is supposed to do. Can you please tell me what it is carrying?",
        "output": "The answer should tell the user that Logistics Robot 1 is carrying a 'ball', 'shovel', and 'towel'.",
        "tools": [
            EvalTool(name="GetInventory")
        ]
    },
    {
        "input": "I need robot number 3 to pickup a 'broom'. It should already be in the right zone, so you don't need to worry about this.",
        "output": "The answer should tell the user that Logistics Robot 3 has successfully picked up the item 'broom'.",
        "tools": [
            EvalTool(name="PickupItem", args=[EvalToolParam(key="item", value="broom")])
        ]
    },
    {
        "input": "Alright, after some attempts, logistics robot 3 is finally in the right spot. Now it can continue with its task. I want you to help me with that. Its next task is to pickup a 'vacuum-cleaner'.",
        "output": "The answer should tell the user that Logistics Robot 3 has successfully picked up the item 'vacuum-cleaner'.",
        "tools": [
            EvalTool(name="PickupItem", args=[EvalToolParam(key="item", value="vacuum-cleaner")])
        ]
    },
    {
        "input": "Please make logistics robot 3 drop the item 'ball' to where it is currently standing.",
        "output": "The answer should tell the user that Logistics Robot 3 has successfully dropped the item 'ball'.",
        "tools": [
            EvalTool(name="DropItem", args=[EvalToolParam(key="item", value="ball")])
        ]
    },
    {
        "input": "Alright, I have navigated robot 3 where it needs to be. Next task is to drop an item. The item in question, which should also be in the robots inventory, so you don't need to check that, is the item 'shovel'. It can be dropped directly in the current zone of the robot.",
        "output": "The answer should tell the user that Logistics Robot 3 has successfully dropped the item 'ball'.",
        "tools": [
            EvalTool(name="DropItem", args=[EvalToolParam(key="item", value="shovel")])
        ]
    },

    ### Manager Agent

    {
        "input": "Get me the name of the warehouse.",
        "output": "The answer should tell the user that the name of the warehouse is 'Super Awesome Warehouse'.",
        "tools": [
            EvalTool(name="GetWarehouseName")
        ]
    },
    {
        "input": "I heard that you provide functions regarding a warehouse. That is pretty cool in my opinion. First things first, so I know that this is actually real. What is its name?",
        "output": "The answer should tell the user that the name of the warehouse is 'Super Awesome Warehouse'.",
        "tools": [
            EvalTool(name="GetWarehouseName")
        ]
    },
    {
        "input": "Where is the warehouse located?",
        "output": "The answer should tell the user that the warehouse is located at 'Industrial Street 1'.",
        "tools": [
            EvalTool(name="GetWarehouseAddress")
        ]
    },
    {
        "input": "Tomorrow I have to go to the warehouse for the first time. I think I have written down the address correct but I just want to confirm with you.",
        "output": "The answer should tell the user that the warehouse is located at 'Industrial Street 1'.",
        "tools": [
            EvalTool(name="GetWarehouseAddress")
        ]
    },
    {
        "input": "Who is the owner of the warehouse?",
        "output": "The answer should tell the user that the owner of the warehouse is 'John Warehouse'.",
        "tools": [
            EvalTool(name="GetWarehouseOwner")
        ]
    },
    {
        "input": "I was just at the warehouse and met the owner there very briefly. I am curios to learn more about him. Do you know how he is called, so I might be able to search him up on the internet?",
        "output": "The answer should tell the user that the owner of the warehouse is 'John Warehouse'.",
        "tools": [
            EvalTool(name="GetWarehouseOwner")
        ]
    },
    {
        "input": "What is the email address of the warehouse?",
        "output": "The answer should tell the user that the email address of the warehous eis 'Warehouse@mail.com'.",
        "tools": [
            EvalTool(name="GetWarehouseEmail")
        ]
    },
    {
        "input": "I was supposed to write to this warehouse about a job offering? But I was unable to find the mail address of the warehouse for some reason. So I thought, hey, maybe you can help me out with that!",
        "output": "The answer should tell the user that the email address of the warehous eis 'Warehouse@mail.com'.",
        "tools": [
            EvalTool(name="GetWarehouseEmail")
        ]
    },
    {
        "input": "What is the total size of the warehouse?",
        "output": "The answer should tell the user that the total size of the warehouse is 5000 square meters.",
        "tools": [
            EvalTool(name="GetWarehouseAreaSize")
        ]
    },
    {
        "input": "I was looking over warehouse to buy for my company and I stumbled over yours. One important factor for me is the total size that would be available, since I need a lot of room. So tell me, I think you know this, what is the size of the warehouse?",
        "output": "The answer should tell the user that the total size of the warehouse is 5000 square meters.",
        "tools": [
            EvalTool(name="GetWarehouseAreaSize")
        ]
    },
    {
        "input": "Can you tell me the sizes of each zone in the warehouse?",
        "output": "The answer should give an overview of the different zones and their sizes in square meters. These are the zones: - zone-A: 2000, - zone-B: 1000, - zone-C: 750, - zone-D: 750, - zone_E: 500.",
        "tools": [
            EvalTool(name="GetWarehouseZoneSizes")
        ]
    },
    {
        "input": "I've heard that you know your way around the warehouse. I was just visiting there and apparently there were multiple areas, but they seemed to have a different size. Is there any way you can provide me with the sizes of each of those areas?",
        "output": "The answer should give an overview of the different zones and their sizes in square meters. These are the zones: - zone-A: 2000, - zone-B: 1000, - zone-C: 750, - zone-D: 750, - zone_E: 500.",
        "tools": [
            EvalTool(name="GetWarehouseZoneSizes")
        ]
    },
    {
        "input": "Please tell me the size of zone A",
        "output": "The answer should tell the user that the size of zone A is 2000 square meters.",
        "tools": [
            EvalTool(name="GetWarehouseZoneSize", args=[EvalToolParam(key="zone", value="A", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "In the last warehouse I worked, our largest area was 'only' 1000 square meters big. Now I am in this new warehouse and I think the biggest zone is even bigger than my old one. Also, I believe the biggest zone is called zone-A. How big is that zone in total?",
        "output": "The answer should tell the user that the size of zone A is 2000 square meters.",
        "tools": [
            EvalTool(name="GetWarehouseZoneSize", args=[EvalToolParam(key="zone", value="A", match=EvalMatch.PARTIAL)])
        ]
    },

    # Warehouse Agent

    {
        "input": "I need to know where the item 'shelf' is located in the warehouse.",
        "output": "The answer should tell the user that the item 'shelf' can be found in zone-A.",
        "tools": [
            EvalTool(name="GetItemLocation", args=[EvalToolParam(key="item", value="shelf")])
        ]
    },
    {
        "input": "Man this warehouse is big. And the only thing I want is a new 'towel'. There is no way I search each zone for that, I would be here forever. Also, I think there are no employees here, so that's why I ask you for help with that.",
        "output": "The answer should tell the user that the item 'towel' can be found in zone-E.",
        "tools": [
            EvalTool(name="GetItemLocation", args=[EvalToolParam(key="item", value="towel")])
        ]
    },
    {
        "input": "Give me the inventory of zone B.",
        "output": "The answer should tell the user that following items can be found in zone-B: - 'box', 'wrap', 'tape', 'rope', 'strap'.",
        "tools": [
            EvalTool(name="GetInventory", args=[EvalToolParam(key="zone", value="B", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "I am currently doing a scheduled inventory for our warehouse and I need to know what items are located where. I think you can help me with that. Next thing I need to know, is what items are located in the zone with letter 'E'.",
        "output": "The answer should tell the user that following items can be found in zone-E: - 'toilet', 'sink', 'shower', 'curtain', 'towel'.",
        "tools": [
            EvalTool(name="GetInventory", args=[EvalToolParam(key="zone", value="E", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "Give me the list of zones that exist in the warehouse.",
        "output": "The answer should tell the user that the following zones exist in the warehouse: - zone-A, - zone-B, - zone-C, - zone-D, - zone_E.",
        "tools": [
            EvalTool(name="GetZones")
        ]
    },
    {
        "input": "I am new in the warehouse and I still don't know my way around, especially with the names of the areas or zones I belive are they called here. Can you tell me which exist?",
        "output": "The answer should tell the user that the following zones exist in the warehouse: - zone-A, - zone-B, - zone-C, - zone-D, - zone_E.",
        "tools": [
            EvalTool(name="GetZones")
        ]
    },
    {
        "input": "Please add the item 'cement' to zone-A.",
        "output": "The answer should confirm that the item 'cement' has been added to zone-A.",
        "tools": [
            EvalTool(name="AddItemToZone", args=[EvalToolParam(key="item", value="cement"), EvalToolParam(key="zone", value="A", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "There was a new delivery of a product that I need to store in the warehouse and keep track of it. I think the best location for it would be in zone c. Please make sure the item 'hdmi cables' is properly added so we know where it is.",
        "output": "The answer should inform the user that the item 'hdmi cables' has been added to zone-C.",
        "tools": [
            EvalTool(name="AddItemToZone", args=[EvalToolParam(key="item", value="hdmi cable", match=EvalMatch.PARTIAL), EvalToolParam(key="zone", value="C", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "I need you to remove the item 'dustpan' from zone-D.",
        "output": "The answer should inform the user that the item 'dustpan' has been removed from zone-D.",
        "tools": [
            EvalTool(name="RemoveItemFromZone", args=[EvalToolParam(key="item", value="dustpan", match=EvalMatch.PARTIAL), EvalToolParam(key="zone", value="D", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "I just sold the last bit of the item 'mop' that was left in my warehouse. Make sure my inventory management is updated by calling the necessary action for that. The item was located in zone-D.",
        "output": "The answer should inform the user that the item 'mop' has been removed from zone-D.",
        "tools": [
            EvalTool(name="RemoveItemFromZone", args=[EvalToolParam(key="item", value="mop", match=EvalMatch.PARTIAL), EvalToolParam(key="zone", value="D", match=EvalMatch.PARTIAL)])
        ]
    },

    ### Music Player Agent

    {
        "input": "Please start playing the track 7.",
        "output": "The answer should confirm to the user, that the track with id 7 is now currently playing.",
        "tools": [
            EvalTool(name="PlayTrack", args=[EvalToolParam(key="track_id", value=7)])
        ]
    },
    {
        "input": "Resume the song",
        "output": "The answer should confirm to the user, that the track with id 7 is now currently playing.",
        "tools": [
            EvalTool(name="PlayTrack")
        ]
    },
    {
        "input": "Pause the current track.",
        "output": "The answer should inform the user, that the music has been paused.",
        "tools": [
            EvalTool(name="PauseTrack")
        ]
    },
    {
        "input": "I've had enough of the currently playing song and I want to have some silence for a minute.",
        "output": "The answer should inform the user, that the music has been paused.",
        "tools": [
            EvalTool(name="PauseTrack")
        ]
    },
    {
        "input": "Please skip to the next song.",
        "output": "The answer should inform the user, that the next song is now playing.",
        "tools": [
            EvalTool(name="SkipToNextTrack")
        ]
    },
    {
        "input": "Oh I don't like the current song, I would rather hear the next instead. Make it happen.",
        "output": "The answer should inform the user, that the next song is now playing.",
        "tools": [
            EvalTool(name="SkipToNextTrack")
        ]
    },
    {
        "input": "Please make the previous song play again.",
        "output": "The answer should inform the user, that the previous song is now playing again.",
        "tools": [
            EvalTool(name="SkipToPreviousTrack")
        ]
    },
    {
        "input": "I really liked the last song. Can you make it play again?",
        "output": "The answer should inform the user, that the previous song is now playing again.",
        "tools": [
            EvalTool(name="SkipToPreviousTrack")
        ]
    },
    {
        "input": "What is the current volume?",
        "output": "The answer should inform the user about the current volume level, which can range from 0 to 10.",
        "tools": [
            EvalTool(name="GetCurrentVolume")
        ]
    },
    {
        "input": "Is the music playing too loud? Not sure but can you check what the current configuration is?",
        "output": "The answer should inform the user about the current volume level of the music, which can range from 0 to 10.",
        "tools": [
            EvalTool(name="GetCurrentVolume")
        ]
    },
    {
        "input": "I want you to increase the volume.",
        "output": "The answer should inform the user that the volume level has been increased and provide the new volume level, which can range from 0 to 10.",
        "tools": [
            EvalTool(name="IncreaseVolume")
        ]
    },
    {
        "input": "Oh I really like the current song. Make it louder!",
        "output": "The answer should inform the user that the volume level has been increased and provide the new volume level, which can range from 0 to 10.",
        "tools": [
            EvalTool(name="IncreaseVolume")
        ]
    },
    {
        "input": "Please decrease the volume.",
        "output": "The answer should inform the user that the volume level has been decreased and provide the new volume level, which can range from 0 to 10.",
        "tools": [
            EvalTool(name="DecreaseVolume")
        ]
    },
    {
        "input": "Now the music is playing a little bit to loud. Can you lower it just a bit?",
        "output": "The answer should inform the user that the volume level has been decreased and provide the new volume level, which can range from 0 to 10.",
        "tools": [
            EvalTool(name="DecreaseVolume")
        ]
    },
    {
        "input": "I want you to change the volume setting to 5.",
        "output": "The answer should inform the user that the volume level has been changed to 5.",
        "tools": [
            EvalTool(name="AdjustVolume", args=[EvalToolParam(key="volume", value=5)])
        ]
    },
    {
        "input": "I need to tone down the music quite a bit. I think a new value of 3 should be suitable.",
        "output": "The answer should confirm that the current volume level has been set to 3.",
        "tools": [
            EvalTool(name="AdjustVolume", args=[EvalToolParam(key="volume", value=3)])
        ]
    },
    {
        "input": "Please mute the music.",
        "output": "The answer should confirm that the music has now been muted.",
        "tools": [
            EvalTool(name="Mute")
        ]
    },
    {
        "input": "Hold on, somebody is talking to me. Silence the music for a moment.",
        "output": "The answer should confirm that the music has now been muted.",
        "tools": [
            EvalTool(name="Mute")
        ]
    },
    {
        "input": "Get me all the track ids.",
        "output": "The answer should include a list of all track ids, which is a list of all numbers from 0 to 9.",
        "tools": [
            EvalTool(name="GetTrackIds")
        ]
    },
    {
        "input": "I think for some of your actions ids are quite important, including for interaction with my music. Which ids can I use if I want to play some songs for example?",
        "output": "The answer should include a list of all track ids, which is a list of all numbers from 0 to 9.",
        "tools": [
            EvalTool(name="GetTrackIds")
        ]
    },
    {
        "input": "Please tell me all the track names that you know.",
        "output": "The answer should include a list of all track names, which are: 'Echoes in the Rain', 'Starlight Serenade', 'Midnight Mirage', 'Crimson Horizon', 'Whispers of the Wind', 'Neon Dreams', 'Solace in the Shadows', 'Golden Skies', 'Rhythm of the Heartbeat', 'Aurora's Embrace'.",
        "tools": [
            EvalTool(name="GetTracks")
        ]
    },
    {
        "input": "I am curios about the song names you provide. Because I would really like to know what is included. Can you help me out with that?",
        "output": "The answer should include a list of all track names, which are: 'Echoes in the Rain', 'Starlight Serenade', 'Midnight Mirage', 'Crimson Horizon', 'Whispers of the Wind', 'Neon Dreams', 'Solace in the Shadows', 'Golden Skies', 'Rhythm of the Heartbeat', 'Aurora's Embrace'.",
        "tools": [
            EvalTool(name="GetTracks")
        ]
    },
    {
        "input": "Get the id of the track 'Crimson Horizon'.",
        "output": "The answer should return the id of the track 'Crimson Horizon' which is 3.",
        "tools": [
            EvalTool(name="GetIdByTrack", args=[EvalToolParam(key="track", value="crimson", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "I think for some of your actions regarding music I need the ids of specific songs. One song that I am curious about is called Aurora's Embrace. Can you tell me the id of that song?",
        "output": "The answer should return the id of the track Aurora's Embrace which is 9.",
        "tools": [
            EvalTool(name="GetIdByTrack", args=[EvalToolParam(key="track", value="aurora", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "Get me the name of the track with id 7.",
        "output": "The answer should return the name of the track with id 7, which is 'Golden Skies'.",
        "tools": [
            EvalTool(name="GetTrackById", args=[EvalToolParam(key="track_id", value=7)])
        ]
    },
    {
        "input": "Hey, I know that you use ids for songs but sometimes I would also like to know their actual names. Can you tell what song 4 is called?",
        "output": "The answer should return the name of the track with id 7, which is 'Whispers of the Wind'.",
        "tools": [
            EvalTool(name="GetTrackById", args=[EvalToolParam(key="track_id", value=4)])
        ]
    },

    ### Playlist Management Agent

    {
        "input": "Please create the playlist called 'My Favorite Songs'.",
        "output": "The answer should confirm that the playlist 'My Favorite Songs' has been created.",
        "tools": [
            EvalTool(name="CreatePlaylist", args=[EvalToolParam(key="playlist_name", value="Favorite Songs", match=EvalMatch.PARTIAL)])
        ]
    },
    {
        "input": "I want you to create the playlist called 'My Favorite Songs' and in there should be the songs 'Whispers in the Static', 'Velvet Skies and Broken Dreams', 'Echoes of Tomorrow', 'Crimson Horizon', and 'Dancing with Shadows'.",
        "output": "The answer should confirm that the playlist 'My Favorite Songs' has been created and the songs 'Whispers in the Static', 'Velvet Skies and Broken Dreams', 'Echoes of Tomorrow', 'Crimson Horizon', and 'Dancing with Shadows' have been added to the playlist.",
        "tools": [
            EvalTool(name="CreatePlaylist", args=[EvalToolParam(key="playlist_name", value="Favorite Songs", match=EvalMatch.PARTIAL), EvalToolParam(key="songs", value=['Whispers in the Static', 'Velvet Skies and Broken Dreams', 'Echoes of Tomorrow', 'Crimson Horizon', 'Dancing with Shadows'])]),
        ]
    },
    {
        "input": "I want you to create multiple playlists for me called 'Coffee & Cloudbursts', 'Wanderlust Tapes', and 'Fragments of a Forgotten Summer'.",
        "output": "The answer should confirm that the playlists 'Coffee & Cloudbursts', 'Wanderlust Tapes', and 'Fragments of a Forgotten Summer' have successfully been created. The answer should also include a list of the created playlist ids.",
        "tools": [
            EvalTool(name="CreateMultiplePlaylists", args=[EvalToolParam(key="playlist_names", value=['Coffee & Cloudbursts', 'Wanderlust Tapes', 'Fragments of a Forgotten Summer'])]),
        ]
    },
    {
        "input": "I want you to create multiple playlists for me called 'Coffee & Cloudbursts', 'Wanderlust Tapes', and 'Fragments of a Forgotten Summer'. Fill the first playlist with the songs 'Whispers in the Static' and 'Velvet Skies and Broken Dreams', the second playlist with 'Echoes of Tomorrow' and 'Crimson Horizon', and the third playlist with just 'Dancing with Shadows'.",
        "output": "The answer should confirm that the playlists 'Coffee & Cloudbursts', 'Wanderlust Tapes', and 'Fragments of a Forgotten Summer' have successfully been created. The answer should also include a list of the created playlist ids.",
        "tools": [
            EvalTool(name="CreateMultiplePlaylists", args=[EvalToolParam(key="playlist_names", value=['Coffee & Cloudbursts', 'Wanderlust Tapes', 'Fragments of a Forgotten Summer']), EvalToolParam(key="playlist_songs", value=[['Whispers in the Static', 'Velvet Skies and Broken Dreams'], ['Echoes of Tomorrow', 'Crimson Horizon'], ['Dancing with Shadows']])]),
        ]
    },
    {
        "input": "Please add the song 'Whispers in the Static' to the playlist with id 46.",
        "output": "The answer should confirm that the song 'Whispers in the Static' has been successfully added to the playlist with id 46.",
        "tools": [
            EvalTool(name="AddSongToPlaylist", args=[EvalToolParam(key="playlist_id", value=46), EvalToolParam(key="song_name", value="Whispers in the Static")]),
        ]
    },
    {
        "input": "I have found this cool new song called 'Echoes of Tomorrow'. I definitely want to save that song for later, but not sure to which playlist I want to add it right now. You know what? Just add it to the playlist with id 46 for now.",
        "output": "The answer should confirm that the song 'Echoes of Tomorrow' has been successfully added to the playlist with id 46.",
        "tools": [
            EvalTool(name="AddSongToPlaylist", args=[EvalToolParam(key="playlist_id", value=46), EvalToolParam(key="song_name", value="Echoes of Tomorrow")]),
        ]
    },
    {
        "input": "Rename playlist 46 to 'New Hits 2025' for me.",
        "output": "The answer should confirm that the playlist with id 46 has been renamed to 'New Hits 2025'.",
        "tools": [
            EvalTool(name="RenamePlaylist", args=[EvalToolParam(key="playlist_id", value=46), EvalToolParam(key="new_name", value="New Hits 2025")]),
        ]
    },
    {
        "input": "I wasn't quite sure how to name playlist 46 yet, but after adding some songs to it, I am certain that the new name should be 'New Hits 2025'.",
        "output": "The answer should confirm that the playlist with id 46 has been renamed to 'New Hits 2025'.",
        "tools": [
            EvalTool(name="RenamePlaylist", args=[EvalToolParam(key="playlist_id", value=46), EvalToolParam(key="new_name", value="New Hits 2025")]),
        ]
    },
    {
        "input": "Get me all the names of the playlists.",
        "output": "The answer should return a list of all playlist names, which have to include at least 'Oblivion Soundtrack' and 'Minecraft Soundtrack'. The answer is allowed to contain more than those playlist names.",
        "tools": [
            EvalTool(name="GetPlaylistNames"),
        ]
    },
    {
        "input": "I am wondering what the names of all the playlists are, I don't really care for the ids to be honest.",
        "output": "The answer should return a list of all playlist names, which have to include at least 'Oblivion Soundtrack' and 'Minecraft Soundtrack'. The answer is allowed to contain more than those playlist names.",
        "tools": [
            EvalTool(name="GetPlaylistNames"),
        ]
    },
    {
        "input": "Tell me the song names of the playlist with id 42.",
        "output": "The answer should return a list of all song names of the playlist 42, which include: 'Through the Valleys', 'Harvest Dawn', 'King and Country', 'Wings of Kynareth', 'Glory of Cyrodiil'",
        "tools": [
            EvalTool(name="GetPlaylistSongs", args=[EvalToolParam(key="playlist_id", value=42)]),
        ]
    },
    {
        "input": "I am wondering what songs are included in playlist 42, I heard the playlist now a couple of times, but the songs don't have any vocals so it is hard to know what their names are.",
        "output": "The answer should return a list of all song names of the playlist 42, which include: 'Through the Valleys', 'Harvest Dawn', 'King and Country', 'Wings of Kynareth', 'Glory of Cyrodiil'",
        "tools": [
            EvalTool(name="GetPlaylistSongs", args=[EvalToolParam(key="playlist_id", value=42)]),
        ]
    },
    {
        "input": "Give me an overview of all the playlists you have access to.",
        "output": "The answer should include a detailed overview of all the playlist names and their songs. The answer will include multiple playlists, but should at least include the playlist names 'Oblivion Soundtrack' and 'Minecraft Soundtrack'.",
        "tools": [
            EvalTool(name="GetPlaylists"),
        ]
    },
    {
        "input": "I am new here and I heard that you give access to some sort of playlist management? I believe you already have some playlists saved. Could you tell me what they are and what songs are in them?",
        "output": "The answer should include a detailed overview of all the playlist names and their songs. The answer will include multiple playlists, but should at least include the playlist names 'Oblivion Soundtrack' and 'Minecraft Soundtrack'.",
        "tools": [
            EvalTool(name="GetPlaylists"),
        ]
    },
    {
        "input": "Get me the id of the playlist with name 'Oblivion Soundtrack'.",
        "output": "The answer should return the id of the playlist with the name 'Oblivion Soundtrack', which is 42.",
        "tools": [
            EvalTool(name="GetPlaylistId", args=[EvalToolParam(key="playlist_name", value="Oblivion Soundtrack")]),
        ]
    },
    {
        "input": "I think for some of your functionalities it is important to the ids of playlists. Anyway, I would like to modify a playlist. The playlist in question is called 'Oblivion Soundtrack'. Give me some unique number or whatever you have associated with that playlist.",
        "output": "The answer should return the id of the playlist with the name 'Oblivion Soundtrack', which is 42.",
        "tools": [
            EvalTool(name="GetPlaylistId", args=[EvalToolParam(key="playlist_name", value="Oblivion Soundtrack")]),
        ]
    },
    {
        "input": "Remove song 'Haggstorm' from playlist with id 43",
        "output": "The answer should confirm that the song 'Haggstorm' has been removed from the playlist with id 43.",
        "tools": [
            EvalTool(name="RemoveSongFromPlaylist", args=[EvalToolParam(key="playlist_id", value=43), EvalToolParam(key="song_name", value="Haggstorm")]),
        ]
    },
    {
        "input": "I accidentally added the song Sweden to the playlist with id 43. Is it possible that you remove it?",
        "output": "The answer should confirm that the song 'Sweden' has been removed from the playlist with id 43.",
        "tools": [
            EvalTool(name="RemoveSongFromPlaylist", args=[EvalToolParam(key="playlist_id", value=43), EvalToolParam(key="song_name", value="Sweden")]),
        ]
    },
    {
        "input": "Please delete the playlist with id 44 for me.",
        "output": "The answer should confirm that the playlist with id 44 has been deleted.",
        "tools": [
            EvalTool(name="DeletePlaylist", args=[EvalToolParam(key="playlist_id", value=44)]),
        ]
    },
    {
        "input": "I created this one playlist, don't remember the name, but the id is 45, where I just saved some songs for later. I have added them all to other playlists now and I would like to delete the old playlist. Please do that for me.",
        "output": "The answer should confirm that the playlist with id 45 has been deleted.",
        "tools": [
            EvalTool(name="DeletePlaylist", args=[EvalToolParam(key="playlist_id", value=45)]),
        ]
    },

    ### Social Agent

    {
        "input": "Please follow the artist 'Luna Vesper' for me.",
        "output": "The answer should confirm that the artist 'Luna Vesper' is now being followed.",
        "tools": [
            EvalTool(name="FollowArtist", args=[EvalToolParam(key="artist", value="Luna Vesper")]),
        ]
    },
    {
        "input": "I have found this interesting sounding new band called 'The Hollow Keys'. Please follow them on my social.",
        "output": "The answer should confirm that the band 'The Hollow Keys' is now being followed.",
        "tools": [
            EvalTool(name="FollowArtist", args=[EvalToolParam(key="artist", value="The Hollow Keys")]),
        ]
    },
    {
        "input": "Please unfollow the artist 'Nova Rook'.",
        "output": "The answer should confirm that the artist 'Nova Rook' has been unfollowed.",
        "tools": [
            EvalTool(name="UnfollowArtist", args=[EvalToolParam(key="artist", value="Nova Rook")]),
        ]
    },
    {
        "input": "The latest stuff being released by Echofield is not really that good anymore. I want to unfollow them.",
        "output": "The answer should confirm that the artist 'Echofield' has been unfollowed.",
        "tools": [
            EvalTool(name="UnfollowArtist", args=[EvalToolParam(key="artist", value="Echofield")]),
        ]
    },
    {
        "input": "Please like the track 'Heartbeats' for me.",
        "output": "The answer should confirm that the track 'Heartbeats' has been liked.",
        "tools": [
            EvalTool(name="LikeTrack", args=[EvalToolParam(key="track", value="Heartbeats")]),
        ]
    },
    {
        "input": "I just heard the track 'Azure Nights' and I think it is pretty good. Like it for me.",
        "output": "The answer should confirm that the track 'Azure Nights' has been liked.",
        "tools": [
            EvalTool(name="LikeTrack", args=[EvalToolParam(key="track", value="Azure Nights")]),
        ]
    },
]
