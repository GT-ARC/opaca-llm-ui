import openai

client = openai.OpenAI()

services = """
getTemperature(location: Location, date: Date): Float;
  getCurrentLocation(user: string): Location; 
  getToday(): Date
"""


services = """
bookDesk(room: Room)
getAirQuality(room: Room): float
getListOfRooms(): List<Room>
showRoute(room: Room)
"""

services = """
"agents": [
    {
      "agentId": "desk-agent",
      "agentType": "de.gtarc.opaca.sample.DeskAgent",
      "actions": [
        {
          "name": "GetDesks",
          "parameters": {
            "room": "string"
          },
          "result": "List[int]"
        },
        {
          "name": "IsFree",
          "parameters": {
            "desk": "int"
          },
          "result": "bool"
        },
        {
          "name": "BookDesk",
          "parameters": {
            "desk": "int"
          },
          "result": "bool"
        }
      ]
    },
    {
      "agentId": "sensor-agent",
      "agentType": "de.gtarc.opaca.sample.SensorAgent",
      "actions": [
        {
          "name": "GetTemperature",
          "parameters": {
            "room": "string"
          },
          "result": "float"
        },
        {
          "name": "GetNoise",
          "parameters": {
            "room": "string"
          },
          "result": "float"
        },
        {
          "name": "GetHumidity",
          "parameters": {
            "room": "string"
          },
          "result": "float"
        }
      ]
    },
    {
      "agentId": "wayfinding-agent",
      "agentType": "de.gtarc.opaca.sample.WayfindingAgent",
      "actions": [
        {
          "name": "NavigateTo",
          "parameters": {
            "room": "string"
          },
          "result": "null"
        }
      ]
    }
  ]
"""


system = """
You suggest web services to fulfil a given purpose.
You present the result as pseudo-code, including temporary variables if needed.
You know some agents providing different actions that you can use. Do not assume any other services.
If those services are not sufficient to solve the problem, just say so.
Following is the list of available services described in JSON, which can be called as webservices:   
""" + services

#user = "given my name, what is the temperature in my location?"
user = "get a list of rooms with temperature lower than 25 degrees, book me a free desk in one of these rooms, and navigate me to that room"
user = "book me 2 desks in the same room"
#user = "turn on the light in the room 'kitchen'"

completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
  )
print(completion.choices[0].message.content)
