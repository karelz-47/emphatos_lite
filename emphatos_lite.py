import json
import streamlit as st
from openai import OpenAI

# ──────────────────────────────────────────────────────────────
# App meta
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Empathos Lite", layout="centered")
st.title("Empathos Lite")
st.subheader("Your voice, their peace of mind")

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
LANGUAGE_OPTIONS = [
    "English", "Slovak", "Italian", "Icelandic",
    "Hungarian", "German", "Czech", "Polish", "Vulcan"
]

DEFAULT_PROMPT = (
    "You are Empathos, a seasoned life‑insurance‑support assistant.\n"
    "Use professional unit‑linked insurance terminology; ensure it sounds natural for native speakers with a background in unit‑linked insurance.\n"
    "Style: Empathic\n"
    "Customer review (verbatim):\n"
    "{client_review}\n\n"
    "Operator notes:\n"
    "{operator_notes}\n\n"
    "Task:\n"
    "1. Write a complete reply to the customer even if some details are missing.\n"
    "2. Whenever you must infer a fact, prefix it with ASSUMPTION: in one sentence.\n"
    "3. Length: ≤ 250 words.\n"
    "4. Voice: warm, empathic, strictly factual, using insurance terminology appropriately if needed.\n"
    "5. At the end of your reply, include exactly this signature (do not alter it):\n"
    "{signature}\n"
    "6. **Return only the final reply text** – no lists, no meta‑commentary."
)

# ──────────────────────────────────────────────────────────────
# Helper – minimal OpenAI wrapper
# ──────────────────────────────────────────────────────────────

def run_llm(messages, api_key):
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0.9,
        max_tokens=650,
    )
    return resp.choices[0].message.content.strip()

