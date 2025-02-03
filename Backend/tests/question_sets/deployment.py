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


    # {"question": "Find a meeting slot with the XAI team next week.", "icon": "📆"},
    # {"question": "Show my calendar for next week.", "icon": "📅"},
    {"question": "How can you assist me?", "icon": "❓"},
    {"question": "Tell me something about the 'go-KI' project by GT-ARC.", "icon": "🤖"},
    {"question": "What documents do I need for a residence permit?", "icon": "📄"},
    {"question": "Find the nearest public service office to the TU Berlin Campus?", "icon": "🏢"},
    {"question": "How can I get an appointment at the Berlin Bürgeramt?", "icon": "📅"},
    {"question": "What are 'Large Language Models'?", "icon": "🧠"},
    {"question": "What are the most exciting tech trends for 2025?", "icon": "🚀"},
    {"question": "Explain Agile methodology.", "icon": "🔄"},
    {"question": "How to build a simple website?", "icon": "💻"},
    {"question": "It is too noisy in the kitchen. Could you check if the noise level in the co-working space is lower?", "icon": "🔊"},
    {"question": "Set my desk height to 120cm.", "icon": "⬆️"},
    {"question": "Open the shelf in which I can store a glass.", "icon": "🥃"},
    {"question": "Where can I find the espresso cups in the kitchen?", "icon": "☕"},
    {"question": "Create a forecast of the temperature in the Coworking Space.", "icon": "🌤️"},
    {"question": "Plot the past noise levels in the ZEKI kitchen.", "icon": "📈"},
    {"question": "Create a bar plot comparing the current stock prices of Amazon, Apple, Microsoft and Nvidia.", "icon": "📊"},
    {"question": "Get Germany's energy production mix from the year 2024 and create a pie chart from it.", "icon": "⚡"},
]