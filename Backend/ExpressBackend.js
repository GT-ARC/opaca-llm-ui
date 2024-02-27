import express from 'express'
import cors from 'cors'
import bp from 'body-parser'

import 'dotenv/config'
const app = express()
const port = 3000
app.use(cors())
app.use(bp.json())
app.use(bp.urlencoded({ extended: true }))

//openAI configuration
import OpenAIApi from "openai";
const openai = new OpenAIApi({apiKey: process.env.OPENAI_API_KEY});
const model='gpt-3.5-turbo'
    
app.listen(port, () => {
  console.log(`Example app listening on port ${port}`)
})

app.post("/wapi/reset", async (req, res) => {
  messageHistory = confMessage
  console.log("chat history was reset");
})

app.post("/wapi/chat", async (req, res) => {
  var prompt = req.body.prompt
  console.log("Prompt from Frontend: " + JSON.stringify(prompt))

  try {
    if (prompt == null) {
      throw new Error("Uh oh, no prompt was provided");
    }
    
    // trigger OpenAI completion
    const response = await openai.chat.completions.create({
      model: model,
      messages: prompt,
      temperature: 0.2,
      max_tokens: 150,
    });

    console.log("Complete response from OpenAI:")
    console.log(response);
    console.log("message from OpenAI:")
    console.log(response.choices[0].message);
    const responseMessage = response.choices[0].message;
    prompt.push(responseMessage);

    //send answer to frontend for no function call
    res.setHeader('Access-Control-Allow-Origin','*');
    res.status(200).json({
      success: true,
      messages: prompt,
    });

  } catch (error) {
    console.log(error.message);
    res.status(500).json({
      success: false,
      messages: {error: error.message},
    });
  }
});
