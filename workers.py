import asyncio
from queue_utils import redis_client 
from fetch_resume import fetch_data
import time

async def worker(worker_id: int):

    while True:
        await asyncio.sleep(2)
        try:
            task = await redis_client.brpop("task_queue", timeout=1)
            print(task)
            if task:
                print(f"Worker {worker_id} processing: {task[1]}")
                print(task)
                await asyncio.sleep(1)
                # fetch_data(task[1])
                print(f"Worker {worker_id} completed task: {task[1]}")
            else:
                print('task is not present')
                await asyncio.sleep(2)
        except Exception as e:
            print(f"worker {worker_id} encountered an error {e}")