import chainlit as cl


@cl.on_message
async def handle_message(message: cl.Message):
    await cl.Message(content=f"You said: {message.content}").send()

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="👋 Welcome to VeriFact! The system is up and running. Type your claim or question to get started.").send()