import os
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app.core.env import load_env  # type: ignore[import-not-found]

load_env()

from sqlalchemy.orm import Session

from app.database import get_db_session  # type: ignore[import-not-found]
from app.models.task import Task, TaskStep  # type: ignore[import-not-found]
from app.models.media import Scene  # type: ignore[import-not-found]


def print_task_state(task_id: int):
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        print('Task:', {'id': task.id, 'status': task.status, 'progress': task.progress, 'error_msg': task.error_msg})
        steps = db.query(TaskStep).filter(TaskStep.task_id == task_id).order_by(TaskStep.seq).all()
        print('Steps:')
        for s in steps:
            print(' ', s.seq, s.step_name, 'status=', s.status, 'started_at=', s.started_at, 'finished_at=', s.finished_at, 'error=', s.error_msg)
        scenes = db.query(Scene).filter(Scene.task_id == task_id).order_by(Scene.seq).all()
        print('Scenes: (count=', len(scenes), ')')
        for sc in scenes:
            print(' ', sc.seq, 'image_status=', sc.image_status, 'audio_status=', sc.audio_status, 'video_status=', sc.video_status, 'error=', sc.error_msg)
    finally:
        db.close()

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--task', type=int, default=2)
    args = p.parse_args()
    print_task_state(args.task)
