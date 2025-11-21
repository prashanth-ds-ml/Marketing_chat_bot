from core_logic.llm_config import get_local_chat_model
from langchain_core.messages import HumanMessage


def main():
    # Load the ChatHuggingFace model (cached after first call)
    chat_model = get_local_chat_model()

    # Instead of SystemMessage, fold instructions into the human message
    prompt = (
        "You are a friendly marketing copywriter.\n\n"
        "Write a short, fun one-line ad for a coffee shop."
    )

    messages = [
        HumanMessage(content=prompt),
    ]

    # Call the model
    ai_msg = chat_model.invoke(messages)

    # Show the result
    print("Response type:", type(ai_msg))
    print("Response content:\n")
    print(ai_msg.content)


if __name__ == "__main__":
    main()
