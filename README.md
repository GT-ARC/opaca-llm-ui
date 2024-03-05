# OpenAI API Test

Simple script for testing how OpenAI API works for finding suitable OPACA actions. Given a prompt with some known OPACA agents and actions in different formats and tries to answer some question about those.


## Simple Chat Web Interface

* based on https://gitlab.dai-labor.de/308201/wayfindingzeki-opaca
* first, run `npm install` in both the root and Backend directories
* to start, run `npm run dev` in the repo root directory, then go to http://localhost:5173/
* environment variable `OPENAI_API_KEY` has to be defined

### What to do and what to expect?

* start the app as described above
* the default prompt will be "Which services do you know?" ask that, i.e. press enter in the input field -> the AI should respond that it does not know any services as it is not connected to an OPACA platform
* start an OPACA platform on the same machine, so the app can find it on `localhost:8000`; see <https://gitlab.dai-labor.de/jiacpp/prototype/>
* press the "Reset Chat" button and ask the question again -> how it should say that it does not know any services since no agents are running
* get the Dummy Services <https://gitlab.dai-labor.de/zeki-bmas/tp-framework/dummy-services> and build the image with `docker build -t dummy-services-image .`, then deploy the image to the OPACA Platform at <http://localhost:8000/swagger-ui/index.html>, calling the POST Container route with `{"image": {"imageName": "dummy-services-image"}}`
* reset the chat again and ask the question again -> now it should list the different available agents and their actions
* ask for help with developing something that might involve those services (or something completely unrelated)

### What is what?

* SimpleKeyboard does not seem to be used at all --> I added a simple input field for testing
* App.vue does not have all that much content any more --> remove entirely?
* content.vue container most of the UI logic and some javascript
* ExpressBackend provides REST routes for the core functions, which are called by the JS in content.vue, and calls the actual OpenAI API

### To Do

* [x] strip down Wayfinding Demo to just the OpenAI input prompt
* [x] get OPACA services from Runtime Platform
* [X] get speech recognition to work (it should already work, but not for me)
* [X] get SimpleKeyboard to work
* [X] adapt visuals a bit, insert OPACA Logo somewhere, etc.
* [ ] simplify further, e.g. does it really have to be those 2 packages?
* [ ] make location of OPACA platform configurable in the UI itself?
* [X] re-enable multiple languages (all the code is still there, just translate the new prompt)
