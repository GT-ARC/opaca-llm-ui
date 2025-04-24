#                                                                                   #
#   This file defines complex questions to test the performance of the OPACA LLM.   #
#   The questions should invoke multiple actions, some of which depend on each      #
#   other. There might also be questions which are not serviceable by the testing   #
#   environment.                                                                    #
#                                                                                   #
#   The current testing environment which should deployed on the OPACA Platform:    #
#   - rkader2811/smart-office                                                       #
#   - rkader2811/warehouse                                                          #
#   - rkader2811/music-platform                                                     #
#   - rkader2811/calculator                                                         #
#                                                                                   #
from models import EvalTool, EvalToolParam, EvalMatch


complex_questions = [
    {
        "input": "What is the highest room id in the system and what is the name belonging to that id?",
        "output": "The highest room id is 100 and the name of that room is 'VIP Room'.",
        "tools": [
            EvalTool(name="GetRooms", id=0, alternatives=[[1, 2]]),
            EvalTool(name="GetRoomIds", id=1, alternatives=[[0]]),
            EvalTool(name="GetRoomName", id=2, args=[EvalToolParam(key="room_id", value=100)], alternatives=[[0]])
        ]
    },
    {
        "input": "Turn on the lights in every bathroom.",
        "output": "The answer should indicate that the lights were turned on the rooms 'Bathroom Women', 'Bathroom Men', and 'Bathroom Uni'. The ids of those rooms are 9, 10, 11 respectively.",
        "tools": [
            EvalTool(name="GetRooms", id=0, alternatives=[[1, 2, 3, 4]]),
            EvalTool(name="GetRoomNames", id=1, alternatives=[[0]]),
            EvalTool(name="GetRoomId", id=2, alternatives=[[0]], args=[EvalToolParam(key="room_name", value="Women", match=EvalMatch.PARTIAL)]),
            EvalTool(name="GetRoomId", id=3, alternatives=[[0]], args=[EvalToolParam(key="room_name", value="Men", match=EvalMatch.PARTIAL)]),
            EvalTool(name="GetRoomId", id=4, alternatives=[[0]], args=[EvalToolParam(key="room_name", value="Uni", match=EvalMatch.PARTIAL)]),
            EvalTool(name="TurnOnLights", id=5, args=[EvalToolParam(key="room_id", value=9)]),
            EvalTool(name="TurnOnLights", id=5, args=[EvalToolParam(key="room_id", value=10)]),
            EvalTool(name="TurnOnLights", id=5, args=[EvalToolParam(key="room_id", value=11)]),
        ]
    },
    {
        "input": "Set the light intensity in the Focus space to 50%.",
        "output": "The answer should indicate, that the light intensity was set to 50%. In the given context, the answer might also indicate 50% as 0.5.",
        "tools": [
            EvalTool(name="GetRoomId", args=[EvalToolParam(key="room_name", value="Focus", match=EvalMatch.PARTIAL)]),
            EvalTool(name="SetLightIntensity", args=[EvalToolParam(key="room_id", value=4), EvalToolParam(key="intensity", value=0.5)]),
        ]
    },
    {
        "input": "Check if the Conference room is currently free and if it is, book it.",
        "output": "In the answer, the status of the conference occupation should be returned. If it is occupied, a booking procedure should not have happened. But if the conference room is free, it should also have already been booked.",
        "tools": [
            EvalTool(name="GetRoomId", id=0, args=[EvalToolParam(key="room_name", value="Conference", match=EvalMatch.PARTIAL)]),
            EvalTool(name="CheckAvailability", id=1, depends=[0], args=[EvalToolParam(key="room_id", value=2)]),
            EvalTool(name="BookRoom", id=2, depends=[1], args=[EvalToolParam(key="room_id", value=2)]),
        ]
    },
    {
        "input": "Please run a full system check. Summarize the results for me and for every damaged device, I want you to schedule a maintenance date on the 1st of February 2025",
        "output": "The answer should give an overview of the current status of each device in the system. There are in total 5 devices in the system. The devices 'Thermostat' and 'Security Camera' should have been found as damaged. Further, it should give a confirmation about the scheduling of maintenance dates on the 1st of February 2025 for the 'Thermostat' and 'Security Camera'.",
        "tools": [
            EvalTool(name="RunFullSystemCheck", id=0),
            EvalTool(name="GetDeviceId", id=1, depends=[0], args=[EvalToolParam(key="device_name", value="Thermostat")]),
            EvalTool(name="GetDeviceId", id=2, depends=[0], args=[EvalToolParam(key="device_name", value="Security Camera")]),
            EvalTool(name="ScheduleMaintenance", id=3, depends=[1], args=[EvalToolParam(key="device_id", value=0), EvalToolParam(key="date", value="2025-02-01")]),
            EvalTool(name="ScheduleMaintenance", id=3, depends=[2], args=[EvalToolParam(key="device_id", value=2), EvalToolParam(key="date", value="2025-02-01")]),
        ]
    },
    {
        "input": "Please order me the snack with the longest name",
        "output": "The answer should tell the user, that the snack with the longest name is 'chocolate bar'. Further, the answer should confirm that a 'chocolate bar' has been ordered for the user.",
        "tools": [
            EvalTool(name="GetSnackInventory", id=0),
            EvalTool(name="OrderSnack", id=1, depends=[0], args=[EvalToolParam(key="item", value="chocolate bar"), EvalToolParam(key="amount", value=1, optional=True)]),
        ]
    },
    {
        "input": "Please book me any available desk",
        "output": "The answer should include a specific desk id that was booked for the user.",
        "tools": [
            EvalTool(name="GetDesks", id=0),
            EvalTool(name="IsFree", id=1, alternatives=[[1]], depends=[0], args=[EvalToolParam(key="desk", value=1, match=EvalMatch.NONE)]),        # Is its own alternative, meaning it only needs to be present once
            EvalTool(name="BookDesk", id=2, depends=[1], args=[EvalToolParam(key="desk", value=1, match=EvalMatch.NONE)]),
        ]
    },
    {
        "input": "Please create an overview in the form of a table what contents are in which fridge spaces",
        "output": "The answer should include a formatted table in markdown. In this table, the fridge ids ranging from 60 to 66 should be listed alongside their contents.",
        "tools": [
            EvalTool(name="GetFridgeSpaceIds", id=0),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=60)]),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=61)]),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=62)]),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=63)]),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=64)]),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=65)]),
            EvalTool(name="GetFridgeContents", id=1, depends=[0], args=[EvalToolParam(key="space_id", value=66)]),
        ]
    },
    {
        "input": "Please schedule cleaning days for the kitchen as follows: Begin with the 1st of February 2025 and then until the end of March, schedule a cleaning day every two weeks.",
        "output": "The answer should confirm a successful scheduling of cleaning days for the following days: 1st of February 2025, 15th of February 2025, 1st of March 2025, 15th of March 2025, and 29th of March 2025.",
        "tools": [
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-02-01")]),
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-02-15")]),
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-03-01")]),
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-03-15")]),
            EvalTool(name="ScheduleCleaning", args=[EvalToolParam(key="date", value="2025-03-29")]),
        ]
    },
    {
        "input": "Can you check if there is any milk left in my fridge? If not, add 'milk' to my grocery list.",
        "output": "The answer should indicate, that there was no milk found in the fridge and that the item 'milk' has been added to the list of groceries, or that 'milk' is already part of the grocery list.",
        "tools": [
            EvalTool(name="GetFridgeContents", id=0),
            EvalTool(name="AddToGroceryList", id=1, depends=[0], args=[EvalToolParam(key="item", value="milk")]),
        ]
    },
    {
        "input": "Check the sensor battery in each room and tell me in which rooms the sensor battery is less than 30%.",
        "output": "The answer needs to include a list of the room names, in which the sensor battery is below 30%. The room names should be given as their actual names and not called 'Room 1' or 'Room 2'.",
        "tools": [
            EvalTool(name="GetRooms", id=0, alternatives=[[1]]),
            EvalTool(name="GetRoomIds", id=1, alternatives=[[0]])] + [
            EvalTool(name="CheckSensorBattery", id=2, args=[EvalToolParam(key="room_id", value=i)]) for i in range(1, 14)] + [
            EvalTool(name="CheckSensorBattery", id=2, args=[EvalToolParam(key="room_id", value=100)])
        ]
    },
    {
        "input": "What is the biggest room?",
        "output": "There is no way to know which room is the biggest in the office. The answer should tell the user, that it is not possible to retrieve the information with the available tools.",
        "tools": []
    },
    {
        "input": "Check the device health of every device in the system. If any device appears to be damaged, try to restart that device and then check its status again. Only attempt a restart once.",
        "output": "The answer should include the status of every device in the system. In total, there are 5 devices in the system. For each device that was damaged, the answer should further indicate, that it has restarted that device and also give the updated status of that device. It might happen, that a restarted device is still damaged, but in context of correctness, this is okay as long as the answer states that it has restarted every damaged device.",
        "tools": [
            EvalTool(name="RunFullSystemCheck", id=0),
            EvalTool(name="GetDeviceId", id=1, depends=[0], args=[EvalToolParam(key="device_id", value=0)]),
            EvalTool(name="GetDeviceId", id=2, depends=[0], args=[EvalToolParam(key="device_id", value=2)]),
            EvalTool(name="RestartDevice", id=3, depends=[1], args=[EvalToolParam(key="device_id", value=0)]),
            EvalTool(name="RestartDevice", id=4, depends=[2], args=[EvalToolParam(key="device_id", value=2)]),
            EvalTool(name="CheckDeviceHealth", id=5, depends=[3], args=[EvalToolParam(key="device_id", value=0)]),
            EvalTool(name="CheckDeviceHealth", id=6, depends=[4], args=[EvalToolParam(key="device_id", value=2)]),
        ]
    },
    {
        "input": "Please get the total size of the warehouse. Given a monthly rent cost of 7.50$ per square meter, what would be the monthly rent for the entire warehouse?",
        "output": "The answer should tell the user, that the total size of the warehouse is 5000 square meters. The answer then should give value for the monthly rent, which would be 37,500$.",
        "tools": [
            EvalTool(name="GetWarehouseAreaSize", id=0),
            EvalTool(name="Multiply", id=1, depends=[0], args=[EvalToolParam(key="a", value=7.5, match=EvalMatch.NONE), EvalToolParam(key="b", value=5000, match=EvalMatch.NONE)], optional=True),
        ]
    },
    {
        "input": "Find out in which warehouse zone the item 'curtain' is and navigate the logistic robot 2 to that zone to pick up two sets of curtains.",
        "output": "The answer should tell the user, the curtains were located in 'zone-E'. It should then have sent specifically the logistic robot number 2 to the 'zone-E' and should have made it pick up exactly 2 sets of curtains.",
        "tools": [
            EvalTool(name="GetItemLocation", id=0, args=[EvalToolParam(key="item", value="curtain")]),
            EvalTool(name="MoveToLocation", id=1, depends=[0], args=[EvalToolParam(key="zone", value="zone-E")]),
            EvalTool(name="PickupItem", id=2, depends=[1], args=[EvalToolParam(key="item", value="curtain")]),
            EvalTool(name="PickupItem", id=3, depends=[1], args=[EvalToolParam(key="item", value="curtain")]),
        ]
    },
    {
        "input": "I want to buy a printer and also a new sink, where would I find them?",
        "output": "The answer should tell the user, that the printers are located in 'zone-C', while the sinks are located in 'zone-E'.",
        "tools": [
            EvalTool(name="GetItemLocation", args=[EvalToolParam(key="item", value="printer")]),
            EvalTool(name="GetItemLocation", args=[EvalToolParam(key="item", value="sink")]),
        ]
    },
    {
        "input": "Please find out the contact details for the warehouse and prepare a formal written letter, that I would like to seek a job opportunity as a logistics manager in that warehouse.",
        "output": "The answer should include the address of the warehouse, which is 'Industrial Street 1'. Additionally, it might include that the name of the warehouse is 'Super Awesome Warehouse', the owner's name is 'John Warehouse', and the email address of the warehouse is 'Warehouse@mail.com'. It then has to include a formal letter, addressing the wish to start working at that warehouse as a logistics manager.",
        "tools": [
            EvalTool(name="GetWarehouseName"),
            EvalTool(name="GetWarehouseAddress"),
            EvalTool(name="GetWarehouseOwner"),
            EvalTool(name="GetWarehouseEmail"),
        ]
    },
    {
        "input": "I want to order a new pair of green scissors and a pair of blue jeans.",
        "output": "The answer should confirm the creation of two orders, one which has as an item a pair of green scissors and the other one which has an item of a pair of blue jeans. The order ids should be provided as well",
        "tools": [
            EvalTool(name="MakeOrders", id=0, alternatives=[[1, 2]], args=[EvalToolParam(key="items", value=["green scissors", "blue jeans"], match=EvalMatch.PARTIAL), EvalToolParam(key="amounts", value=[1, 1], optional=True)]),
            EvalTool(name="MakeOrder", id=1, alternatives=[[0]], args=[EvalToolParam(key="item", value="green scissors", match=EvalMatch.PARTIAL), EvalToolParam(key="amount", value=1, optional=True)]),
            EvalTool(name="MakeOrder", id=2, alternatives=[[0]], args=[EvalToolParam(key="item", value="blue jeans", match=EvalMatch.PARTIAL), EvalToolParam(key="amount", value=1, optional=True)]),
        ]
    },
    {
        "input": "Please move every logistics robot to 'zone-A'.",
        "output": "The answer should confirm, that the logistics robots number 1, 2, and 3 were all moved to 'zone-A'.",
        "tools": [
            EvalTool(name="MoveToLocation", args=[EvalToolParam(key="zone", value="zone-A")]),
            EvalTool(name="MoveToLocation", args=[EvalToolParam(key="zone", value="zone-A")]),
            EvalTool(name="MoveToLocation", args=[EvalToolParam(key="zone", value="zone-A")]),
        ]
    },
    {
        "input": "Where in the warehouse are the paints?",
        "output": "The answer should let the user know, that the warehouse currently does not have any paints or paint canister stored and therefore, no location should be named.",
        "tools": [
            EvalTool(name="GetItemLocation", args=[EvalToolParam(key="item", value="paints")]),
        ]
    },
    {
        "input": "Calculate the following formula: (sin(20)/cos(10)) * 0.45.",
        "output": "The correct result for the formula is approximately -0.489619. If the given result in the answer is somewhat close to this value, it can be considered as correct.",
        "tools": [
            EvalTool(name="Sin", id=0, args=[EvalToolParam(key="a", value=20)]),
            EvalTool(name="Cos", id=1, args=[EvalToolParam(key="a", value=10)]),
            EvalTool(name="Divide", id=2, depends=[0, 1], args=[EvalToolParam(key="a", value=0.9129452507276277), EvalToolParam(key="b", value=-0.8390715290764524)], optional=True),
            EvalTool(name="Multiply", id=3, depends=[2], args=[EvalToolParam(key="a", value=-1.0880422217787395), EvalToolParam(key="b", value=0.45)], optional=True)
        ]
    },
    {
        "input": "Please create two playlists. One should be called '80s Hits' and should include the following songs: 'Africa', 'Take on Me', 'Sweet Dreams (Are Made of This)', 'Footloose', 'Maniac'. The other one should be called 'Hip-Hop Classics' and should include the following songs: 'Jump Around', 'Still D.R.E.', 'POWER', 'Hypnotize', 'In Da Club'.",
        "output": "The answer should confirm the creation of two playlists with the names '80s Hits' and 'Hip-Hop Classics'. It should give the playlist ids for each of the playlists. It should also confirm, that the given songs have been added to each playlist respectively.",
        "tools": [
            EvalTool(name="CreateMultiplePlaylists", id=0, alternatives=[[1, 2]], args=[EvalToolParam(key="playlist_names", value=["80s Hits", "Hip-Hop Classics"]), EvalToolParam(key="playlist_songs", value=[['Africa', 'Take on Me', 'Sweet Dreams (Are Made of This)', 'Footloose', 'Maniac'], ['Jump Around', 'Still D.R.E.', 'POWER', 'Hypnotize', 'In Da Club']])]),
            EvalTool(name="CreatePlaylist", id=1, alternatives=[[0]], args=[EvalToolParam(key="playlist_name", value="80s Hits"), EvalToolParam(key="songs", value=['Africa', 'Take on Me', 'Sweet Dreams (Are Made of This)', 'Footloose', 'Maniac'])]),
            EvalTool(name="CreatePlaylist", id=2, alternatives=[[0]], args=[EvalToolParam(key="playlist_name", value="Hip-Hop Classics"), EvalToolParam(key="songs", value=['Jump Around', 'Still D.R.E.', 'POWER', 'Hypnotize', 'In Da Club'])])
        ]
    },
    {
        "input": "Check the water filter and the coffee machine. If any of those are damaged or require attention, report a kitchen issue. Also, schedule a cleaning day for the kitchen on the 1st of February 2025.",
        "output": "The answer should inform the user, that it has checked the water filter status, which could be any of 'Clean', 'Slightly used', 'Dirty', or 'Dysfunctional'. If it is 'Dysfunctional', or 'Dirty', an issue should have been reported. For the coffee machine, the available status are 'making coffee...', 'unavailable', 'available', 'cleaning', or 'coffee ready!'. In all cases a cleaning day on 1st of February 2025 should have been scheduled.",
        "tools": [
            EvalTool(name="CheckWaterFilterStatus", id=0),
            EvalTool(name="CheckCoffeeMachineStatus", id=1),
            EvalTool(name="ReportKitchenIssue", id=2, depends=[0, 1], args=[EvalToolParam(key="issue_description", value="issue", match=EvalMatch.NONE)], optional=True),
            EvalTool(name="ScheduleCleaning", id=3, args=[EvalToolParam(key="date", value="2025-02-01")]),
        ]
    }
]
