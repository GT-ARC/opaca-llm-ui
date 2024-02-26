# OpenAI API Test

Simple script for testing how OpenAI API works for finding suitable OPACA actions. Given a prompt with some known OPACA agents and actions in different formats and tries to answer some question about those.


## Simple Chat Web Interface

* based on https://gitlab.dai-labor.de/308201/wayfindingzeki-opaca
* first, run `npm install` in both the root and Backend directories
* to start, run `npm run dev` in the repo root directory, then go to http://localhost:5173/
* environment variable `OPENAI_API_KEY` has to be defined

### What is what?

* SimpleKeyboard does not seem to be used at all --> I added a simple input field for testing
* App.vue does not have all that much content any more --> remove entirely?
* content.vue container most of the UI logic and some javascript
* ExpressBackend provides REST routes for the core functions, which are called by the JS in content.vue, and calls the actual OpenAI API

### To Do

* [x] strip down Wayfinding Demo to just the OpenAI input prompt
* [ ] get OPACA services from Runtime Platform
* [ ] get speech recognition to work (it should already work, but not for me)
* [ ] get SimpleKeyboard to work
* [ ] adapt visuals a bit, insert OPACA Logo somewhere, etc.
* [ ] simplify further, e.g. does it really have to be those 2 packages?
