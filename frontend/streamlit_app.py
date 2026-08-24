from datetime import date, timedelta
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from services.finance import analyze, goal_plan, notifications, recommendations, sample_transactions
from ml.risk_model import predict_risk
from dl.behavior_model import predict_savings
from database.mongodb import authenticate_user, load_notifications, load_transactions, register_user, save_notifications, save_transaction

st.set_page_config(page_title="AI Financial Advisor", page_icon="$", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#17212b; --muted:#6c7884; --line:#dfe6e3; --mint:#dff4ea; --green:#147d62; --coral:#ef755f; }
html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
h1,h2,h3 { font-family:'Space Grotesk', sans-serif; letter-spacing:0; }
.block-container { padding:2.2rem 3rem 3rem; max-width:1450px; }
[data-testid="stSidebar"] { background:#f4f7f5; border-right:1px solid var(--line); }
.eyebrow { color:var(--green); font-size:.75rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.hero { background:linear-gradient(120deg,#e8f7ef 0%,#f9fbf8 58%,#fff0e7 100%); padding:2.1rem 2.3rem; border:1px solid var(--line); border-radius:8px; margin-bottom:1.4rem; }
.hero h1 { font-size:2.7rem; margin:.25rem 0 .4rem; }
.hero p { color:var(--muted); max-width:650px; margin:0; }
.metric { border-top:3px solid var(--green); padding:1rem 0; }
.metric small { color:var(--muted); text-transform:uppercase; letter-spacing:.08em; font-size:.68rem; font-weight:700; }
.metric strong { display:block; font-family:'Space Grotesk'; font-size:1.75rem; margin-top:.3rem; }
.section-label { border-bottom:1px solid var(--line); padding-bottom:.7rem; margin:1.5rem 0 1rem; }
div[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:7px; padding:1rem; }
</style>
""", unsafe_allow_html=True)

from database.mongodb import authenticate_user, load_transactions, register_user, save_transaction
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if not st.session_state.authenticated_user:
    st.markdown('<div class="eyebrow">AI Financial Advisor / secure access</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero"><h1>Welcome back</h1><p>Sign in to access your financial dashboard, goals, predictions and reports.</p></div>', unsafe_allow_html=True)
    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")
        if submitted:
            try:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.authenticated_user = user
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
            except Exception:
                st.error("Unable to connect to MongoDB. Please try again.")
    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            new_email = st.text_input("Email address")
            new_password = st.text_input("Password", type="password")
            create_account = st.form_submit_button("Create account")
        if create_account:
            if not name.strip() or not new_email.strip() or len(new_password) < 8:
                st.error("Name, email and a password of at least 8 characters are required.")
            else:
                try:
                    register_user(name, new_email, new_password)
                    st.success("Account created. You can now sign in.")
                except ValueError as error:
                    st.error(str(error))
                except Exception:
                    st.error("Unable to connect to MongoDB. Please try again.")
    st.stop()

user_id = st.session_state.authenticated_user["id"]

if "transactions" not in st.session_state:
    try:
        stored_transactions = load_transactions(user_id)
        st.session_state.transactions = pd.DataFrame(stored_transactions) if stored_transactions else sample_transactions()
        st.session_state.database_connected = True
    except Exception:
        st.session_state.transactions = sample_transactions()
        st.session_state.database_connected = False

transactions = st.session_state.transactions
summary = analyze(transactions)

with st.sidebar:
    st.markdown("## $  Advisor")
    st.caption(f"Welcome, {st.session_state.authenticated_user['name']}")
    page = st.radio("Workspace", ["Dashboard", "Financial Analysis", "AI Advisor", "Goals", "Prediction", "Reports"], label_visibility="collapsed")
    st.divider()
    st.caption("MONGODB WORKSPACE" if st.session_state.database_connected else "LOCAL FALLBACK")
    st.caption("Transactions persist in MongoDB." if st.session_state.database_connected else "MongoDB unavailable; using sample data.")
    with st.expander("Notifications"):
        for alert in notifications(summary):
            st.markdown(f"**{alert['title']}**")
            st.caption(alert["message"])
    if st.button("Sign out"):
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="eyebrow">AI Financial Advisor / 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="hero"><h1>{page}</h1><p>A calm, data-led view of your money. Make the next decision with a little more signal.</p></div>', unsafe_allow_html=True)

if page == "Dashboard":
    st.subheader("Your month at a glance")
    cols = st.columns(4)
    for col, label, value, delta in zip(cols, ["Income", "Expenses", "Saved", "Health score"], [summary["income"], summary["expenses"], summary["savings"], summary["score"]], ["This period", "This period", f"{summary['savings_rate']:.1f}% rate", summary["risk"] + " risk"]):
        col.metric(label, f"${value:,.0f}" if label != "Health score" else f"{value}/100", delta)
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown('<div class="section-label"><b>Income vs expenses</b></div>', unsafe_allow_html=True)
        trend = pd.DataFrame({"Month":["Income", "Expenses", "Saved"], "Amount":[summary["income"], summary["expenses"], summary["savings"]]})
        st.plotly_chart(px.bar(trend, x="Month", y="Amount", color="Month", color_discrete_sequence=["#147d62", "#ef755f", "#8eb8a6"], template="simple_white"), use_container_width=True, config={"displayModeBar":False})
    with right:
        st.markdown('<div class="section-label"><b>Spending mix</b></div>', unsafe_allow_html=True)
        st.plotly_chart(px.pie(values=summary["category_spend"].values, names=summary["category_spend"].index, hole=.58, color_discrete_sequence=["#147d62","#ef755f","#e8aa62","#7397a8","#9bc6b3"], template="simple_white"), use_container_width=True, config={"displayModeBar":False})
elif page == "Financial Analysis":
    st.subheader("Patterns worth noticing")
    with st.expander("Add transaction"):
        with st.form("transaction_form", clear_on_submit=True):
            form_left, form_right = st.columns(2)
            with form_left:
                transaction_type = st.selectbox("Type", ["income", "expense"])
                category = st.text_input("Category", placeholder="e.g. Food")
                amount = st.number_input("Amount", min_value=0.01, step=10.0)
            with form_right:
                transaction_date = st.date_input("Date", value=date.today())
                description = st.text_input("Description")
            submitted = st.form_submit_button("Save transaction")
        if submitted:
            if not category.strip():
                st.error("Category is required.")
            else:
                new_transaction = {"date": transaction_date.isoformat(), "type": transaction_type, "category": category.strip(), "amount": amount, "description": description.strip()}
                try:
                    save_transaction(new_transaction, user_id)
                    st.session_state.database_connected = True
                    st.success("Transaction saved to MongoDB.")
                except Exception:
                    st.session_state.database_connected = False
                    st.warning("MongoDB unavailable. Transaction kept only for this session.")
                st.session_state.transactions = pd.concat([transactions, pd.DataFrame([new_transaction])], ignore_index=True)
                st.rerun()
    st.dataframe(transactions, use_container_width=True, hide_index=True)
    a, b, c = st.columns(3)
    a.metric("Savings rate", f"{summary['savings_rate']:.1f}%")
    b.metric("Expense ratio", f"{summary['expense_ratio']:.1f}%")
    c.metric("Risk classification", summary["risk"])
elif page == "AI Advisor":
    st.subheader("Recommendations for this period")
    for index, tip in enumerate(recommendations(summary), 1):
        st.info(f"{index:02d}  {tip}")
    if st.session_state.database_connected and st.button("Save alerts to MongoDB"):
        save_notifications(notifications(summary), user_id)
        st.success("Notifications saved.")
elif page == "Goals":
    st.subheader("Plan a target")
    left, right = st.columns(2)
    with left:
        target = st.number_input("Target amount", min_value=0.0, value=5000.0, step=100.0)
        current = st.number_input("Already saved", min_value=0.0, value=1000.0, step=100.0)
        target_date = st.date_input("Target date", value=date.today() + timedelta(days=180), min_value=date.today())
    with right:
        monthly = goal_plan(target, current, target_date)
        st.markdown(f'<div class="metric"><small>Required monthly saving</small><strong>${monthly:,.0f}</strong></div>', unsafe_allow_html=True)
        st.progress(min(1.0, current / target) if target else 0)
        st.caption(f"{current / target * 100:.0f}% of target complete" if target else "Set a target to begin.")
elif page == "Prediction":
    st.subheader("Forward view")
    months = st.slider("Projection horizon", 1, 12, 6)
    projected_savings = summary["savings"] * months
    projected_expenses = summary["expenses"] * months
    a, b = st.columns(2)
    a.metric(f"Projected savings / {months} months", f"${projected_savings:,.0f}")
    b.metric(f"Projected spending / {months} months", f"${projected_expenses:,.0f}")
    st.markdown("#### Model predictions")
    ml_result = predict_risk(summary["savings_rate"], summary["expense_ratio"], 0)
    st.metric("ML financial risk", f"{ml_result['risk']}", f"{float(ml_result['confidence']) * 100:.0f}% confidence")
    try:
        dl_result = predict_savings(summary["savings_rate"], summary["expense_ratio"], months)
        st.metric("DL projected savings rate", f"{dl_result['projected_savings_rate']}%", str(dl_result["model"]))
    except RuntimeError as error:
        st.warning(str(error))
    st.caption("ML uses Random Forest classification. DL uses a Keras neural network trained on normalized behavior features.")
else:
    st.subheader("Monthly report")
    report = f"AI FINANCIAL ADVISOR\n\nHealth score: {summary['score']}/100 ({summary['risk']} risk)\nIncome: ${summary['income']:,.2f}\nExpenses: ${summary['expenses']:,.2f}\nSavings: ${summary['savings']:,.2f}\nSavings rate: {summary['savings_rate']:.1f}%\n\nRECOMMENDATIONS\n" + "\n".join(f"- {tip}" for tip in recommendations(summary))
    st.download_button("Download report", report, "financial-report.txt", "text/plain")
    st.code(report, language="text")