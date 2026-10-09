from agents import llm

print("Testing Gemini...")

try:
    response = llm.invoke("Reply with only OK")
    print(response.content)
except Exception as e:
    print("Gemini failed:", e)  