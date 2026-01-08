"""
Test AI search with K888 example to verify:
1. Chemical composition is found (mandatory)
2. Manufacturer and country are extracted (Bohler Edelstahl, Австрия)
3. Source URL is extracted (official website or PDF datasheet)
"""
import json
import sys
from ai_search import AISearch

def test_k888():
    """Test K888 steel grade search"""
    print("="*80)
    print("TESTING AI SEARCH WITH K888 EXAMPLE")
    print("="*80)

    ai = AISearch()

    if not ai.enabled:
        print("\n[ERROR] AI search is not enabled!")
        print("Please set PERPLEXITY_API_KEY or OPENAI_API_KEY in .env file")
        return False

    print("\n[INFO] AI Search enabled")
    print(f"  - Perplexity: {'✓' if ai.perplexity_key else '✗'}")
    print(f"  - OpenAI: {'✓' if ai.api_key else '✗'}")

    # Test search
    grade_name = "K888"
    print(f"\n[SEARCH] Searching for '{grade_name}'...")
    print("-"*80)

    result = ai.search_steel(grade_name)

    if not result:
        print("\n[FAILED] ❌ No result returned")
        print("Expected: Result with chemical composition, manufacturer, and source URL")
        return False

    print("\n[SUCCESS] ✓ Result found!")
    print("="*80)
    print("RESULT DETAILS")
    print("="*80)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Validation checks
    print("\n" + "="*80)
    print("VALIDATION CHECKS")
    print("="*80)

    checks = {
        "Grade name": result.get('grade') == grade_name,
        "Validated": result.get('validated') == True,
        "Chemical composition found": any([
            result.get('c'), result.get('cr'), result.get('mo'),
            result.get('v'), result.get('w'), result.get('ni')
        ]),
        "Manufacturer": bool(result.get('manufacturer')),
        "Standard/Manufacturer info": bool(result.get('standard')),
        "Source URL (link)": bool(result.get('link')),
        "AI source": result.get('ai_source') in ['perplexity', 'openai']
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {check_name:30s}: {status}")
        if not passed:
            all_passed = False

    # Specific checks for K888
    print("\n" + "="*80)
    print("K888 SPECIFIC REQUIREMENTS")
    print("="*80)

    manufacturer = result.get('manufacturer', '')
    standard = result.get('standard', '')
    link = result.get('link', '')

    k888_checks = {
        "Manufacturer contains 'Bohler'": 'bohler' in manufacturer.lower() if manufacturer else False,
        "Standard/Country info present": bool(standard),
        "Link is valid URL": link.startswith('http') if link else False,
        "Link to Bohler website or PDF": ('bohler' in link.lower() or '.pdf' in link.lower()) if link else False
    }

    for check_name, passed in k888_checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {check_name:35s}: {status}")
        if not passed:
            all_passed = False

    # Print specific extracted values
    print("\n" + "="*80)
    print("EXTRACTED VALUES")
    print("="*80)
    print(f"  Manufacturer: {manufacturer or 'NOT FOUND'}")
    print(f"  Standard: {standard or 'NOT FOUND'}")
    print(f"  Link: {link or 'NOT FOUND'}")

    # Chemical composition summary
    elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si']
    comp_found = []
    for elem in elements:
        value = result.get(elem)
        if value and value not in ['null', None, '', '0', '0.00']:
            comp_found.append(f"{elem.upper()}={value}")

    print(f"  Composition: {', '.join(comp_found) if comp_found else 'NOT FOUND'}")

    # Final result
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL CHECKS PASSED!")
        print("="*80)
        return True
    else:
        print("✗ SOME CHECKS FAILED")
        print("="*80)
        return False

if __name__ == "__main__":
    success = test_k888()
    sys.exit(0 if success else 1)
