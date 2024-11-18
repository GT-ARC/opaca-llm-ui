<!-- /*******************************************************************************
* Distributed Artificial Intelligence Laboratory TU Berlin.
* Wayfinding system (BACKEND & FRONTEND TEAM)
* All Rights Reserved.
********************************************************************************
* Filename    : SimpleKeyboard.vue
* Description : 
*
* History
*-------------------------------------------------------------------------------
* Date                       Name                    Description of Change
* 19.01.2023              Louis Ankel             Implementation of first Keyboard attempt -> filter in App.vue not in SearchBar.vue anymore 
* 08.02.2023   Louis Ankel, Adrian Brag, Markus Thunig      Custom keyboard changes 
*-------------------------------------------------------------------------------
* Developers :  
                Louis Leon Ankel (@ltrou_7)
                Markus Thunig (@markust)
                Adrian Benjamin Brag (@adri.b.brag)
*******************************************************************************/ -->

<template>
      <div class="keyboardContainer">
            <div class="simple-keyboard-main"></div>
      </div>
</template>

<script>
import Keyboard from "simple-keyboard";
import "simple-keyboard/build/css/index.css";

export default {
      name: "SimpleKeyboard",
      props: {
            keyboardClass: {
                  default: "simple-keyboard",
                  type: String,
            },
            input: {
                  type: String,
            },
      },
      data() {
            return {
                  keyboard: null,
            };
      },
      mounted() {
            let commonKeyboardOptions = {
                  onChange: (input) => this.onChange(input),
                  onKeyPress: (button) => this.onKeyPress(button),

                  mergeDisplay: true,
            };
            this.keyboard = new Keyboard(".simple-keyboard-main", {
                  ...commonKeyboardOptions,

                  layout: {
                        default: [
                              "1 2 3 4 5 6 7 8 9 0 {bksp}",
                              "q w e r t z u i o p ü",
                              "a s d f g h j k l ö ä",
                              "y x c v b n m , . - {shift}",
                              "{space}",
                        ],
                        shift: [
                              "1 2 3 4 5 6 7 8 9 0 {bksp}",
                              "Q W E R T Z U I O P Ü",
                              "A S D F G H J K L Ö Ä",
                              "Y X C V B N M ; : _ {shift}",
                              "{space}"
                        ]
                  },
                  display: {
                        '{bksp}': 'delete',
                  },
                  excludeFromLayout: {
                        default: [],
                  },
            });
      },
      methods: {
            onChange(input) {
                  this.$emit("onChange", input);
                  this.$emit("filterArray");
            },
            onKeyPress(button) {
                  this.$emit("onKeyPress", button);
                  if (button === "{shift}")
                        this.handleShift();
            },
            handleShift() {
                  let currentLayout = this.keyboard.options.layoutName;
                  let shiftToggle =
                        currentLayout === "default" ? "shift" : "default";

                  this.keyboard.setOptions({
                        layoutName: shiftToggle,
                  });
            },
      },
      watch: {
            input(input) {
                  this.keyboard.setInput(input);
            },
      },
};
</script>

<style>
      .simple-keyboard-main{
            background-color: #212529;
            opacity: 0.8;
      }
</style>
