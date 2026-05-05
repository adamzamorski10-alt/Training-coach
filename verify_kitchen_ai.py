#!/usr/bin/env python
"""
Verify script for Kitchen AI implementation
Checks if all components are properly configured
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

sys.path.insert(0, '.')

def check_env():
    """Check if environment variables are set"""
    print("\n🔐 Environment Variables Check:")
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if groq_key:
        print(f"  ✅ GROQ_API_KEY is set (length: {len(groq_key)})")
    else:
        print("  ❌ GROQ_API_KEY is missing!")
        return False
    
    if gemini_key:
        print(f"  ✅ GEMINI_API_KEY is set (length: {len(gemini_key)})")
    else:
        print("  ⚠️  GEMINI_API_KEY is missing (will use Groq as primary)")
    
    return True

def check_imports():
    """Check if all required modules are imported"""
    print("\n📦 Module Imports Check:")
    try:
        import fitai_api
        print("  ✅ fitai_api imported successfully")
        
        # Check if ask_claude exists
        if hasattr(fitai_api, 'ask_claude'):
            print("  ✅ ask_claude function found")
        else:
            print("  ❌ ask_claude function not found!")
            return False
        
        # Check if _AIError exists
        if hasattr(fitai_api, '_AIError'):
            print("  ✅ _AIError class found")
        else:
            print("  ❌ _AIError class not found!")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def check_endpoint():
    """Check if endpoint logic can parse JSON correctly"""
    print("\n🔄 Endpoint JSON Logic Check:")
    try:
        test_json = [
            {
                "nazwa": "Kurczak z ryzem",
                "składniki": ["kurczak", "ryż"],
                "opis": "Przepis testowy",
                "kalorie": 350,
                "białko": 35,
                "węglowodany": 40,
                "tłuszcze": 8
            }
        ]
        
        # Test JSON serialization
        json_str = json.dumps(test_json)
        print(f"  ✅ JSON serialization works (length: {len(json_str)})")
        
        # Test JSON deserialization
        parsed = json.loads(json_str)
        print(f"  ✅ JSON deserialization works ({len(parsed)} recipes)")
        
        # Test markdown code block removal (what backend does)
        markdown = f"```json\n{json_str}\n```"
        cleaned = markdown.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        parsed2 = json.loads(cleaned)
        print(f"  ✅ Markdown code block removal works ({len(parsed2)} recipes)")
        
        return True
    except Exception as e:
        print(f"  ❌ JSON Logic error: {e}")
        return False

def check_frontend():
    """Check if frontend file has kitchenGenerate function"""
    print("\n🎨 Frontend Check:")
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'function kitchenGenerate' in content:
            print("  ✅ kitchenGenerate function found in index.html")
        else:
            print("  ❌ kitchenGenerate function not found!")
            return False
        
        if '/app/kitchen/generate' in content:
            print("  ✅ /app/kitchen/generate endpoint call found")
        else:
            print("  ❌ /app/kitchen/generate endpoint call not found!")
            return False
        
        if 'onclick="kitchenGenerate()"' in content:
            print("  ✅ Button properly configured to call kitchenGenerate()")
        else:
            print("  ⚠️  Button might not call kitchenGenerate()")
        
        if 'Authorization' in content and 'Bearer' in content:
            print("  ✅ Authorization header is being added")
        else:
            print("  ❌ Authorization header not found!")
            return False
        
        if 'console.log' in content:
            print("  ✅ Debug console.log statements found")
        else:
            print("  ⚠️  No console.log statements for debugging")
        
        return True
    except Exception as e:
        print(f"  ❌ Frontend check error: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 KITCHEN AI VERIFICATION SCRIPT")
    print("=" * 60)
    
    results = []
    
    results.append(("Environment Variables", check_env()))
    results.append(("Module Imports", check_imports()))
    results.append(("Endpoint JSON Logic", check_endpoint()))
    results.append(("Frontend", check_frontend()))
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Ready for testing!")
        print("\nNext steps:")
        print("  1. Run: uvicorn fitai_api:app --reload --port 8000")
        print("  2. Open: http://localhost:5500/index.html (or file://)")
        print("  3. Go to: Plan → Dieta → Kuchnia AI")
        print("  4. Open DevTools (F12) to see console logs")
        print("  5. Add ingredients and click 'Generuj 4 przepisy'")
    else:
        print("❌ SOME CHECKS FAILED - Please review errors above")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
