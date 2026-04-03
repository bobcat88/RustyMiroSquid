import pytest
import threading
import concurrent.futures

class MockBeliefTracker:
    def __init__(self):
        self._lock = threading.RLock()
        self.count = 0
        
    def update(self):
        with self._lock:
            # Simulate a non-atomic operation that would race without a lock
            current = self.count
            current += 1
            self.count = current

def test_belief_tracker_threading():
    tracker = MockBeliefTracker()
    
    def worker():
        for _ in range(100):
            tracker.update()
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker) for _ in range(10)]
        concurrent.futures.wait(futures)
        
    assert tracker.count == 1000
