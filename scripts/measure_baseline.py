import requests
import time
import json
import statistics

def measure_chat_performance(prompt, num_runs=3):
    url = "http://localhost:5002/chat"
    total_times = []
    
    print(f"Measuring performance for prompt: '{prompt}'")
    print(f"Running {num_runs} iterations...\n")
    
    for i in range(num_runs):
        start_time = time.time()
        try:
            response = requests.post(url, json={"message": prompt})
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                movies_count = len(data.get("movies", []))
                validation = data.get("validation", {})
                
                print(f"Run {i+1}: {duration:.2f}s | Movies: {movies_count} | Avg Val Latency: {validation.get('avg_latency_ms', 0):.0f}ms")
                total_times.append(duration)
            else:
                print(f"Run {i+1}: Error {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Run {i+1}: Exception: {e}")
            
    if total_times:
        avg_time = statistics.mean(total_times)
        min_time = min(total_times)
        max_time = max(total_times)
        print(f"\n--- Results ---")
        print(f"Average: {avg_time:.2f}s")
        print(f"Min:     {min_time:.2f}s")
        print(f"Max:     {max_time:.2f}s")
        return avg_time
    return None

if __name__ == "__main__":
    # Ensure the server is running or tell user to run it
    try:
        requests.get("http://localhost:5002/health")
    except:
        print("Error: Cineman server is not running on http://localhost:5002")
        print("Please start it with 'python3 run.py' in a separate terminal.")
        exit(1)
        
    measure_chat_performance("I want to watch three sci-fi movies like Interstellar", num_runs=3)
