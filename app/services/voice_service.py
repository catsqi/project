"""
Backward-compatible facade for the voice service.

The implementation was split into `app.services.voice.*` to keep the codebase
maintainable without changing external imports.
"""

from app.services.voice import global_state, process_interaction, process_interaction_stream, stream

__all__ = [
    "global_state",
    "process_interaction",
    "process_interaction_stream",
    "stream",
]

if __name__ == "__main__":
    print("多模态交互 AI 面试官已就绪...")
    stream.ui.launch()
