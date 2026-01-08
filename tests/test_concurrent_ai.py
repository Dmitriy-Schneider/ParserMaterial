"""
Test concurrent AI search from multiple sources (Telegram + Web simulation)
"""
import threading
import time
from ai_search import AISearch

def test_ai_search(source_name, grade_name):
    """Simulate AI search from a source"""
    print(f"\n[{source_name}] Starting search for '{grade_name}'...")
    ai = AISearch()

    if not ai.enabled:
        print(f"[{source_name}] AI search disabled")
        return

    start_time = time.time()
    result = ai.search_steel(grade_name)
    elapsed = time.time() - start_time

    if result:
        print(f"[{source_name}] ✓ Found '{grade_name}' in {elapsed:.2f}s")
        print(f"[{source_name}]   - Validated: {result.get('validated')}")
        print(f"[{source_name}]   - Cached: {result.get('cached', False)}")
        print(f"[{source_name}]   - Link: {result.get('link', 'N/A')[:50]}")
    else:
        print(f"[{source_name}] ✗ Not found '{grade_name}' in {elapsed:.2f}s")

def test_concurrent_access():
    """Test concurrent AI searches"""
    print("="*80)
    print("ТЕСТ ОДНОВРЕМЕННЫХ AI ЗАПРОСОВ")
    print("="*80)

    # Scenario 1: Same grade from two sources (tests cache locking)
    print("\n[SCENARIO 1] Два источника ищут одну марку одновременно")
    print("-"*80)

    grade = "K888"

    thread1 = threading.Thread(target=test_ai_search, args=("TELEGRAM", grade))
    thread2 = threading.Thread(target=test_ai_search, args=("WEB", grade))

    thread1.start()
    time.sleep(0.1)  # Small delay to simulate near-simultaneous requests
    thread2.start()

    thread1.join()
    thread2.join()

    print("\n[RESULT] Оба запроса завершены без ошибок")

    # Scenario 2: Different grades from two sources (tests parallel AI calls)
    print("\n" + "="*80)
    print("[SCENARIO 2] Два источника ищут разные марки одновременно")
    print("-"*80)

    thread3 = threading.Thread(target=test_ai_search, args=("TELEGRAM", "Bohler K340"))
    thread4 = threading.Thread(target=test_ai_search, args=("WEB", "CPM 3V"))

    thread3.start()
    thread4.start()

    thread3.join()
    thread4.join()

    print("\n[RESULT] Оба запроса завершены без ошибок")

    # Scenario 3: Test cache hit (second request should be instant)
    print("\n" + "="*80)
    print("[SCENARIO 3] Повторный запрос той же марки (должен быть из кеша)")
    print("-"*80)

    test_ai_search("TELEGRAM", grade)

    print("\n" + "="*80)
    print("✓ ВСЕ СЦЕНАРИИ ЗАВЕРШЕНЫ")
    print("="*80)

if __name__ == "__main__":
    test_concurrent_access()
