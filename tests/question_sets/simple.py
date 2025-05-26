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


simple_questions = [
    {
        "input": "Please tell me the name of the room with id 1.",
        "output": "The answer should have successfully determined that the name of the room with id 1 is 'Experience Hub'."
    },
    {
        "input": "Can I make coffee?",
        "output": "The answer should check the status of the coffee machine. The available status can be 'making coffee...', 'unavailable', 'available', 'cleaning', or 'coffee ready!'. The answer should then tell the user if a new cup of coffee can be made, or if the coffee machine is currently in service or unavailable."
    },
    {
        "input": "I want to order something to eat, what are my options?",
        "output": "The answer should have retrieved a list of snacks. The full list of snacks should include 'chips', 'nuts', 'chocolate bar', 'gummy bears', 'apples', and 'ice'. Nothing should have been ordered yet."
    },
    {
        "input": "Please schedule a cleaning day for the kitchen on 1st of February 2025.",
        "output": "The answer should confirm that a cleaning day has been scheduled on the 1st of February 2025."
    },
    {
        "input": "Rent the fridge space with id 62 for 6 hours.",
        "output": "The answer should decline the request, since the available method to reserve a fridge space does only allow to specify a duration of days."
    },
    {
        "input": "Rent the fridge space with id 62 for 2 days.",
        "output": "The answer should confirm that the fridge space with the id 62 was successfully rented for a duration of 2 days."
    },
    {
        "input": "The dishwasher is once again not working... let someone know to fix this damn thing!",
        "output": "The answer should confirm is has reported a kitchen issue by calling the necessary action. The action itself does not return a confirmation, so the answer might indicate that it is unable to confirm whether the issue has been acknowledged or not."
    },
    {
        "input": "Is it just me or is the water in the kitchen dirty?",
        "output": "The answer should tell the user, that it has checked the water filter status. Based on the status, which can be 'Clean', 'Slightly used', 'Dirty', or 'Dysfunctional'. If the status is 'Clean', the answer should tell the user that the water should be safe to drink. Otherwise, the answer should tell the user, that the water filter should be checked and changed and that the water might not be safe to drink."
    },
    {
        "input": "Remind me, what did I want to buy at the store?",
        "output": "The answer should have checked the current grocery list. This list includes: 'bread', 'tomato', 'pasta', 'water', 'juice'"
    },
    {
        "input": "It is too dark in room 4, please change that.",
        "output": "The answer should tell the user, that it has turned on the lights in room 4."
    },
    {
        "input": "Can you tell me which rooms exist in this office building?",
        "output": "The answer should tell the user every existing room, which includes: 'Experience Hub', 'Conference Room', 'Management Office', 'Focus Space', 'Design Thinking Space', 'Co-Working Space', 'Robot Development Space', 'Robot Testing Area', 'Bathroom Women', 'Bathroom Men', 'Bathroom Uni', 'Kitchen', 'Server Room', 'VIP Room'."
    },
    {
        "input": "Give me every available data for room 10.",
        "output": "The answer should give information about room 10 for its temperature, co2 level, humidity, noise leve, and the sensor battery level."
    },
    {
        "input": "I need to order four computer mouses.",
        "output": "The answer should confirm that an order has been placed for 4 computer mouses. The id of the order should be given within the answer. The id number should be positive or 0, both are valid order ids."
    },
    {
        "input": "In which zone can I find a fax-machine?",
        "output": "The answer should tell the user, that the item 'fax-machine' can be found in 'zone-C'."
    },
    {
        "input": "What items can be found in 'zone-B'?",
        "output": "The answer should have identified the items in 'zone-B' to be 'box', 'wrap', 'tape', 'rope', 'strap'."
    },
    {
        "input": "Is there a way I can write an email to the warehouse?",
        "output": "The answer should tell the user, that the e-mail address to contact the warehouse is 'Warehouse@mail.com'."
    },
    {
        "input": "What are the sizes of each zone?",
        "output": "The answer should tell the user the following sizes: ('zone-A', 2000), ('zone-B', 1000), ('zone-C', 750), ('zone-D', 750), ('zone-E', 500). It should also tell the user, that the sizes are given as square meters."
    },
    {
        "input": "What is the location second logistic robot?",
        "output": "The answer should tell the user, that logistic robot 2 is currently located in 'zone-C'."
    },
    {
        "input": "Is the first logistic robot carrying something at the moment?",
        "output": "The answer should tell the user, that the logistic robot 1 has items within its inventory, which include: 'ball', 'shovel', 'towel'. Therefore, it should tell the user, that the logistic robot 1 is in fact carrying items."
    },
    {
        "input": "Please start playing the track 7",
        "output": "The answer should confirm to the user, that the track with id 7 is now currently playing."
    },
    {
        "input": "Please set the volume down to 3",
        "output": "The answer should confirm that the current volume level has been set to 3."
    },
    {
        "input": "What is 42 to the power of 4?",
        "output": "The answer should include the result for the calculation of 42 to the power of 4, which is 3,111,696."
    },
    {
        "input": "What is the sine of 2.857?",
        "output": "The answer should tell the sine of 2.857, which is roughly 0.2807665132504996. If the result is approximately this value, the answer can be seen as fulfilled."
    },
    {
        "input": "What would I get, if I subtract twelve from one hundred and four?",
        "output": "The answer should tell the user the result of 104 minus 12, which is 92, or ninety-two."
    },
]
