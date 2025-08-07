import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import sqlite3
import os

class ActionExecutor:
    """
    Executes actions when allowed by the agentic rule engine.
    This demonstrates how actions can be performed automatically after LLM approval.
    """
    
    def __init__(self, db_file='actions.db'):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for action logging"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create tables for different features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                timestamp DATETIME,
                location TEXT,
                status TEXT,
                rule_evaluation TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expense_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                amount REAL,
                category TEXT,
                timestamp DATETIME,
                status TEXT,
                rule_evaluation TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                leave_type TEXT,
                start_date DATE,
                end_date DATE,
                days INTEGER,
                timestamp DATETIME,
                status TEXT,
                rule_evaluation TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                amount REAL,
                vendor TEXT,
                item TEXT,
                quantity INTEGER,
                timestamp DATETIME,
                status TEXT,
                rule_evaluation TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_attendance_action(self, user: str, action: str, parameters: Dict[str, Any], 
                                rule_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute attendance-related actions"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            location = parameters.get('LOCATION', 'Unknown')
            
            cursor.execute('''
                INSERT INTO attendance_logs (user_id, action, timestamp, location, status, rule_evaluation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user, action, timestamp, location, rule_evaluation['decision'], 
                  json.dumps(rule_evaluation)))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"✅ {action} executed successfully for {user}",
                "timestamp": timestamp,
                "action_id": cursor.lastrowid
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Failed to execute {action}: {str(e)}"
            }
    
    def execute_expense_action(self, user: str, action: str, parameters: Dict[str, Any], 
                             rule_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute expense-related actions"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            amount = parameters.get('AMOUNT', 0.0)
            category = parameters.get('CATEGORY', 'General')
            
            cursor.execute('''
                INSERT INTO expense_logs (user_id, action, amount, category, timestamp, status, rule_evaluation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user, action, amount, category, timestamp, rule_evaluation['decision'], 
                  json.dumps(rule_evaluation)))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"✅ {action} executed successfully for {user} - Amount: ${amount}",
                "timestamp": timestamp,
                "action_id": cursor.lastrowid
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Failed to execute {action}: {str(e)}"
            }
    
    def execute_leave_action(self, user: str, action: str, parameters: Dict[str, Any], 
                           rule_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute leave-related actions"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            leave_type = parameters.get('TYPE', 'Annual')
            start_date = parameters.get('START_DATE', datetime.now().date())
            end_date = parameters.get('END_DATE', datetime.now().date())
            days = parameters.get('AMOUNT', 1)
            
            cursor.execute('''
                INSERT INTO leave_requests (user_id, action, leave_type, start_date, end_date, days, timestamp, status, rule_evaluation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user, action, leave_type, start_date, end_date, days, timestamp, 
                  rule_evaluation['decision'], json.dumps(rule_evaluation)))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"✅ {action} executed successfully for {user} - {days} days {leave_type} leave",
                "timestamp": timestamp,
                "action_id": cursor.lastrowid
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Failed to execute {action}: {str(e)}"
            }
    
    def execute_purchase_action(self, user: str, action: str, parameters: Dict[str, Any], 
                              rule_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute purchase-related actions"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            timestamp = datetime.now()
            amount = parameters.get('AMOUNT', 0.0)
            vendor = parameters.get('VENDOR', 'Unknown')
            item = parameters.get('ITEM', 'Unknown')
            quantity = parameters.get('QUANTITY', 1)
            
            cursor.execute('''
                INSERT INTO purchase_requests (user_id, action, amount, vendor, item, quantity, timestamp, status, rule_evaluation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user, action, amount, vendor, item, quantity, timestamp, 
                  rule_evaluation['decision'], json.dumps(rule_evaluation)))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"✅ {action} executed successfully for {user} - {quantity}x {item} from {vendor}",
                "timestamp": timestamp,
                "action_id": cursor.lastrowid
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Failed to execute {action}: {str(e)}"
            }
    
    def execute_action(self, user: str, feature: str, action: str, parameters: Dict[str, Any], 
                      rule_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Main action execution method"""
        
        if rule_evaluation['decision'] != 'ALLOWED':
            return {
                "success": False,
                "message": f"❌ Action not executed - Rule evaluation: {rule_evaluation['decision']}"
            }
        
        # Route to appropriate executor based on feature
        if feature == 'ATTENDANCE':
            return self.execute_attendance_action(user, action, parameters, rule_evaluation)
        elif feature == 'EXPENSE':
            return self.execute_expense_action(user, action, parameters, rule_evaluation)
        elif feature == 'LEAVE':
            return self.execute_leave_action(user, action, parameters, rule_evaluation)
        elif feature == 'PURCHASE':
            return self.execute_purchase_action(user, action, parameters, rule_evaluation)
        else:
            return {
                "success": False,
                "message": f"❌ No executor found for feature: {feature}"
            }
    
    def get_action_history(self, user: Optional[str] = None, feature: Optional[str] = None, 
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Get action history from database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Determine which table to query based on feature
            if feature == 'ATTENDANCE':
                table = 'attendance_logs'
                columns = ['user_id', 'action', 'timestamp', 'location', 'status']
            elif feature == 'EXPENSE':
                table = 'expense_logs'
                columns = ['user_id', 'action', 'amount', 'category', 'timestamp', 'status']
            elif feature == 'LEAVE':
                table = 'leave_requests'
                columns = ['user_id', 'action', 'leave_type', 'days', 'timestamp', 'status']
            elif feature == 'PURCHASE':
                table = 'purchase_requests'
                columns = ['user_id', 'action', 'amount', 'vendor', 'item', 'timestamp', 'status']
            else:
                # Get from all tables
                return self.get_all_action_history(user, limit)
            
            # Build query
            query = f"SELECT {', '.join(columns)} FROM {table}"
            params = []
            
            if user:
                query += " WHERE user_id = ?"
                params.append(user)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            history = []
            for row in rows:
                history.append(dict(zip(columns, row)))
            
            conn.close()
            return history
            
        except Exception as e:
            return [{"error": f"Failed to get history: {str(e)}"}]
    
    def get_all_action_history(self, user: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get action history from all tables"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            all_history = []
            
            # Get from each table
            tables = [
                ('attendance_logs', ['user_id', 'action', 'timestamp', 'location', 'status']),
                ('expense_logs', ['user_id', 'action', 'amount', 'category', 'timestamp', 'status']),
                ('leave_requests', ['user_id', 'action', 'leave_type', 'days', 'timestamp', 'status']),
                ('purchase_requests', ['user_id', 'action', 'amount', 'vendor', 'item', 'timestamp', 'status'])
            ]
            
            for table, columns in tables:
                query = f"SELECT {', '.join(columns)} FROM {table}"
                params = []
                
                if user:
                    query += " WHERE user_id = ?"
                    params.append(user)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit // len(tables))  # Distribute limit across tables
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                for row in rows:
                    record = dict(zip(columns, row))
                    record['table'] = table  # Add table identifier
                    all_history.append(record)
            
            # Sort by timestamp and limit
            all_history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            conn.close()
            
            return all_history[:limit]
            
        except Exception as e:
            return [{"error": f"Failed to get history: {str(e)}"}]

def action_history_interface():
    """Interface for viewing action history"""
    st.title("📊 Action History & Analytics")
    
    executor = ActionExecutor()
    
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
        
        history = executor.get_action_history(user=user, feature=feature, limit=limit)
        
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
    
    # Statistics
    st.subheader("📊 Quick Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📈 Attendance Stats"):
            history = executor.get_action_history(feature='ATTENDANCE', limit=1000)
            if history and not history[0].get('error'):
                st.metric("Total Attendance Actions", len(history))
                checkins = len([h for h in history if h.get('action') == 'CHECK-IN'])
                st.metric("Check-ins", checkins)
    
    with col2:
        if st.button("💰 Expense Stats"):
            history = executor.get_action_history(feature='EXPENSE', limit=1000)
            if history and not history[0].get('error'):
                st.metric("Total Expense Actions", len(history))
                total_amount = sum([h.get('amount', 0) for h in history])
                st.metric("Total Amount", f"${total_amount:,.2f}")
    
    with col3:
        if st.button("🏖️ Leave Stats"):
            history = executor.get_action_history(feature='LEAVE', limit=1000)
            if history and not history[0].get('error'):
                st.metric("Total Leave Actions", len(history))
                total_days = sum([h.get('days', 0) for h in history])
                st.metric("Total Days", total_days)
    
    with col4:
        if st.button("🛒 Purchase Stats"):
            history = executor.get_action_history(feature='PURCHASE', limit=1000)
            if history and not history[0].get('error'):
                st.metric("Total Purchase Actions", len(history))
                total_amount = sum([h.get('amount', 0) for h in history])
                st.metric("Total Amount", f"${total_amount:,.2f}")

if __name__ == "__main__":
    action_history_interface() 