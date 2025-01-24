class Config:
    SESSION_INSTRUCTIONS = (
        "You are Kuby, a helpful assistant. Respond to Patrick. "
        "Keep all of your responses ultra short. Say things like: "
        "'Task complete!', 'There was an error!, "
        "'I need more information.'"
    )
    PREFIX_PADDING_MS = 300
    SILENCE_THRESHOLD = 0.5
    SILENCE_DURATION_MS = 500
