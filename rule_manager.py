import streamlit as st
import json
from datetime import datetime
import os

class RuleManager:
    def __init__(self, rules_file='rules.json'):
        self.rules_file = rules_file
        self.load_rules()
    
    def load_rules(self):
        """Load rules from JSON file"""
        try:
            with open(self.rules_file, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = {
                "rule_sets": {},
                "user_assignments": {},
                "project_location": "Default Location"
            }
    
    def save_rules(self):
        """Save rules to JSON file"""
        with open(self.rules_file, 'w') as file:
            json.dump(self.data, file, indent=4)
    
    def add_rule_set(self, name, rules):
        """Add a new rule set"""
        rule_set_id = f"rule_set_{len(self.data['rule_sets']) + 1}"
        self.data['rule_sets'][rule_set_id] = {
            "name": name,
            "rules": rules
        }
        return rule_set_id
    
    def update_rule_set(self, rule_set_id, name, rules):
        """Update an existing rule set"""
        if rule_set_id in self.data['rule_sets']:
            self.data['rule_sets'][rule_set_id] = {
                "name": name,
                "rules": rules
            }
            return True
        return False
    
    def delete_rule_set(self, rule_set_id):
        """Delete a rule set"""
        if rule_set_id in self.data['rule_sets']:
            del self.data['rule_sets'][rule_set_id]
            # Remove user assignments that reference this rule set
            users_to_remove = []
            for user, assigned_rule_set in self.data['user_assignments'].items():
                if assigned_rule_set == rule_set_id:
                    users_to_remove.append(user)
            for user in users_to_remove:
                del self.data['user_assignments'][user]
            return True
        return False
    
    def assign_user_to_rule_set(self, user, rule_set_id):
        """Assign a user to a rule set"""
        if rule_set_id in self.data['rule_sets']:
            self.data['user_assignments'][user] = rule_set_id
            return True
        return False

def rule_management_interface():
    """Streamlit interface for rule management"""
    st.title("🔧 Rule Management Interface")
    st.markdown("**AI-Native Rule Engine Management** - Edit rules in natural language")
    
    # Initialize rule manager
    rule_manager = RuleManager()
    
    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["📋 View Rules", "➕ Add Rule Set", "✏️ Edit Rule Set", "👥 Manage Users", "⚙️ Settings"]
    )
    
    if page == "📋 View Rules":
        view_rules_page(rule_manager)
    elif page == "➕ Add Rule Set":
        add_rule_set_page(rule_manager)
    elif page == "✏️ Edit Rule Set":
        edit_rule_set_page(rule_manager)
    elif page == "👥 Manage Users":
        manage_users_page(rule_manager)
    elif page == "⚙️ Settings":
        settings_page(rule_manager)

