import streamlit as st
import json
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def evaluate_attendance_rules(user, action, time, location, rule_set):
    """AI-native rule evaluation using LLM"""
    prompt = f"""
    You are an intelligent attendance rule evaluator. Analyze the following scenario:

    **USER:** {user}
    **ACTION:** {action}
    **TIME:** {time.strftime('%H:%M')}
    **LOCATION:** {location}
    **PROJECT LOCATION:** {project_location}

    **APPLICABLE RULES:**
    {chr(10).join(f"• {rule}" for rule in rule_set['rules'])}

    **EVALUATION INSTRUCTIONS:**
    1. Check if the action (CHECK-IN/CHECK-OUT) is allowed based on the rules
    2. Consider time constraints, location requirements, and any other relevant rules
    3. Provide a clear decision with reasoning

    **RESPONSE FORMAT:**
    Decision: [ALLOWED/DENIED]
    Reason: [Brief explanation of which rule(s) were evaluated and why the decision was made]
    Rule Violated: [If denied, specify which rule was violated]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert attendance rule evaluator. Be precise and follow the response format exactly."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0
        )
        
        result_text = response.choices[0].message.content
        return parse_llm_response(result_text)
        
    except Exception as e:
        return {
            "decision": "ERROR",
            "reason": f"Failed to evaluate rules: {str(e)}",
            "rule_violated": None
        }

def parse_llm_response(response_text):
    """Parse the LLM response into structured format"""
    lines = response_text.strip().split('\n')
    result = {
        "decision": "UNKNOWN",
        "reason": "No clear decision provided",
        "rule_violated": None
    }
    
    for line in lines:
        line = line.strip()
        if line.startswith("Decision:"):
            decision = line.replace("Decision:", "").strip()
            result["decision"] = decision
        elif line.startswith("Reason:"):
            reason = line.replace("Reason:", "").strip()
            result["reason"] = reason
        elif line.startswith("Rule Violated:"):
            rule_violated = line.replace("Rule Violated:", "").strip()
            result["rule_violated"] = rule_violated if rule_violated != "None" else None
    
    return result

def display_result(result, action):
    """Display the evaluation result with appropriate styling"""
    st.subheader(f"🤖 AI Evaluation Result")
    
    if result["decision"] == "ALLOWED":
        st.success(f"✅ {action} **ALLOWED**")
        st.write(f"**Reason:** {result['reason']}")
    elif result["decision"] == "DENIED":
        st.error(f"❌ {action} **DENIED**")
        st.write(f"**Reason:** {result['reason']}")
        if result["rule_violated"]:
            st.warning(f"**Rule Violated:** {result['rule_violated']}")
    else:
        st.warning(f"⚠️ {action} **EVALUATION ERROR**")
        st.write(f"**Issue:** {result['reason']}")

def analyze_rules(rule_set, time, location):
    """Analyze how rules would apply to current context"""
    st.subheader("🔍 Rule Analysis")
    
    analysis_prompt = f"""
    Analyze how each rule in the rule set would apply to this context:
    
    **Context:**
    - Time: {time.strftime('%H:%M')}
    - Location: {location}
    - Project Location: {project_location}
    
    **Rules:**
    {chr(10).join(f"• {rule}" for rule in rule_set['rules'])}
    
    For each rule, explain:
    1. How it applies to CHECK-IN
    2. How it applies to CHECK-OUT
    3. Whether the current context satisfies the rule
    
    Provide a clear, structured analysis.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert rule analyst. Provide clear, structured analysis."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=400,
            temperature=0
        )
        
        st.write(response.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Failed to analyze rules: {str(e)}")

# Load rules
with open('rules.json') as file:
    data = json.load(file)

rule_sets = data['rule_sets']
user_assignments = data['user_assignments']
project_location = data['project_location']

# Initialize session state for time input
if 'checkin_time' not in st.session_state:
    st.session_state.checkin_time = datetime.now().time()

# Streamlit UI
st.title("🧑‍💻 LLM-based Attendance App")
st.markdown("**AI-Native Rule Engine** - Rules defined in natural language, evaluated by LLM")

# Sidebar for rule management
with st.sidebar:
    st.header("📋 Rule Management")
    st.write("**Current Rule Sets:**")
    for rule_set_id, rule_set in rule_sets.items():
        with st.expander(f"{rule_set['name']} ({rule_set_id})"):
            for i, rule in enumerate(rule_set['rules'], 1):
                st.write(f"{i}. {rule}")
    
    st.write("**User Assignments:**")
    for user, rule_set in user_assignments.items():
        st.write(f"• {user} → {rule_sets[rule_set]['name']}")

# Main interface
col1, col2 = st.columns(2)

with col1:
    st.subheader("👤 User Selection")
    user_choice = st.selectbox("Select User", ["user_1", "user_2"])
    current_rule_set_key = user_assignments[user_choice]
    current_rule_set = rule_sets[current_rule_set_key]
    
    st.info(f"**Active Rules for {user_choice}:**")
    for i, rule in enumerate(current_rule_set["rules"], 1):
        st.write(f"{i}. {rule}")

with col2:
    st.subheader("⏰ Check-In Details")
    checkin_time = st.time_input("Select Check-In Time", value=st.session_state.checkin_time)
    # Update session state when time changes
    st.session_state.checkin_time = checkin_time
    
    location_choice = st.selectbox("Select Location", [project_location, "Home", "Other"])
    
    # Display current context
    st.write("**Current Context:**")
    st.write(f"• Time: {checkin_time.strftime('%H:%M')}")
    st.write(f"• Location: {location_choice}")
    st.write(f"• Project Location: {project_location}")

# Action buttons
st.subheader("🎯 Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("✅ CHECK-IN", type="primary"):
        action = "CHECK-IN"
        with st.spinner("Evaluating rules with AI..."):
            result = evaluate_attendance_rules(user_choice, action, checkin_time, location_choice, current_rule_set)
            display_result(result, action)

with col2:
    if st.button("🚪 CHECK-OUT"):
        action = "CHECK-OUT"
        with st.spinner("Evaluating rules with AI..."):
            result = evaluate_attendance_rules(user_choice, action, checkin_time, location_choice, current_rule_set)
            display_result(result, action)

with col3:
    if st.button("📊 RULE ANALYSIS"):
        analyze_rules(current_rule_set, checkin_time, location_choice)
