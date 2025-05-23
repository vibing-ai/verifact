import chainlit as cl

from src.verifact_agents.pipeline import FactcheckPipeline

pipeline = FactcheckPipeline()

@cl.on_message
async def handle_message(message: cl.Message):
    result = await pipeline.process(message.content)
    if result is None:
        await cl.Message(content="No factual claims detected in your message.").send()
        return
    if "error" in result:
        await cl.Message(content=f"An error occurred during fact-checking: {result['error']}").send()
        return
    claim = result["claim"]
    verdict = result["verdict"]
    # Defensive: handle missing attributes gracefully
    claim_text = getattr(claim, 'text', str(claim))
    verdict_text = getattr(verdict, 'verdict', str(verdict))
    confidence = getattr(verdict, 'confidence', 'N/A')
    explanation = getattr(verdict, 'explanation', 'N/A')
    sources = getattr(verdict, 'sources', [])
    sources_str = "\n".join(sources) if sources else "No sources provided."
    response = (
        f"**Claim:** {claim_text}\n"
        f"**Verdict:** {verdict_text}\n"
        f"**Confidence:** {confidence}\n"
        f"**Explanation:** {explanation}\n"
        f"**Sources:**\n{sources_str}"
    )
    await cl.Message(content=response).send()

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="👋 Welcome to VeriFact! The system is up and running. Type your claim or question to get started.").send()