"""
App entry point for Marketeer on Hugging Face Spaces (and local use).
"""

from ui.gradio_ui import create_interface


# Hugging Face Spaces will run this file.
# Locally, you can run: python app.py
if __name__ == "__main__":
    demo = create_interface()
    # On Spaces, you typically don't need any special args.
    demo.launch()