# ──────────────────────────────────────────────────────────────
# Session‑state bootstrap
# ──────────────────────────────────────────────────────────────
_defaults = {
    "stage": "init",          # init → done → reviewed → translated → reviewed_translation
    "draft": "",
    "reviewed_draft": "",
    "translation": "",
    "reviewed_translation": "",
    "operator_notes": "",
    "signature": "",
    "client_review": "",          
    "messages": [],            # raw LLM message history for debugging
    "api_log": []
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

# ──────────────────────────────────────────────────────────────
# UI – inputs
# ──────────────────────────────────────────────────────────────

st.text_area(
    "Operator signature (e.g., 'Yours sincerely\nJacob')",
    key="signature",
    placeholder="Enter your personal signature line(s) here",
    height=80,
)

client_review = st.text_area(
    "Customer message or review",
    key="client_review",                    
    placeholder="Paste the customer's text here",
    height=140,
)

st.text_area(
    "Additional information for answer (operator notes)",
    key="operator_notes",
    placeholder="Reply to open questions or add facts the model needs.",
    height=100,
)

st.radio("Response channel", ["Email (private)", "Public post"], key="channel_type", horizontal=True)

api_key = st.text_input("OpenAI API key", type="password")

# ──────────────────────────────────────────────────────────────
# Helper – safe Session-State reset
# ──────────────────────────────────────────────────────────────
def clear_state(preserve: bool = False) -> None:
    """Reset all fields; optionally keep signature & notes."""
    saved_sig   = st.session_state.get("signature", "")
    saved_notes = st.session_state.get("operator_notes", "")

    for k in (
        "stage", "draft", "reviewed_draft", "translation", "reviewed_translation",
        "messages", "api_log", "signature", "operator_notes", "client_review",
    ):
        st.session_state.pop(k, None)        # remove the key entirely

    if preserve:
        st.session_state["signature"]      = saved_sig
        st.session_state["operator_notes"] = saved_notes

    st.session_state["stage"] = "init"      # fresh start


# ──────────────────────────────────────────────────────────────
# Controls – Clear form
# ──────────────────────────────────────────────────────────────

keep_info = st.checkbox(
    "Keep signature and notes when clearing", key="keep_info"
)

st.button(
    "Clear fields / Start new task",
    key="btn_clear",
    on_click=clear_state,          # ← call helper BEFORE next rerun
    kwargs={"preserve": keep_info},
)

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Generate response draft
# ──────────────────────────────────────────────────────────────

if st.button("Generate response draft", key="btn_generate"):
    if not client_review.strip() or not api_key:
        st.error("Please provide the customer text and an API key.")
    else:
        # 1. Translate customer input → English
        try:
            detect_prompt = (
                "You are a translation assistant. Detect the language of the text below, "
                "then translate it into English. Return only the English translation."
            )
            client_review_en = run_llm([
                {"role": "system", "content": detect_prompt},
                {"role": "user", "content": client_review},
            ], api_key)
        except Exception as e:
            st.error(f"❌ OpenAI API error (translation): {e}")
            st.stop()

        # 2. Channel‑specific guidance
        if st.session_state.channel_type == "Email (private)":
            channel_instr = (
                "Format the response as a private email: greet the customer by name if known, "
                "include a polite signature, and keep policy references internal."
            )
        else:
            channel_instr = (
                "Format the response as a public‑facing post: no personal details, concise, "
                "maintain brand voice, end with a call‑to‑action if appropriate."
            )

        # 3. Build one‑shot prompt
        signature = st.session_state.signature.strip() or "(No signature provided)"
        system_prompt = f"{channel_instr}\n" + DEFAULT_PROMPT.format(
            client_review=client_review_en,
            operator_notes=st.session_state.operator_notes or "-",
            signature=signature,
        )
        st.session_state.messages = [{"role": "system", "content": system_prompt}]

        # 4. Call LLM → draft
        try:
            draft = run_llm(st.session_state.messages, api_key)
        except Exception as e:
            st.error(f"❌ OpenAI API error: {e}")
            st.stop()

        st.session_state.draft = draft
        st.session_state.stage = "done"

# ──────────────────────────────────────────────────────────────
# Review draft (single pass, no function calls)
# ──────────────────────────────────────────────────────────────

if st.session_state.stage == "done" and not st.session_state.reviewed_draft:
    review_prompt = (
        "You are a strict reviewer.\n"
        "TASK:\n"
        "- Audit the draft for factual accuracy, tone, and unauthorized promises.\n"
        "- Correct any issues directly in‑line.\n"
        "- Delete or rewrite ASSUMPTION lines only if they are unsupported or unclear.\n"
        "- Keep total length no more than 250 words.\n"
        "**Output only the final, corrected draft** (no explanations)."
    )
    try:
        reviewed = run_llm([
            {"role": "system", "content": review_prompt},
            {"role": "user",   "content": st.session_state.draft},
        ], api_key)
    except Exception as e:
        st.error(f"❌ OpenAI API error: {e}")
        st.stop()

    st.session_state.reviewed_draft = reviewed
    st.session_state.stage = "reviewed"

# ──────────────────────────────────────────────────────────────
# Show reviewed draft + controls
# ──────────────────────────────────────────────────────────────

if st.session_state.reviewed_draft:
    st.header("Final Draft (reviewed)")
    st.text_area("Draft", value=st.session_state.reviewed_draft, height=220)

    wc = len(st.session_state.reviewed_draft.split())
    st.caption(f"Word count: {wc} / 250")

    # Download button
    st.download_button(
        "📥 Download final reply",
        st.session_state.reviewed_draft,
        file_name="empathos_reply.txt",
        mime="text/plain",
    )

    st.markdown("---")

    # Translation option
    tgt = st.selectbox("Translate final reply to:", LANGUAGE_OPTIONS, index=0, key="translation_language")
    if st.button("Translate & review", key="btn_translate"):
        try:
            trans = run_llm([
                {
                    "role": "system",
                    "content": (
                        "You are a translation assistant. Translate the following reply into "
                        f"{tgt} using professional unit‑linked insurance terminology; ensure it sounds natural for native speakers.\n"
                        "Do not add commentary or promises."
                    ),
                },
                {"role": "user", "content": st.session_state.reviewed_draft},
            ], api_key)
        except Exception as e:
            st.error(f"❌ OpenAI API error (translation): {e}")
            st.stop()

        st.session_state.translation = trans
        st.session_state.stage = "translated"

    if st.session_state.translation and not st.session_state.reviewed_translation:
        # Light polish of translation
        try:
            polished = run_llm([
                {
                    "role": "system",
                    "content": (
                        "You are a meticulous supervisor reviewing the translated reply in\n"
                        f"{tgt} language. Improve wording for accuracy and tone. \n"
                        "Return only the improved version, nothing else. You must not change the language."
                    ),
                },
                {"role": "user", "content": st.session_state.translation},
            ], api_key)
        except Exception as e:
            st.error(f"❌ OpenAI API error: {e}")
            st.stop()

        st.session_state.reviewed_translation = polished
        st.session_state.stage = "reviewed_translation"

    if st.session_state.reviewed_translation:
        st.header("Final Translated Reply")
        st.text_area("Translation", value=st.session_state.reviewed_translation, height=220)
        st.download_button(
            "📥 Download translated reply",
            st.session_state.reviewed_translation,
            file_name="empathos_reply_translated.txt",
            mime="text/plain",
        )

# ──────────────────────────────────────────────────────────────
# Debug – raw API log (optional)
# ──────────────────────────────────────────────────────────────
if st.session_state.api_log:
    if st.checkbox("🔍 Show API Communication Log", key="show_api_log"):
        st.markdown("---")
        st.markdown("## 🔍 API Communication Log (all calls)")
        for i, entry in enumerate(st.session_state.api_log, start=1):
            with st.expander(f"Call #{i}"):
                st.markdown("**Outgoing messages**:")
                for m in entry["outgoing"]:
                    st.write(f"- role: `{m['role']}`")
                    st.code(m["content"])
                st.markdown("**Incoming response**:")
                inc = entry["incoming"]
                st.write(f"- role: `{inc['role']}`")
                st.code(inc["content"])
                if inc.get("function_call") and inc["function_call"]["name"]:
                    st.markdown("- function_call:")
                    st.write(f"  - name: `{inc['function_call']['name']}`")
                    st.write("  - arguments:")
                    st.json(json.loads(inc["function_call"]["arguments"] or "{}"))