def view_rules_page(rule_manager):
    """Display all current rules"""
    st.header("📋 Current Rules")
    
    # Display rule sets
    for rule_set_id, rule_set in rule_manager.data['rule_sets'].items():
        with st.expander(f"📋 {rule_set['name']} ({rule_set_id})", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write("**Rules:**")
                for i, rule in enumerate(rule_set['rules'], 1):
                    st.write(f"{i}. {rule}")
            
            with col2:
                st.write("**Assigned Users:**")
                assigned_users = [user for user, rule_set_assigned in rule_manager.data['user_assignments'].items() 
                                if rule_set_assigned == rule_set_id]
                if assigned_users:
                    for user in assigned_users:
                        st.write(f"• {user}")
                else:
                    st.write("No users assigned")
    
    # Display user assignments
    st.subheader("👥 User Assignments")
    for user, rule_set_id in rule_manager.data['user_assignments'].items():
        rule_set_name = rule_manager.data['rule_sets'][rule_set_id]['name']
        st.write(f"• **{user}** → {rule_set_name} ({rule_set_id})")

def add_rule_set_page(rule_manager):
    """Add a new rule set"""
    st.header("➕ Add New Rule Set")
    
    with st.form("add_rule_set"):
        rule_set_name = st.text_input("Rule Set Name", placeholder="e.g., Flexible Work Policy")
        
        st.write("**Rules (one per line):**")
        rules_text = st.text_area(
            "Enter rules in natural language",
            placeholder="ATTENDANCE can be CHECKED-IN from anywhere.\nCHECK-IN allowed only after 10:00.\nCHECK-OUT not allowed after 23:30.",
            height=200
        )
        
        submitted = st.form_submit_button("Add Rule Set")
        
        if submitted and rule_set_name and rules_text:
            rules = [rule.strip() for rule in rules_text.split('\n') if rule.strip()]
            if rules:
                rule_set_id = rule_manager.add_rule_set(rule_set_name, rules)
                rule_manager.save_rules()
                st.success(f"✅ Rule set '{rule_set_name}' added successfully!")
                st.info(f"Rule Set ID: {rule_set_id}")
            else:
                st.error("Please enter at least one rule.")

def edit_rule_set_page(rule_manager):
    """Edit existing rule sets"""
    st.header("✏️ Edit Rule Set")
    
    if not rule_manager.data['rule_sets']:
        st.warning("No rule sets available to edit.")
        return
    
    # Select rule set to edit
    rule_set_options = {f"{rule_set['name']} ({rule_set_id})": rule_set_id 
                       for rule_set_id, rule_set in rule_manager.data['rule_sets'].items()}
    
    selected_rule_set = st.selectbox("Select Rule Set to Edit", list(rule_set_options.keys()))
    rule_set_id = rule_set_options[selected_rule_set]
    rule_set = rule_manager.data['rule_sets'][rule_set_id]
    
    with st.form("edit_rule_set"):
        new_name = st.text_input("Rule Set Name", value=rule_set['name'])
        
        st.write("**Rules (one per line):**")
        current_rules_text = '\n'.join(rule_set['rules'])
        new_rules_text = st.text_area("Edit rules", value=current_rules_text, height=200)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Save Changes"):
                new_rules = [rule.strip() for rule in new_rules_text.split('\n') if rule.strip()]
                if new_rules:
                    rule_manager.update_rule_set(rule_set_id, new_name, new_rules)
                    rule_manager.save_rules()
                    st.success("✅ Rule set updated successfully!")
                else:
                    st.error("Please enter at least one rule.")
        
        with col2:
            if st.form_submit_button("🗑️ Delete Rule Set"):
                if rule_manager.delete_rule_set(rule_set_id):
                    rule_manager.save_rules()
                    st.success("✅ Rule set deleted successfully!")
                    st.rerun()

def manage_users_page(rule_manager):
    """Manage user assignments"""
    st.header("👥 Manage User Assignments")
    
    # Add new user assignment
    st.subheader("➕ Assign User to Rule Set")
    
    with st.form("assign_user"):
        new_user = st.text_input("User ID", placeholder="e.g., user_3")
        
        if rule_manager.data['rule_sets']:
            rule_set_options = {rule_set['name']: rule_set_id 
                               for rule_set_id, rule_set in rule_manager.data['rule_sets'].items()}
            selected_rule_set = st.selectbox("Rule Set", list(rule_set_options.keys()))
            rule_set_id = rule_set_options[selected_rule_set]
        else:
            st.warning("No rule sets available. Please create a rule set first.")
            rule_set_id = None
        
        if st.form_submit_button("Assign User") and new_user and rule_set_id:
            rule_manager.assign_user_to_rule_set(new_user, rule_set_id)
            rule_manager.save_rules()
            st.success(f"✅ User '{new_user}' assigned to rule set successfully!")
    
    # Remove user assignments
    st.subheader("🗑️ Remove User Assignments")
    if rule_manager.data['user_assignments']:
        for user, rule_set_id in rule_manager.data['user_assignments'].items():
            rule_set_name = rule_manager.data['rule_sets'][rule_set_id]['name']
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**{user}** → {rule_set_name}")
            
            with col2:
                if st.button(f"Remove {user}", key=f"remove_{user}"):
                    del rule_manager.data['user_assignments'][user]
                    rule_manager.save_rules()
                    st.success(f"✅ User '{user}' assignment removed!")
                    st.rerun()
    else:
        st.info("No user assignments to display.")

def settings_page(rule_manager):
    """Settings and configuration"""
    st.header("⚙️ Settings")
    
    st.subheader("📍 Project Location")
    current_location = rule_manager.data.get('project_location', 'Default Location')
    new_location = st.text_input("Project Location", value=current_location)
    
    if st.button("💾 Save Location"):
        rule_manager.data['project_location'] = new_location
        rule_manager.save_rules()
        st.success("✅ Project location updated!")
    
    st.subheader("📊 System Information")
    st.write(f"• **Total Rule Sets:** {len(rule_manager.data['rule_sets'])}")
    st.write(f"• **Total Users:** {len(rule_manager.data['user_assignments'])}")
    st.write(f"• **Rules File:** {rule_manager.rules_file}")
    
    # Export/Import functionality
    st.subheader("📤 Export/Import")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Export Rules"):
            st.download_button(
                label="Download rules.json",
                data=json.dumps(rule_manager.data, indent=4),
                file_name="rules_export.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_file = st.file_uploader("Import rules.json", type=['json'])
        if uploaded_file is not None:
            try:
                imported_data = json.load(uploaded_file)
                if st.button("📥 Import Rules"):
                    rule_manager.data = imported_data
                    rule_manager.save_rules()
                    st.success("✅ Rules imported successfully!")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file")

if __name__ == "__main__":
    rule_management_interface() 