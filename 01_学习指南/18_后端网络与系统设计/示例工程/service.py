"""业务层不依赖HTTP，便于分别验证协议和任务行为。"""

import json
import threading
import time
from copy import deepcopy

from storage import JobStore

POLICIES = {"refund": "退款期限为30天。", "support": "支持邮箱为help@example.invalid。"}


class ServiceError(ValueError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def validate_question(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        raise ServiceError(400, "invalid_question", "question须为1到100字符的非空文本")
    return value.strip()


def retrieve(question: str):
    if question == "simulate_timeout":
        # 明确模拟上游报告超时，不把此分支称为真实网络超时。
        raise TimeoutError("模拟检索上游超时")
    if question not in POLICIES:
        return {"answer": None, "code": "no_evidence"}
    return {"answer": POLICIES[question], "source": "synthetic-policy-v1"}


class QueryService:
    def __init__(self, store: JobStore, ttl_seconds=0.2, clock=time.monotonic):
        self.store = store
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.worker = None

    def query(self, owner: str, question: str):
        question = validate_question(question)
        cache_key = (owner, "synthetic-policy-v1", question)
        with self.cache_lock:
            cached = self.cache.get(cache_key)
            if cached and cached[0] > self.clock():
                return {**deepcopy(cached[1]), "cache_hit": True}
            self.cache.pop(cache_key, None)
        try:
            result = retrieve(question)
        except TimeoutError as error:
            raise ServiceError(504, "upstream_timeout", str(error)) from error
        with self.cache_lock:
            # 小型内存缓存明确限容量；不展示没有边界的长期字典增长。
            if len(self.cache) >= 32:
                self.cache.pop(next(iter(self.cache)))
            self.cache[cache_key] = (self.clock() + self.ttl_seconds, deepcopy(result))
        return {**result, "cache_hit": False}

    def submit(self, owner: str, request_key: str, question: str):
        question = validate_question(question)
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 64:
            raise ServiceError(
                400, "invalid_request_key", "request_key须为1到64字符文本"
            )
        result = self.store.create(owner, request_key, question)
        self.wake_event.set()
        return result

    def run_one(self):
        job = self.store.claim_next()
        if job is None:
            return False
        try:
            result = self.query(job["owner"], job["question"])
        except ServiceError as error:
            self.store.finish(job["job_id"], "failed", {"code": error.code})
        else:
            self.store.finish(job["job_id"], "completed", result)
        return True

    def start_worker(self):
        if self.worker is not None:
            raise RuntimeError("工作线程不能重复启动")
        self.store.recover_running()
        self.worker = threading.Thread(target=self._work, name="query-worker")
        self.worker.start()

    def _work(self):
        while not self.stop_event.is_set():
            if not self.run_one():
                self.wake_event.wait(0.1)
                self.wake_event.clear()

    def close(self):
        self.stop_event.set()
        self.wake_event.set()
        if self.worker is not None:
            self.worker.join(timeout=2)
            if self.worker.is_alive():
                raise RuntimeError("工作线程未能在2秒内退出")


def public_job(job):
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "result": json.loads(job["result"]) if job["result"] else None,
    }
