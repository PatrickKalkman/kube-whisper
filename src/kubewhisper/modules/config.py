class Config:
    SESSION_INSTRUCTIONS = (
        "You are Kuby, a helpful assistant. Respond to Pat. "
        "Keep all of your responses short. Say things like: "
        "'Task complete', 'There was an error', 'I need more information'."
    )
    PREFIX_PADDING_MS = 300
    SILENCE_THRESHOLD = 0.5
    SILENCE_DURATION_MS = 700
