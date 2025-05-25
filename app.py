import chainlit as cl

from src.verifact_manager import VerifactManager

pipeline = VerifactManager()

@cl.on_message
async def handle_message(message: cl.Message):
    progress_msg = cl.Message(content="Starting fact-checking pipeline...")
    await progress_msg.send()
    progress_updates = []

    async def progress_callback(msg, update):
        progress_updates.append(update)
        msg.content = "\n".join(progress_updates)
        await msg.update()

    try:
        verdicts = await pipeline.run(message.content, progress_callback=progress_callback, progress_msg=progress_msg)
        if not verdicts:
            progress_msg.content = "No factual claims detected in your message."
            await progress_msg.update()
            return
        # Format the final organized message
        response = ""
        for idx, (claim, evidence, verdict) in enumerate(verdicts):
            claim_text = getattr(claim, 'text', str(claim))
            verdict_text = getattr(verdict, 'verdict', str(verdict))
            confidence = getattr(verdict, 'confidence', 'N/A')
            explanation = getattr(verdict, 'explanation', 'N/A')
            sources = getattr(verdict, 'sources', [])
            sources_str = "\n".join(sources) if sources else "No sources provided."
            # Evidence formatting
            if evidence:
                evidence_str = "\n".join([
                    f"- {getattr(ev, 'content', str(ev))} (Source: {getattr(ev, 'source', 'N/A')}, Stance: {getattr(ev, 'stance', 'N/A')}, Relevance: {getattr(ev, 'relevance', 'N/A')})"
                    for ev in evidence
                ])
            else:
                evidence_str = "No evidence found."
            response += (
                f"\n---\n**Claim {idx+1}:** {claim_text}\n"
                f"**Evidence:**\n{evidence_str}\n"
                f"\n**Verdict:** {verdict_text}\n"
                f"**Confidence:** {confidence}\n"
                f"**Explanation:** {explanation}\n"
                f"**Sources:**\n{sources_str}\n"
            )
        progress_msg.content = response
        await progress_msg.update()
    except Exception as e:
        progress_msg.content = f"An error occurred during fact-checking: {str(e)}"
        await progress_msg.update()

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="👋 Welcome to VeriFact! The system is up and running. Type your claim or question to get started.").send()