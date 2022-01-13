import json
import boto3
import tempfile
import os
import logger
from media_tools import video_encode_for_web
from api import (
    upload_task_status_update,
    UpdateTaskStatusRequest,
)


log = logger.get_logger("answer-transcode-web-handler")


def _require_env(n: str) -> str:
    env_val = os.environ.get(n, "")
    if not env_val:
        raise EnvironmentError(f"missing required env var {n}")
    return env_val


s3_bucket = _require_env("S3_STATIC_ARN").split(":")[-1]
log.info("using s3 bucket %s", s3_bucket)
s3 = boto3.client("s3")


def transcode_web(video_file, s3_path):
    work_dir = os.path.dirname(video_file)
    web_mp4 = os.path.join(work_dir, "web.mp4")

    video_encode_for_web(video_file, web_mp4)

    log.info("uploading %s to %s/%s", web_mp4, s3_bucket, s3_path)
    s3.upload_file(
        web_mp4,
        s3_bucket,
        f"{s3_path}/web.mp4",
        ExtraArgs={"ContentType": "video/mp4"},
    )


def handler(event, context):
    log.info(json.dumps(event))
    for record in event["Records"]:
        body = json.loads(str(record["body"]))
        request = json.loads(str(body["Message"]))["request"]
        task_list = request["task_list"]
        task = next(filter(lambda t: t["task_name"] == "transcoding-web", task_list))
        if not task:
            log.warning("no transcoding-web task requested")
            return
        log.info("video to process %s", request["video"])
        with tempfile.TemporaryDirectory() as work_dir:
            work_file = os.path.join(work_dir, "original.mp4")
            s3.download_file(s3_bucket, request["video"], work_file)
            s3_path = os.path.dirname(
                request["video"]
            )  # same 'folder' as original file
            log.info("%s downloaded to %s", request["video"], work_dir)
            upload_task_status_update(
                UpdateTaskStatusRequest(
                    mentor=request["mentor"],
                    question=request["question"],
                    task_id=task["task_id"],
                    new_status="IN_PROGRESS",
                )
            )
            transcode_web(work_file, s3_path)
            upload_task_status_update(
                UpdateTaskStatusRequest(
                    mentor=request["mentor"],
                    question=request["question"],
                    task_id=task["task_id"],
                    new_status="DONE",
                    media=[
                        {
                            "type": "video",
                            "tag": "web",
                            "url": f"{s3_path}/web.mp4",
                        }
                    ],
                )
            )
