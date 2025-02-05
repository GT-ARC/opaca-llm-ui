#                                                                                   #
#   This file provides the example questions defined in the frontend. Since these   #
#   questions are tested with the real deployment, only questions with no           #
#   physical or invasive effect are tested. For example, tests regarding the        #
#   opening and closing of kitchen shelves are left out.                            #
#                                                                                   #
#   !!!!HOWEVER!!!!                                                                 #
#                                                                                   #
#   If you decide to test this set of questions with the deployment, it could       #
#   happen that incorrectly generated and executed function calls might resolve     #
#   in physical calls, so be very careful when testing these.                       #
#                                                                                   #

deployment_questions = [
    {
        "input": "Please fetch and summarize my latest e-mails.",
        "output": "The answer should give an overview with bullet points containing information to each of the latest e-mail. The response should only include general information and not return the full content of a single e-mail.",
    },
    {
        "input": "Summarize my upcoming meetings for the next 3 days.",
        "output": "The answer should include an overview of upcoming meetings. For each meeting, the date, time, location and attendees should be given.",
    },
    {
        "input": "Show the phone numbers of all participants in my next meeting.",
        "output": "The answer should tell the user the name of the next meeting, the name of the attendees of that meeting and further include a list providing the phone numbers of each attendee. The phone numbers of Tolga Akar, Tobias Küster and David Schultz should always exist, if they are part of the attendees."
    },
    {
        "input": "Draft an out-of-office email explaining that Tolga is my stand-in for the next 2 weeks.",
        "output": "The answer should contain a nicely formatted e-mail, addressed to a generic group of people, explaining that Tolga is the stand-in for oneself for the next 2 weeks. The answer should not include that it has sent that e-mail to anyone."
    },
    {
        "input": "I need the phone numbers of the people working with XAI from the GoKI project.",
        "output": "The answer should tell the user, that it has found 'Nils Breuer', which deals with XAI in the GoKI project. His phone number should be +493031474042."
    },
    {
        "input": "How can you assist me?",
        "output": "The answer should give a summary about all the functions that are available to it. These should include sensor readings, like checking the temperature or Co2 levels in different rooms, offer help with services from the Berlin Bürgeramt, various e-mail services, and data analysis functions. The answer should not include generic answers given by LLMs. It should not include the ability to write poems or help with creative writing."
    },
    {
        "input": "Tell me something about the 'go-KI' project by GT-ARC.",
        "output": "The answer should tell the user, that the 'go-KI' project by GT-ARC resolves around developing AI applications for the common good. It should give a short summary of different key aspects of the project. It should not include any information about Mangas."
    },
    {
        "input": "What are 'Large Language Models'",
        "output": "The answer should give an overview of the key aspects of Large Language Models. It should emphasize the generation of natural language and the huge amount of data to train such models."
    },
    {
        "input": "What are the most exciting tech trends for 2025?",
        "output": "The answer should be concrete and not give a hypothesis. The tech trends for 2025 might include 'Agentic AI', 'Disinformation security', 'Post-quantum cryptography', 'Energy-efficient computing', 'spatial computing', 'polyfunctional robots'. The list of tech trends can be different, but should list at least 5 different topics."
    },
    {
        "input": "Explain Agile methodology.",
        "output": "The answer should give a detailed explanation of agile methodology. It should include aspects like flexibility and allow for sudden changes in the workflow. It should also state the close collaboration with customers to accommodate these changes."
    },
    {
        "input": "How to build a simple website?",
        "output": "The answer should give a short plan on how to design and create a simple website. It should further give a very short example of html code of a simple website. It should also provide the keywords 'HTML' and 'CSS'"
    },
    {
        "input": "It is too noisy in the kitchen. Could you check if the noise level in the co-working space is lower?",
        "output": "The answer should provide the current noise level from the kitchen and also the current noise level from the co-working space in values. It should then tell the user that the room with the smaller value is more quiet. The value that is given is NOT in decibel. If the answer gives the unit as decibel, the score should be lowered."
    },
    {
        "input": "Create a forecast of the temperature in the Coworking Space.",
        "output": "The answer should return an embedded image in markdown language, which should show a forecast of the temperature in the coworking space for the next days."
    },
    {
        "input": "Plot the past noise levels in the ZEKI kitchen.",
        "output": "The answer should return an embedded image in markdown language, which should show the historic noise levels in the ZEKI kitchen."
    },
    {
        "input": "Create a bar plot comparing the current stock prices of Amazon, Apple, Microsoft and Nvidia.",
        "output": "The answer should return an embedded image, in which the stock prices of Amazon, Apple, Microsoft, and Nvidia and compared. The answer should indicate, that the values are the current stock prices and not historic data."
    },
    {
        "input": "Get Germany's energy production mix from the first half of the year 2024 and create a pie chart from it.",
        "output": "The answer should return an embedded image, in which the Germany's energy production mix from the first half of 2024 should be displayed. It should mention coal, natural gas, wind, and solar energies to be part of the energy mix. The percentage of nuclear energy should be 0, since Germany has shutdown its last nuclear power plants since the beginning of 2024."
    },


    # {"question": "Find a meeting slot with the XAI team next week.", "icon": "📆"},
    # {"question": "Show my calendar for next week.", "icon": "📅"},

    # Bobbi agent not working currently.
    # {"question": "What documents do I need for a residence permit?", "icon": "📄"},
    # {"question": "Find the nearest public service office to the TU Berlin Campus?", "icon": "🏢"},
    #{"question": "How can I get an appointment at the Berlin Bürgeramt?", "icon": "📅"},


    # This would not create real-world effects if executed properly, but the risk is too high that shelves are opened
    # {"question": "Where can I find the espresso cups in the kitchen?", "icon": "☕"},
]