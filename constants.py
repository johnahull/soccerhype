"""
Shared constants for SoccerHype video sections feature.
"""

# Predefined sections for highlight videos
SECTIONS = [
    "Goals",
    "Assists",
    "Dribbling",
    "Defense",
    "Saves",
    "Headers",
    "Free Kicks",
    "Penalties",
    "Set Pieces",
    "Passing"
]

# Color mapping for section badges in GUI
SECTION_COLORS = {
    "Goals": "#CC3333",
    "Assists": "#33AA33",
    "Dribbling": "#3366CC",
    "Defense": "#CC6633",
    "Saves": "#33AAAA",
    "Headers": "#AA33AA",
    "Free Kicks": "#AAAA33",
    "Penalties": "#8833CC",
    "Set Pieces": "#33CC99",
    "Passing": "#CC9933",
}

# Lower-third overlay timing constants (in seconds)
OVERLAY_DURATION_DEFAULT = 3.0  # Default overlay display duration
OVERLAY_FADE_IN = 0.5           # Fade-in animation duration
OVERLAY_FADE_OUT = 0.5          # Fade-out animation duration
OVERLAY_DURATION_MIN = 1.5      # Minimum overlay duration for short clips
OVERLAY_MARGIN = 0.5            # Margin before clip end for timing
