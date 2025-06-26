import json
import streamlit as st
from openai import OpenAI
from streamlit.components.v1 import html

# ─────────────────────────────────────────────
# i18n – Manual lightweight version
# ─────────────────────────────────────────────
FLAGS = {
    "en": "gb",   # 🇬🇧
    "sk": "sk",   # 🇸🇰
    "it": "it",   # 🇮🇹
    "hu": "hu"    # 🇭🇺
}

DEFAULT_LANG = "en"

current_lang = st.query_params.get("lang", DEFAULT_LANG)

# after current_lang is defined  ───────────────────────────────
def load_translation(lang):
    try:
        with open(f"lang/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        with open("lang/en.json", "r", encoding="utf-8") as f:
            return json.load(f)

_trans = load_translation(current_lang)

def _(key: str) -> str:
    """Return translated string or the key itself if missing."""
    return _trans.get(key, key)

# ─────────────────────────────────────────────────────────────
# Flag selector – uses on_click → same-tab, no other buttons touched
# ─────────────────────────────────────────────────────────────
FLAGS = {"en": "gb", "sk": "sk", "it": "it", "hu": "hu"}
DEFAULT_LANG = "en"
current_lang = st.query_params.get("lang", DEFAULT_LANG)

def _switch_lang(code):
    st.query_params["lang"] = code     # rewrite URL
    st.rerun()                         # reload in same tab

with st.container():
    flag_cols = st.columns(len(FLAGS))
    for (code, iso), col in zip(FLAGS.items(), flag_cols):
        border = "2px solid #1f77ff" if code == current_lang else "1px solid rgba(0,0,0,.15)"

        # put the <img> HTML directly in the button’s label
        col.button(
            label=f"""<img src="https://flagcdn.com/w40/{iso}.png"
                           style="width:32px;height:24px;object-fit:cover;
                              border:{border};border-radius:6px;" />""",
            key=f"flag_{code}",
            on_click=_switch_lang,
            args=(code,),
            use_container_width=True,          # so the icon is centred
            unsafe_allow_html=True             # let HTML through
        )

    # hide ONLY the buttons in this container
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button:empty {
            background: transparent;
            border: none;
            padding: 0;
            height: 24px; width: 32px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────────────────────
# App meta
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title=_("APP_TITLE"), layout="centered")
st.title(_("APP_TITLE"))
st.subheader(_("TAGLINE"))
# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

LANGUAGE_OPTIONS = [
    "English", "Slovak", "Italian", "Icelandic",
    "Hungarian", "German", "Czech", "Polish", "Vulcan"
]

DEFAULT_PROMPT = (
    "You are Empathos, a seasoned life‑insurance‑support assistant.\n"
    "Use professional insurance terminology; ensure it sounds natural for native speakers with a background in insurance. \n"
    "If replying to message in relation to unit-linked product, use accordingly the terminology.\n"
    "— Tone & style —\n"
    "• Audience: retail policyholders.\n"
    "• Voice: warm, empathic, strictly factual.\n" 
    "• Register: professional insurance terminology.\n" 
    "• Max length: 220 words (±10). Trim greetings/closings before omitting facts.\n\n"

    "— Inputs —\n"
    "CLIENT_REVIEW: {client_review}\n"
    "OPERATOR_NOTES (may be blank): {operator_notes}\n"

    "— Task —\n"
    "1. Draft a complete reply that addresses every point in CLIENT_REVIEW. \n" 
    "2. If you must infer any fact, add **one sentence** starting with **[ASSUMPTION]**.  \n"
    "Example: “[ASSUMPTION] You may be referring to the annual fund-switch window in March.”  \n"
    "3. If CLIENT_REVIEW or OPERATOR_NOTES is blank, silently skip that section.  \n"
    "4. Do **not** expose policy numbers or internal processes.  \n"
    "5. Do **not** promise anything beyond existing policy terms.  \n"
    "6. End with this exact signature (unaltered): {signature}\n\n"

    "Return **only** the final reply text (no meta-commentary, no lists)."

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
# Helper – clipboard button (pure front-end)
# ──────────────────────────────────────────────────────────────
def copy_button(text: str, key: str, label: str = _("BTN_COPY")) -> None:
    """
    Render a pill-shaped 📋 button (same font/style as Streamlit buttons)
    that copies *text* to clipboard.
    """
    escaped = json.dumps(text)

    st.markdown(
        f"""
        <button id="{key}" class="copy-btn">
            📋 {label}
        </button>

        <script>
        const btn_{key} = document.getElementById("{key}");
        if (btn_{key}) {{
            btn_{key}.onclick = () => {{
                navigator.clipboard.writeText({escaped});
                const original = btn_{key}.innerHTML;
                btn_{key}.innerHTML = "✅ Copied";
                setTimeout(() => btn_{key}.innerHTML = original, 1200);
            }};
        }}
        </script>

        <style>
        /* one-off style hooked to this id only */
        #{key}.copy-btn {{
            font: inherit;                       /* same family/weight */
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            padding: .3rem .9rem;
            border-radius: .5rem;
            border: 1px solid rgba(49,51,63,.2);
            background: #fff;                    /* white pill */
            cursor: pointer;
            transition: background .15s;
        }}
        #{key}.copy-btn:hover  {{ background:#f8f9fa; }}
        #{key}.copy-btn:active {{ background:#eceef1; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    _("SIGNATURE_LABEL"),
    key="signature",
    placeholder=_("SIGNATURE_PLACEHOLDER"),
    height=80,
)

client_review = st.text_area(
    _("CUSTOMER_MSG"),
    key="client_review",                    
    placeholder=_("CUSTOMER_MSG_PLACEHOLDER"),
    height=140,
)

st.text_area(
    _("NOTES"),
    key="operator_notes",
    placeholder=_("NOTES_PLACEHOLDER"),
    height=100,
)

st.radio(_("CHANNEL"), [_("EMAIL_PRIVATE"), _("PUBLIC_POST")], key="channel_type", horizontal=True)

api_key = st.text_input(_("API_KEY"), type="password")

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
    _("KEEP_INFO"), key="keep_info"
)

st.button(
    _("BTN_CLEAR"),
    key="btn_clear",
    on_click=clear_state,          # ← call helper BEFORE next rerun
    kwargs={"preserve": keep_info},
)

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Generate response draft
# ──────────────────────────────────────────────────────────────

if st.button(_("BTN_GENERATE"), key="btn_generate"):
    if not client_review.strip() or not api_key:
        st.error(_("ERROR_MISSING_INPUTS"))
    else:
        # ★ Wipe any previous outputs so we always start fresh
        for k in ("draft", "reviewed_draft", "translation", "reviewed_translation"):
            st.session_state[k] = ""
        st.session_state.stage    = "init"
        st.session_state.messages = []           # clear old system prompt

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

        target_lang_name = {
            "en": "English", "sk": "Slovak",
            "it": "Italian", "hu": "Hungarian"
        }[current_lang]

        channel_instr += f"\nAlways write the final reply in {target_lang_name}."

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
    st.header(_("DRAFT_ANSWER"))
    st.text_area(_("DRAFT_LABEL"), value=st.session_state.reviewed_draft, height=220)

    wc = len(st.session_state.reviewed_draft.split())
    st.caption(f"Word count: {wc} / 250")

    # Download button
    col_dl, col_cp = st.columns([1, 1])        # 1-to-1 width; tweak as you like
    with col_dl:
        st.download_button(
            _("BTN_DOWNLOAD"),
            st.session_state.reviewed_draft,
            file_name="empathos_reply.txt",
            mime="text/plain",
        )
    with col_cp:
    # NEW: clipboard button right next to it
        copy_button(
             st.session_state.reviewed_draft,
             key="copy_draft_btn",
        )

    st.markdown("---")

    # Translation option
    tgt = st.selectbox(_("TRANSLATE_TO"), LANGUAGE_OPTIONS, index=0, key="translation_language")
    if st.button(_("BTN_TRANSLATE"), key="btn_translate"):
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
        st.header(_("TRANSLATED_ANSWER"))
        st.text_area(_("TRANSLATION_LABEL"), value=st.session_state.reviewed_translation, height=220)
        
        col_dl, col_cp = st.columns([1, 1])
        with col_dl:
            st.download_button(
                _("BTN_DOWNLOAD"),
                st.session_state.reviewed_translation,
                file_name="empathos_reply_translated.txt",
                mime="text/plain",
            )
        with col_cp:
        # NEW clipboard for translation
            copy_button(
                st.session_state.reviewed_translation,
                key="copy_translation_btn",
            )

# ──────────────────────────────────────────────────────────────
# Debug – raw API log (optional)
# ──────────────────────────────────────────────────────────────
if st.session_state.api_log:
    if st.checkbox(_("SHOW_API_LOG"), key="show_api_log"):
        st.markdown("---")
        st.markdown(_("API_LOG_HEADER"))
        for i, entry in enumerate(st.session_state.api_log, start=1):
            with st.expander(f"Call #{i}"):
                st.markdown(_("OUTGOING_MESSAGES"))
                for m in entry["outgoing"]:
                    st.write(f"- role: `{m['role']}`")
                    st.code(m["content"])
                st.markdown(_("INCOMING_MESSAGES"))
                inc = entry["incoming"]
                st.write(f"- role: `{inc['role']}`")
                st.code(inc["content"])
                if inc.get("function_call") and inc["function_call"]["name"]:
                    st.markdown(_("FUNCTION_CALL"))
                    st.write(f"  - name: `{inc['function_call']['name']}`")
                    st.write(_("ARGUMENTS"))
                    st.json(json.loads(inc["function_call"]["arguments"] or "{}"))
