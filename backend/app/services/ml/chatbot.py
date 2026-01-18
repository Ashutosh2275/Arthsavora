import google.generativeai as genai
from ...core.config import settings

# Configure the Gemini Engine
genai.configure(api_key=settings.GEMINI_API_KEY)

def get_financial_advice(user_query: str, context: dict):
    """
    Constructs a context-aware prompt for Gemini and returns a response.
    """
    model = genai.GenerativeModel('gemini-pro')
    
    # The Prompt Engineering Layer
    prompt = f"""
    You are ARTHSAVORA AI, a world-class personal finance coach. 
    You are helpful, encouraging, and highly data-driven.

    USER DATA CONTEXT:
    - Total Expenditure this Month: ₹{context['total_spent']}
    - Spending Categories: {", ".join(context['categories'])}
    - Active Financial Goals: {", ".join(context['goals'])}

    USER QUESTION: "{user_query}"

    RULES:
    1. Use the data above to answer specifically about the user's money.
    2. Be concise. Max 3-4 sentences.
    3. Suggest ways to save based on their categories.
    4. Never give legal or certified investment advice; use phrases like "You might consider" or "Educationally speaking."
    5. Format with a friendly tone.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I'm processing your data right now. Could you please repeat that in a moment?"