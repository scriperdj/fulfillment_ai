"""
Streamlit Dashboard Application (Stretch Goal)
Interactive monitoring and management UI for fulfillment_ai
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="fulfillment_ai Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📊 fulfillment_ai - Operations Dashboard")
    st.markdown("Autonomous AI-driven fulfillment operations monitoring")

    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page:",
            [
                "Dashboard",
                "Orders",
                "Agents",
                "Knowledge Base",
                "Settings",
            ],
        )

    # Page routing
    if page == "Dashboard":
        from ui.pages.dashboard import show_dashboard
        show_dashboard()
    elif page == "Orders":
        from ui.pages.orders import show_orders
        show_orders()
    elif page == "Agents":
        from ui.pages.agents import show_agents
        show_agents()
    elif page == "Knowledge Base":
        from ui.pages.knowledge_base import show_kb
        show_kb()
    elif page == "Settings":
        from ui.pages.settings import show_settings
        show_settings()

    # Footer
    st.markdown("---")
    st.markdown(
        "🚀 fulfillment_ai | Built for Celonis Garage | "
        "[Docs](https://github.com/scriperdj/fulfillment_ai)"
    )


if __name__ == "__main__":
    main()
