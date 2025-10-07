# src/ui/sidebar.py
import streamlit as st
from src.data_handling.engine_manager import EngineManager

def display_sidebar(manager: EngineManager):
    st.sidebar.header("🔧 Панель управления")

    # Если пользователь не вошёл
    if not st.session_state.logged_in:
        with st.sidebar.expander("🔐 Войти", expanded=True):
            user_input = st.text_input("Логин", key="login_user")
            pwd_input = st.text_input("Пароль", type="password", key="login_pass")
            
            if st.button("Войти", use_container_width=True):
                is_valid, user_data = manager.check_login(user_input, pwd_input)
                if is_valid:
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.session_state.user_role = user_data["role"]
                    st.session_state.user_name = user_data["name"]
                    st.success(f"Добро пожаловать, {user_data['name']}!")
                    st.rerun()
                else:
                    st.sidebar.error("Неверный логин или пароль")
    else:
        # Пользователь вошёл
        st.sidebar.success(f"Вы вошли как:\n**{st.session_state.user_name}**")
        st.sidebar.info(f"Роль: {st.session_state.user_role.capitalize()}")
        
        if st.sidebar.button("Выйти", type="primary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_role = None
            st.rerun()