#
# This software is Copyright ©️ 2020 The University of Southern California. All Rights Reserved.
# Permission to use, copy, modify, and distribute this software and its documentation for educational, research and non-profit purposes, without fee, and without a written agreement is hereby granted, provided that the above copyright notice and subject to the full license file found in the root of this software deliverable. Permission to make commercial use of this software may be obtained by contacting:  USC Stevens Center for Innovation University of Southern California 1150 S. Olive Street, Suite 2300, Los Angeles, CA 90115, USA Email: accounting@stevens.usc.edu
#
# The full terms of this copyright and license should always be found in the root directory of this software deliverable as "license.txt" and if these terms are not found with this software, please contact the USC Stevens Center for the full license.
#
import os

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.
from celery import Celery  # NOQA
from kombu import Exchange, Queue  # NOQA

from mentor_upload_process import (  # NOQA
    CancelTaskRequest,
    CancelTaskResponse,
    ProcessAnswerRequest,
    ProcessAnswerResponse,
    ProcessTransferRequest,
    process,
)


def get_queue_trim_upload_stage() -> str:
    return os.environ.get("TRIM_UPLOAD_QUEUE_NAME") or "trim_upload"


def get_queue_transcribe_stage() -> str:
    return os.environ.get("TRANSCRIBE_QUEUE_NAME") or "transcribe"


def get_queue_transcode_stage() -> str:
    return os.environ.get("TRANSCODE_QUEUE_NAME") or "transcode"


def get_queue_finalization_stage() -> str:
    return os.environ.get("FINALIZATION_QUEUE_NAME") or "finalization"


def get_queue_cancel_task() -> str:
    return os.environ.get("CANCEL_TASK_QUEUE_NAME") or "cancel"


broker_url = (
    os.environ.get("UPLOAD_CELERY_BROKER_URL")
    or os.environ.get("CELERY_BROKER_URL")
    or "redis://redis:6379/0"
)
celery = Celery("mentor_upload_tasks", broker=broker_url)
celery.conf.update(
    {
        "accept_content": ["json"],
        "broker_url": broker_url,
        "event_serializer": os.environ.get("CELERY_EVENT_SERIALIZER", "json"),
        "result_backend": (
            os.environ.get("UPLOAD_CELERY_RESULT_BACKEND")
            or os.environ.get("CELERY_RESULT_BACKEND")
            or "redis://redis:6379/0"
        ),
        "result_serializer": os.environ.get("CELERY_RESULT_SERIALIZER", "json"),
        "task_default_queue": get_queue_finalization_stage(),
        "task_default_exchange": get_queue_finalization_stage(),
        "task_default_routing_key": get_queue_finalization_stage(),
        "task_queues": [
            Queue(
                get_queue_trim_upload_stage(),
                exchange=Exchange(
                    get_queue_trim_upload_stage(),
                    "direct",
                    durable=True,
                ),
                routing_key=get_queue_trim_upload_stage(),
            ),
            Queue(
                get_queue_transcode_stage(),
                exchange=Exchange(
                    get_queue_transcode_stage(),
                    "direct",
                    durable=True,
                ),
                routing_key=get_queue_transcode_stage(),
            ),
            Queue(
                get_queue_transcribe_stage(),
                exchange=Exchange(
                    get_queue_transcribe_stage(),
                    "direct",
                    durable=True,
                ),
                routing_key=get_queue_transcribe_stage(),
            ),
            Queue(
                get_queue_finalization_stage(),
                exchange=Exchange(
                    get_queue_finalization_stage(), "direct", durable=True
                ),
                routing_key=get_queue_finalization_stage(),
            ),
            Queue(
                get_queue_cancel_task(),
                exchange=Exchange(get_queue_cancel_task(), "direct", durable=True),
                routing_key=get_queue_cancel_task(),
            ),
        ],
        "task_routes": {
            "mentor_upload_tasks.tasks.trim_upload_stage": {
                "queue": get_queue_trim_upload_stage()
            },
            "mentor_upload_tasks.tasks.transcribe_stage": {
                "queue": get_queue_transcribe_stage()
            },
            "mentor_upload_tasks.tasks.transcode_stage": {
                "queue": get_queue_transcode_stage()
            },
            "mentor_upload_tasks.tasks.finalization_stage": {
                "queue": get_queue_finalization_stage()
            },
            "mentor_upload_tasks.tasks.cancel_task": {"queue": get_queue_cancel_task()},
        },
        "task_serializer": os.environ.get("CELERY_TASK_SERIALIZER", "json"),
    }
)


@celery.task()
def trim_upload_stage(
    req: ProcessAnswerRequest,
) -> ProcessAnswerResponse:
    task_id = trim_upload_stage.request.id
    return process.trim_upload_stage(req, task_id)


@celery.task()
def transcode_stage(
    dict_tuple: dict,
    req: ProcessAnswerRequest,
) -> ProcessAnswerResponse:
    task_id = transcode_stage.request.id
    return process.transcode_stage(dict_tuple, req, task_id)


@celery.task()
def transcribe_stage(
    dict_tuple: dict,
    req: ProcessAnswerRequest,
) -> ProcessAnswerResponse:
    task_id = transcribe_stage.request.id
    return process.transcribe_stage(dict_tuple, req, task_id)


@celery.task()
def finalization_stage(
    dict_tuple: dict, req: ProcessAnswerRequest
) -> ProcessAnswerResponse:
    task_id = finalization_stage.request.id
    return process.finalization_stage(dict_tuple, req=req, task_id=task_id)


@celery.task()
def process_transfer_video(req: ProcessTransferRequest):
    task_id = process_transfer_video.request.id
    return process.process_transfer_video(req, task_id)


@celery.task()
def cancel_task(req: CancelTaskRequest) -> CancelTaskResponse:
    t = process.cancel_task(req)
    celery.control.revoke(req.get("task_id"), terminate=True)
    return t
