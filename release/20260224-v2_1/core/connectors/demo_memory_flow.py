"""
Demo: Automatic Memory Flow
===========================
Shows how IDE connector works in practice.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.ide_connector import get_connector

def simulate_conversation():
    """Simulate how I use memory automatically."""
    
    connector = get_connector()
    print("🧙 Klaus (with automatic memory)")
    print("=" * 50)
    
    # Simulated conversation
    conversations = [
        ("My name is Mateus and I'm an AI Solutions Architect", 
         "Got it! I'll remember you're Mateus, an AI Solutions Architect."),
        
        ("I prefer concise responses with bullet points",
         "Noted. I'll keep my responses short and structured."),
        
        ("We're working on a setup wizard project",
         "Yes, we're building setup_wizard.py to improve the onboarding experience."),
    ]
    
    for i, (user_msg, my_response) in enumerate(conversations, 1):
        print(f"\n--- Turn {i} ---")
        
        # BEFORE responding: Get context
        print(f"📝 User: {user_msg}")
        print("🔍 Recalling memories...")
        
        context = connector.get_context(user_msg)
        memories = connector.recall(user_msg)
        
        if memories:
            print(f"   Found {len(memories)} relevant memories:")
            for m in memories[:2]:
                print(f"   • {m['content'][:60]}...")
        else:
            print("   No relevant memories yet")
        
        # Responding
        print(f"🤖 Klaus: {my_response}")
        
        # AFTER responding: Store interaction
        connector.store_interaction(user_msg, my_response)
        print("💾 Stored to memory")
    
    print("\n" + "=" * 50)
    print("📊 Final Memory Stats:")
    stats = connector.get_stats()
    print(f"   Total: {stats['total']} memories")
    print(f"   Categories: {stats['categories']}")
    
    print("\n🧠 Now I can recall:")
    queries = ["Mateus role", "communication preference", "current project"]
    for q in queries:
        results = connector.recall(q, limit=2)
        print(f"\n   Q: {q}")
        for r in results:
            print(f"   → {r['content'][:80]}...")

if __name__ == "__main__":
    simulate_conversation()
