"""
core/grpc_clients.py
"""
import grpc
from constants.defs import GRPC_PORT
from generated import triage_pb2, triage_pb2_grpc
from generated import orchestrator_pb2, orchestrator_pb2_grpc
from generated import specialist_pb2, specialist_pb2_grpc

GRPC_TIMEOUT = 330  # seconds — must exceed NIM 300s timeout

def get_grpc_channel():
    return grpc.aio.insecure_channel(f'localhost:{GRPC_PORT}')

async def triage_classify(user_input: str) -> tuple[str, float]:
    async with get_grpc_channel() as channel:
        stub = triage_pb2_grpc.TriageServiceStub(channel)
        req = triage_pb2.TriageRequest(user_input=user_input)
        resp = await stub.ClassifyFluency(req, timeout=GRPC_TIMEOUT, wait_for_ready=True)
        return resp.fluency, resp.confidence

async def triage_generate_question(phase: int, fluency: str, context_json: str):
    # NOTE: channel must stay open for the full streaming duration — do NOT use async with here
    channel = get_grpc_channel()
    try:
        stub = triage_pb2_grpc.TriageServiceStub(channel)
        req = triage_pb2.QuestionRequest(phase=phase, fluency=fluency, context_json=context_json)
        async for chunk in stub.GenerateQuestion(req, timeout=GRPC_TIMEOUT, wait_for_ready=True):
            yield chunk.token
    finally:
        await channel.close()

async def orchestrator_decide(session_json: str) -> tuple[str, str]:
    async with get_grpc_channel() as channel:
        stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
        req = orchestrator_pb2.SessionPayload(session_json=session_json)
        resp = await stub.DecideNextAction(req, timeout=GRPC_TIMEOUT, wait_for_ready=True)
        return resp.action, resp.payload_json

async def orchestrator_compile_brief(session_json: str) -> str:
    async with get_grpc_channel() as channel:
        stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
        req = orchestrator_pb2.SessionPayload(session_json=session_json)
        resp = await stub.CompileFinalBrief(req, timeout=GRPC_TIMEOUT, wait_for_ready=True)
        return resp.brief_json

async def specialist_run_swarm(brief_json: str):
    # NOTE: channel must stay open for the full streaming duration
    channel = get_grpc_channel()
    try:
        stub = specialist_pb2_grpc.SpecialistServiceStub(channel)
        req = specialist_pb2.BriefRequest(brief_json=brief_json)
        async for event in stub.RunSwarm(req, timeout=GRPC_TIMEOUT, wait_for_ready=True):
            yield event.event_type, event.payload_json
    finally:
        await channel.close()
