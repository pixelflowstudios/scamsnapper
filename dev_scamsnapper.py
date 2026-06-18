import os
import streamlit as st
import anthropic
import base64
import requests
from dotenv import load_dotenv

# 1. Load keys from .env
load_dotenv('dev_scamscanner.env')
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
WHOP_API_KEY = os.getenv("WHOP_API_KEY")

# 2. Page Config & CSS
st.set_page_config(page_title="ScamSnapper", page_icon="🛡️")
st.markdown("""
    <style>
    .result-verdict { font-size: 42px !important; font-weight: 800 !important; color: #E91E63 !important; line-height: 1.4 !important; }
    div.stButton > button:first-child { background-color: #E91E63 !important; color: white !important; font-size: 20px !important; padding: 12px 24px !important; }
    div.stMarkdown p, div.stMarkdown li { color: #C8A8E0 !important; font-size: 18px !important; line-height: 1.8 !important; }
    div.stMarkdown strong { color: #9B27AF !important; font-size: 20px !important; }
    div.stMarkdown h3 { font-size: 22px !important; }
    .stFileUploader label { font-size: 18px !important; }
    .stTextInput label { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ ScamSnapper")

# 3. Whop License Validation — list all memberships and match license key
def check_whop_subscription(license_key):
    url = "https://api.whop.com/api/v2/memberships"

    headers = {
        "Authorization": f"Bearer {WHOP_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)

        print(f"DEBUG: Status Code {response.status_code}")
        print(f"DEBUG: Response Body: {response.text}")

        if response.status_code != 200:
            return False

        data = response.json()
        memberships = data.get("data", [])

        for member in memberships:
            if (
                member.get("license_key") == license_key and
                member.get("valid") == True
            ):
                return True

        return False

    except Exception as e:
        print(f"DEBUG EXCEPTION: {e}")
        return False

# 4. Subscription Gate
if 'authorized' not in st.session_state:
    st.session_state['authorized'] = False

if not st.session_state['authorized']:
    st.subheader("Enter your License Key to access ScamSnapper")
    license_key = st.text_input("License Key:", type="password")

    if st.button("Verify Access"):
        if not license_key.strip():
            st.warning("Please enter a license key.")
        elif check_whop_subscription(license_key.strip()):
            st.session_state['authorized'] = True
            st.rerun()
        else:
            st.error("Invalid or expired license. Get one at your Whop product page.")

else:
    # 5. The App (only shown after successful license verification)
    uploaded_file = st.file_uploader("Upload a screenshot to scan:", type=["png", "jpg", "jpeg"])

    if uploaded_file and st.button("SCAN FOR SCAMS"):
        try:
            image_data = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

            # Detect actual media type from uploaded file
            file_type = uploaded_file.type or "image/png"

            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

            with st.spinner("Analyzing screenshot..."):
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1000,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": file_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": "Is this a scam? Start your response with 'YES' or 'NO' followed by a one-line verdict. Then organize your findings using these emoji headers in ALL CAPS and bold: **🚩 RED FLAGS**, **🔗 URL ISSUES**, **📋 INFORMATION REQUESTS**, **💬 COMMUNICATION ISSUES**, **⚠️ WHAT TO DO**. Use bullet points under each section. Keep it clear and professional."
                            }
                        ]
                    }]
                )

            raw_text = response.content[0].text.replace("#", "").strip()
            lines = raw_text.splitlines()

            st.markdown(f'<p class="result-verdict">{lines[0]}</p>', unsafe_allow_html=True)
            if len(lines) > 1:
                st.write("\n".join(lines[1:]))

        except Exception as e:
            st.error(f"Error during scan: {e}")

st.sidebar.info("ScamSnapper v1.0")