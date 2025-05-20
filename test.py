import os
import requests
from dotenv import load_dotenv
from deepgram import DeepgramClient, PrerecordedOptions
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from langchain_groq import ChatGroq
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage
# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("Token")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
# Initialize conversation memory
# Initialize Deepgram client
deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)  
# Initialize Groq Chat Model
model_name = "llama-3.3-70b-versatile"  # Change to 'mixtral-8x7b-32768' or 'llama-3.3-70b-versatile' if needed
chat_model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=model_name)

# Set up the conversation chain
store={}
def get_chat_history(session_id:str)-> BaseChatMessageHistory:
  if session_id not in store:
    store[session_id]=ChatMessageHistory()
  return store[session_id]

conversation = RunnableWithMessageHistory(chat_model, get_chat_history)

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I'm your AI chatbot. Type anything to chat.")

#voice transcribe
async def transcribe_voice(update: Update, context: CallbackContext):
    """Handles voice messages, transcribes them, and replies with the text."""
    print("Transcription Function called...")
    # print(update.message)
    
    voice = update.message.voice

    # Get file info from Telegram
    file = await context.bot.get_file(voice.file_id)
    file_path = f"{file.file_id}.ogg"

    # Download the audio file
    response = requests.get(file.file_path)
    with open(file_path, "wb") as f:
        f.write(response.content)
        
    options = PrerecordedOptions(model="nova-3", smart_format=True)
    
    # Transcribe using Deepgram
    try:
        with open(file_path, "rb") as audio:
            audio_bytes = audio.read() 
            response = deepgram.listen.rest.v("1").transcribe_file({"buffer": audio_bytes}, options)  

        transcript = response.results.channels[0].alternatives[0].transcript


        if transcript:
            print("Transcription generated sucessfully...")
            os.remove(file_path)
            return transcript
        else:
            await update.message.reply_text("Sorry, I couldn't transcribe the audio.")

    except Exception as e:
        print(e)

    # Clean up: Delete the file after transcription

async def text_generation(update: Update, context: CallbackContext,text) -> None:
    # user_input = update.message.text
    print("Response is Generating...")
    response = conversation.invoke([HumanMessage(content=text)],
                        config={'configurable':{'session_id':"1"}}).content
    # response = conversation.predict(input=text)
    await update.message.reply_text(f"""{text}
Answer: {response}""")
    print("Message Send Sucessfully...")
# Message handler
async def handle_message(update: Update, context: CallbackContext) -> None:
    
    if update.message.voice:
         trans=await transcribe_voice(update, context)
         await text_generation(update, context, trans)
    else:
        user_input = update.message.text
        await text_generation(update, context, user_input)
    


# Main function to start the bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # app.add_handler(MessageHandler(filters.VOICE, transcribe_voice))
    app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
