def apply_defaults(data, question):
    """Apply smart defaults based on the question and partial data from LLM."""
    question_lower = question.lower()

    # Model selection improvement (if model is unspecified)
    if "model" not in data or data["model"] == "":
        if "data" in question_lower:
            data["model"] = "Recording"  # Default to recordings for generic queries

    # Ensure filters exist
    if "filters" not in data:
        data["filters"] = {}

    # Apply model-specific defaults
    if data["model"] == "Recording":
        apply_recording_defaults(data["filters"], question_lower)
    elif data["model"] == "Subject":
        apply_subject_defaults(data["filters"], question_lower)

    return data


def apply_recording_defaults(filters, question_lower):
    # Brain region defaults
    if any(term in question_lower for term in ["hippocampus", "hippocampal"]):
        filters["brain_region"] = "Hippocampus"

    # Probe type defaults
    if any(term in question_lower for term in ["neuropixel", "neuropixels"]):
        filters["probe_type"] = "Neuropixels"
    elif any(term in question_lower for term in ["tetrode", "tetrodes"]):
        filters["probe_type"] = "Tetrode"  # This is likely missing

    # Subject state defaults
    if any(term in question_lower for term in ["sleeping", "sleep"]):
        filters["subject__state"] = "REM"
    elif any(term in question_lower for term in ["awake", "wake"]):
        filters["subject__state"] = "awake"


def apply_subject_defaults(filters, question_lower):
    # Subject state defaults
    if any(term in question_lower for term in ["sleeping", "sleep", "rem"]):
        filters["state"] = "REM"
    elif any(term in question_lower for term in ["awake", "wake"]):
        filters["state"] = "awake"
