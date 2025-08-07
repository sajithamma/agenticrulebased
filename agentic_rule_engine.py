import streamlit as st
import json
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
from typing import Dict, List, Any, Optional
from action_executor import ActionExecutor

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class AgenticRuleEngine:
    """
    General-purpose agentic rule engine that can handle any feature with any parameters.
    Uses standardized format with [FEATURE] and [PARAMETER] identification.
    """
    
    def __init__(self, rules_file='agentic_rules.json'):
        self.rules_file = rules_file
        self.load_rules()
        self.features = self.extract_features()
        self.parameters = self.extract_parameters()
        self.action_executor = ActionExecutor()
    
    def load_rules(self):
        """Load rules from JSON file"""
        try:
            with open(self.rules_file, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = {
                "rule_sets": {},
                "user_assignments": {},
                "global_parameters": {},
                "feature_definitions": {}
            }
    
    def save_rules(self):
        """Save rules to JSON file"""
        with open(self.rules_file, 'w') as file:
            json.dump(self.data, file, indent=4)
    
    def extract_features(self) -> List[str]:
        """Extract all unique features from rules"""
        features = set()
        for rule_set in self.data['rule_sets'].values():
            for rule in rule_set['rules']:
                # Find all [FEATURE] patterns
                feature_matches = re.findall(r'\[([A-Z_]+)\]', rule)
                features.update(feature_matches)
        return list(features)
    
    def extract_parameters(self) -> List[str]:
        """Extract all unique parameters from rules"""
        parameters = set()
        for rule_set in self.data['rule_sets'].values():
            for rule in rule_set['rules']:
                # Find all [PARAMETER] patterns
                param_matches = re.findall(r'\[([A-Z_]+)\]', rule)
                parameters.update(param_matches)
        return list(parameters)
    
    def evaluate_feature_action(self, user: str, feature: str, action: str, 
                              parameters: Dict[str, Any], rule_set_id: Optional[str] = None, 
                              execute_action: bool = True) -> Dict[str, Any]:
        """
        Evaluate if a feature action is allowed based on rules.
        
        Args:
            user: User identifier
            feature: Feature name (e.g., 'ATTENDANCE', 'EXPENSE', 'LEAVE')
            action: Action to perform (e.g., 'CHECK-IN', 'SUBMIT', 'REQUEST')
            parameters: Dictionary of parameter values
            rule_set_id: Optional specific rule set to use
            execute_action: Whether to execute the action if allowed
        
        Returns:
            Dictionary with decision, reason, rule_violated, and execution result
        """
        if rule_set_id is None:
            rule_set_id = self.data['user_assignments'].get(user)
        
        if not rule_set_id or rule_set_id not in self.data['rule_sets']:
            return {
                "decision": "ERROR",
                "reason": f"No rule set found for user {user}",
                "rule_violated": None,
                "execution_result": None
            }
        
        rule_set = self.data['rule_sets'][rule_set_id]
        
        # Build context for LLM
        context = self.build_evaluation_context(feature, action, parameters, rule_set)
        
        # Evaluate with LLM
        evaluation_result = self.evaluate_with_llm(context)
        
        # Execute action if allowed and requested
        execution_result = None
        if execute_action and evaluation_result['decision'] == 'ALLOWED':
            execution_result = self.action_executor.execute_action(
                user=user,
                feature=feature,
                action=action,
                parameters=parameters,
                rule_evaluation=evaluation_result
            )
        
        # Combine results
        final_result = evaluation_result.copy()
        final_result['execution_result'] = execution_result
        
        return final_result
    
    def build_evaluation_context(self, feature: str, action: str, 
                               parameters: Dict[str, Any], rule_set: Dict) -> str:
        """Build context string for LLM evaluation"""
        
        # Format parameters for display
        param_display = []
        for param_name, param_value in parameters.items():
            if isinstance(param_value, datetime):
                param_display.append(f"• {param_name}: {param_value.strftime('%Y-%m-%d %H:%M')}")
            else:
                param_display.append(f"• {param_name}: {param_value}")
        
        context = f"""
        You are an intelligent rule evaluator for an agentic application system.
        
        **FEATURE:** [{feature}]
        **ACTION:** {action}
        **PARAMETERS:**
        {chr(10).join(param_display)}
        
        **APPLICABLE RULES:**
        {chr(10).join(f"• {rule}" for rule in rule_set['rules'])}
        
        **EVALUATION INSTRUCTIONS:**
        1. Identify which rules apply to the [{feature}] feature and {action} action
        2. Check if the provided parameters satisfy the rule conditions
        3. Consider any time, location, or other constraints mentioned in the rules
        4. Provide a clear decision with reasoning
        
        **RESPONSE FORMAT:**
        Decision: [ALLOWED/DENIED]
        Reason: [Brief explanation of which rule(s) were evaluated and why the decision was made]
        Rule Violated: [If denied, specify which rule was violated]
        """
        
        return context
    
    def evaluate_with_llm(self, context: str) -> Dict[str, Any]:
        """Evaluate rules using LLM"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert rule evaluator for agentic applications. Be precise and follow the response format exactly."},
                    {"role": "user", "content": context}
                ],
                max_tokens=300,
                temperature=0
            )
            
            result_text = response.choices[0].message.content
            return self.parse_llm_response(result_text)
            
        except Exception as e:
            return {
                "decision": "ERROR",
                "reason": f"Failed to evaluate rules: {str(e)}",
                "rule_violated": None
            }
    
    def parse_llm_response(self, response_text: str) -> Dict[str, Any]:
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
    
    def get_available_features(self) -> List[str]:
        """Get list of all available features"""
        return self.features
    
    def get_available_parameters(self) -> List[str]:
        """Get list of all available parameters"""
        return self.parameters
    
    def add_rule_set(self, name: str, rules: List[str]) -> str:
        """Add a new rule set"""
        rule_set_id = f"rule_set_{len(self.data['rule_sets']) + 1}"
        self.data['rule_sets'][rule_set_id] = {
            "name": name,
            "rules": rules
        }
        self.save_rules()
        # Refresh features and parameters
        self.features = self.extract_features()
        self.parameters = self.extract_parameters()
        return rule_set_id
    
    def assign_user_to_rule_set(self, user: str, rule_set_id: str) -> bool:
        """Assign a user to a rule set"""
        if rule_set_id in self.data['rule_sets']:
            self.data['user_assignments'][user] = rule_set_id
            self.save_rules()
            return True
        return False

def agentic_rule_interface():
    """Main interface for the agentic rule engine"""
    st.title("🤖 Agentic Rule Engine")
    st.markdown("**General-Purpose Feature-Parameter-Rule (FPR) Architecture**")
    
    # Initialize the rule engine
    engine = AgenticRuleEngine()
    
    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["🎯 Feature Actions", "📋 Rule Management", "🔧 System Configuration", "📊 Analytics", "📈 Action History"]
    )
    
    if page == "🎯 Feature Actions":
        feature_actions_page(engine)
    elif page == "📋 Rule Management":
        rule_management_page(engine)
    elif page == "🔧 System Configuration":
        system_config_page(engine)
    elif page == "📊 Analytics":
        analytics_page(engine)
    elif page == "📈 Action History":
        action_history_page(engine)

def feature_actions_page(engine: AgenticRuleEngine):
    """Main feature actions interface"""
    st.header("🎯 Feature Actions")
    
    # User selection
    available_users = list(engine.data['user_assignments'].keys())
    if not available_users:
        st.warning("No users configured. Please add users in Rule Management.")
        return
    
    user_choice = st.selectbox("Select User", available_users)
    
    # Feature selection
    available_features = engine.get_available_features()
    if not available_features:
        st.warning("No features found in rules. Please add rules with [FEATURE] tags.")
        return
    
    feature_choice = st.selectbox("Select Feature", available_features)
    
    # Action input
    action_choice = st.text_input("Enter Action", placeholder="e.g., CHECK-IN, SUBMIT, REQUEST")
    
    # Dynamic parameter input based on available parameters
    st.subheader("📝 Parameters")
    parameters = {}
    
    available_params = engine.get_available_parameters()
    for param in available_params:
        if param == "TIME":
            param_value = st.time_input(f"[{param}]", value=datetime.now().time())
            parameters[param] = param_value
        elif param == "DATE":
            param_value = st.date_input(f"[{param}]", value=datetime.now().date())
            parameters[param] = param_value
        elif param == "LOCATION":
            param_value = st.selectbox(f"[{param}]", ["Office", "Home", "Client Site", "Other"])
            parameters[param] = param_value
        elif param == "AMOUNT":
            param_value = st.number_input(f"[{param}]", min_value=0.0, value=0.0)
            parameters[param] = param_value
        elif param == "CATEGORY":
            param_value = st.selectbox(f"[{param}]", ["Travel", "Meals", "Equipment", "Training", "Other"])
            parameters[param] = param_value
        elif param == "TYPE":
            param_value = st.selectbox(f"[{param}]", ["Annual", "Sick", "Personal", "Maternity", "Paternity"])
            parameters[param] = param_value
        elif param == "VENDOR":
            param_value = st.text_input(f"[{param}]", placeholder="Enter vendor name")
            parameters[param] = param_value
        elif param == "ITEM":
            param_value = st.text_input(f"[{param}]", placeholder="Enter item name")
            parameters[param] = param_value
        elif param == "QUANTITY":
            param_value = st.number_input(f"[{param}]", min_value=1, value=1)
            parameters[param] = param_value
        elif param == "START_DATE":
            param_value = st.date_input(f"[{param}]", value=datetime.now().date())
            parameters[param] = param_value
        elif param == "END_DATE":
            param_value = st.date_input(f"[{param}]", value=datetime.now().date())
            parameters[param] = param_value
        else:
            param_value = st.text_input(f"[{param}]", placeholder=f"Enter {param}")
            parameters[param] = param_value
    
    # Action execution options
    col1, col2 = st.columns(2)
    
    with col1:
        execute_action = st.checkbox("🚀 Execute Action if Allowed", value=True)
    
    with col2:
        if st.button("🔍 Evaluate Only", type="secondary"):
            execute_action = False
    
    # Execute action
    if st.button("🚀 Execute Action", type="primary"):
        if action_choice and parameters:
            with st.spinner("Evaluating rules with AI..."):
                result = engine.evaluate_feature_action(
                    user=user_choice,
                    feature=feature_choice,
                    action=action_choice,
                    parameters=parameters,
                    execute_action=execute_action
                )
                display_agentic_result(result, feature_choice, action_choice)
        else:
            st.error("Please provide both action and parameters.")

def display_agentic_result(result: Dict[str, Any], feature: str, action: str):
    """Display the evaluation result"""
    st.subheader(f"🤖 AI Evaluation Result")
    
    if result["decision"] == "ALLOWED":
        st.success(f"✅ [{feature}] {action} **ALLOWED**")
        st.write(f"**Reason:** {result['reason']}")
        
        # Show execution result if available
        if result.get('execution_result'):
            exec_result = result['execution_result']
            if exec_result.get('success'):
                st.success(f"🎯 **Action Executed:** {exec_result['message']}")
                st.info(f"**Action ID:** {exec_result.get('action_id', 'N/A')}")
                st.info(f"**Timestamp:** {exec_result.get('timestamp', 'N/A')}")
            else:
                st.error(f"❌ **Execution Failed:** {exec_result['message']}")
        else:
            st.info("🎯 **Next Steps:** Action can be executed. Consider implementing action execution logic here.")
        
    elif result["decision"] == "DENIED":
        st.error(f"❌ [{feature}] {action} **DENIED**")
        st.write(f"**Reason:** {result['reason']}")
        if result["rule_violated"]:
            st.warning(f"**Rule Violated:** {result['rule_violated']}")
            
    else:
        st.warning(f"⚠️ [{feature}] {action} **EVALUATION ERROR**")
        st.write(f"**Issue:** {result['reason']}")

def action_history_page(engine: AgenticRuleEngine):
    """Action history page"""
    st.header("📈 Action History")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        user_filter = st.text_input("Filter by User", placeholder="Enter user ID")
    
    with col2:
        feature_filter = st.selectbox("Filter by Feature", 
                                    ["All", "ATTENDANCE", "EXPENSE", "LEAVE", "PURCHASE"])
    
    with col3:
        limit = st.number_input("Limit Results", min_value=10, max_value=200, value=50)
    
    # Get history
    if st.button("🔍 Load History"):
        feature = None if feature_filter == "All" else feature_filter
        user = user_filter if user_filter else None
        
        history = engine.action_executor.get_action_history(user=user, feature=feature, limit=limit)
        
        if history and not history[0].get('error'):
            st.subheader(f"📈 Action History ({len(history)} records)")
            
            # Display as table
            if history:
                df_data = []
                for record in history:
                    row = {
                        'User': record.get('user_id', 'N/A'),
                        'Action': record.get('action', 'N/A'),
                        'Timestamp': record.get('timestamp', 'N/A'),
                        'Status': record.get('status', 'N/A'),
                        'Table': record.get('table', 'N/A')
                    }
                    
                    # Add feature-specific fields
                    if 'location' in record:
                        row['Location'] = record['location']
                    if 'amount' in record:
                        row['Amount'] = f"${record['amount']}" if record['amount'] else 'N/A'
                    if 'category' in record:
                        row['Category'] = record['category']
                    if 'leave_type' in record:
                        row['Leave Type'] = record['leave_type']
                    if 'days' in record:
                        row['Days'] = record['days']
                    if 'vendor' in record:
                        row['Vendor'] = record['vendor']
                    if 'item' in record:
                        row['Item'] = record['item']
                    
                    df_data.append(row)
                
                st.dataframe(df_data, use_container_width=True)
        else:
            st.error(f"Failed to load history: {history[0].get('error', 'Unknown error')}")

def rule_management_page(engine: AgenticRuleEngine):
    """Rule management interface"""
    st.header("📋 Rule Management")
    
    # Add new rule set
    with st.expander("➕ Add New Rule Set", expanded=True):
        with st.form("add_rule_set"):
            rule_set_name = st.text_input("Rule Set Name", placeholder="e.g., Finance Policy")
            
            st.write("**Rules (use [FEATURE] and [PARAMETER] tags):**")
            rules_text = st.text_area(
                "Enter rules in natural language",
                placeholder="[EXPENSE] can only be [SUBMIT] if [AMOUNT] is less than 1000.\n[ATTENDANCE] can only be [CHECK-IN] at [LOCATION] after [TIME] 08:00.",
                height=200
            )
            
            submitted = st.form_submit_button("Add Rule Set")
            
            if submitted and rule_set_name and rules_text:
                rules = [rule.strip() for rule in rules_text.split('\n') if rule.strip()]
                if rules:
                    rule_set_id = engine.add_rule_set(rule_set_name, rules)
                    st.success(f"✅ Rule set '{rule_set_name}' added successfully!")
                    st.info(f"Rule Set ID: {rule_set_id}")
                else:
                    st.error("Please enter at least one rule.")
    
    # View current rules
    st.subheader("📋 Current Rule Sets")
    for rule_set_id, rule_set in engine.data['rule_sets'].items():
        with st.expander(f"📋 {rule_set['name']} ({rule_set_id})"):
            st.write("**Rules:**")
            for i, rule in enumerate(rule_set['rules'], 1):
                st.write(f"{i}. {rule}")
            
            st.write("**Assigned Users:**")
            assigned_users = [user for user, assigned_rule_set in engine.data['user_assignments'].items() 
                            if assigned_rule_set == rule_set_id]
            if assigned_users:
                for user in assigned_users:
                    st.write(f"• {user}")
            else:
                st.write("No users assigned")
    
    # User assignments
    st.subheader("👥 User Assignments")
    with st.form("assign_user"):
        new_user = st.text_input("User ID", placeholder="e.g., user_3")
        
        if engine.data['rule_sets']:
            rule_set_options = {rule_set['name']: rule_set_id 
                               for rule_set_id, rule_set in engine.data['rule_sets'].items()}
            selected_rule_set = st.selectbox("Rule Set", list(rule_set_options.keys()))
            rule_set_id = rule_set_options[selected_rule_set]
        else:
            st.warning("No rule sets available.")
            rule_set_id = None
        
        if st.form_submit_button("Assign User") and new_user and rule_set_id:
            engine.assign_user_to_rule_set(new_user, rule_set_id)
            st.success(f"✅ User '{new_user}' assigned successfully!")

def system_config_page(engine: AgenticRuleEngine):
    """System configuration page"""
    st.header("🔧 System Configuration")
    
    # Available features and parameters
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Available Features")
        features = engine.get_available_features()
        if features:
            for feature in features:
                st.write(f"• [{feature}]")
        else:
            st.info("No features found in rules.")
    
    with col2:
        st.subheader("📝 Available Parameters")
        parameters = engine.get_available_parameters()
        if parameters:
            for param in parameters:
                st.write(f"• [{param}]")
        else:
            st.info("No parameters found in rules.")
    
    # Export/Import
    st.subheader("📤 Export/Import")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Export Configuration"):
            st.download_button(
                label="Download agentic_rules.json",
                data=json.dumps(engine.data, indent=4),
                file_name="agentic_rules_export.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_file = st.file_uploader("Import configuration", type=['json'])
        if uploaded_file is not None:
            try:
                imported_data = json.load(uploaded_file)
                if st.button("📥 Import Configuration"):
                    engine.data = imported_data
                    engine.save_rules()
                    st.success("✅ Configuration imported successfully!")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file")

def analytics_page(engine: AgenticRuleEngine):
    """Analytics and insights page"""
    st.header("📊 Analytics")
    
    # System statistics
    st.subheader("📈 System Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Rule Sets", len(engine.data['rule_sets']))
    
    with col2:
        st.metric("Total Users", len(engine.data['user_assignments']))
    
    with col3:
        st.metric("Available Features", len(engine.get_available_features()))
    
    # Feature distribution
    st.subheader("🎯 Feature Distribution")
    features = engine.get_available_features()
    if features:
        feature_counts = {}
        for rule_set in engine.data['rule_sets'].values():
            for rule in rule_set['rules']:
                feature_matches = re.findall(r'\[([A-Z_]+)\]', rule)
                for feature in feature_matches:
                    feature_counts[feature] = feature_counts.get(feature, 0) + 1
        
        if feature_counts:
            for feature, count in feature_counts.items():
                st.write(f"• [{feature}]: {count} rules")
    
    # Rule complexity analysis
    st.subheader("🧠 Rule Complexity Analysis")
    total_rules = sum(len(rule_set['rules']) for rule_set in engine.data['rule_sets'].values())
    avg_rules_per_set = total_rules / len(engine.data['rule_sets']) if engine.data['rule_sets'] else 0
    
    st.write(f"• **Total Rules:** {total_rules}")
    st.write(f"• **Average Rules per Set:** {avg_rules_per_set:.1f}")
    st.write(f"• **Total Parameters:** {len(engine.get_available_parameters())}")

if __name__ == "__main__":
    agentic_rule_interface() 