import chainlit as cl


@cl.on_message
async def handle_message(message: cl.Message):
    await cl.Message(content=f"You said: {message.content}").send()