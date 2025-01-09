import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

def enqueue_message(message: str):
    print(message)

    redis_client.rpush(queue_name, message)

def dequeue_message(message):
    print(message)
    return redis_client.lpop(queue_name)

def get_queue_length(message):
    queue_length = redis_client.llen(queue_name)
    print(message, f'remaining user request: {queue_length}')
    return 

def clear_queue():
    redis_client.ltrim(queue_name, 1, 0)  # Trims the list to 0 elements

def delete_queue(message):
    print(message)
    redis_client.delete(queue_name) 

queue_name = "task_queue"